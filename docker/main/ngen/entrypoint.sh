#!/bin/sh
# Managed by the _generate_docker_cmd_args function in scheduler.py of dmod.scheduler
#
# $1 will have the number of nodes associated with this run
# $2 will have the host string in MPI form, i.e. hostname:N, hostname:M
# $3 will have the unique job id
# $4 is the worker index
# $5 will be the name of the output dataset (which will imply a directory location)
# $6 will be the name of the hydrofabric dataset (which will imply a directory location)
# $7 will be the name of the realization configuration dataset (which will imply a directory location)
# $8 will be the name of the BMI configuration dataset (which will imply a directory location)
# $9 will be the name of the partition configuration dataset (which will imply a directory location)
# $10 and beyond will have colon-joined category+name strings (e.g., FORCING:aorc_csv_forcings_1) for Minio object store
#       datasets to mount

MPI_NODE_COUNT="${1:?No MPI node count given}"
MPI_HOST_STRING="${2:?No MPI host string given}"
JOB_ID=${3:?No Job id given}
WORKER_INDEX=${4:?No worker index given}
OUTPUT_DATASET_NAME="${5:?}"
HYDROFABRIC_DATASET_NAME="${6:?}"
REALIZATION_CONFIG_DATASET_NAME="${7:?}"
BMI_CONFIG_DATASET_NAME="${8:?}"
PARTITION_DATASET_NAME="${9:?}"

ACCESS_KEY_SECRET="object_store_exec_user_name"
SECRET_KEY_SECRET="object_store_exec_user_passwd"
DOCKER_SECRETS_DIR="/run/secrets"
ACCESS_KEY_FILE="${DOCKER_SECRETS_DIR}/${ACCESS_KEY_SECRET}"
SECRET_KEY_FILE="${DOCKER_SECRETS_DIR}/${SECRET_KEY_SECRET}"

ALL_DATASET_DIR="/dmod/dataset"
OUTPUT_DATASET_DIR="${ALL_DATASET_DIR}/output/main"
HYDROFABRIC_DATASET_DIR="${ALL_DATASET_DIR}/hydrofabric/main"
REALIZATION_CONFIG_DATASET_DIR="${ALL_DATASET_DIR}/config/realization"
BMI_CONFIG_DATASET_DIR="${ALL_DATASET_DIR}/config/bmi"
PARTITION_DATASET_DIR="${ALL_DATASET_DIR}/config/partitions"

S3FS_PASSWD_FILE="${HOME}/.passwd-s3fs"

MPI_HOSTS_FILE="${HOME}/.mpi_hosts"

# Mount an object store dataset of the given name and data category (which implies mount point directory)
mount_object_store_dataset()
{
    # Dataset name is $1
    # Dataset category (lower case) is $2
    case "${1}" in
        "${OUTPUT_DATASET_NAME}")
            _MOUNT_DIR="${OUTPUT_DATASET_DIR}"
            ;;
        "${HYDROFABRIC_DATASET_NAME}")
            _MOUNT_DIR="${HYDROFABRIC_DATASET_DIR}"
            ;;
        "${REALIZATION_CONFIG_DATASET_NAME}")
            _MOUNT_DIR="${REALIZATION_CONFIG_DATASET_DIR}"
            ;;
        "${BMI_CONFIG_DATASET_NAME}")
            _MOUNT_DIR="${BMI_CONFIG_DATASET_DIR}"
            ;;
        "${PARTITION_DATASET_NAME}")
            _MOUNT_DIR="${PARTITION_DATASET_DIR}"
            ;;
        *)
            _MOUNT_DIR="${ALL_DATASET_DIR}/${2:?}/${1}"
    esac

    # TODO (later): this is a non-S3 implementation URL; add support for S3 directly also
    # This is based on the nginx proxy config (hopefully)
    _URL="http://minio_proxy:9000/"
    s3fs ${1} ${_MOUNT_DIR} -o passwd_file=${HOME}/.passwd-s3fs -o url=${_URL} -o use_path_request_style
}

parse_object_store_strings()
{
    while [ ${#} -gt 0 ]; do
        _CAT="$(echo "${1}"| sed -e 's/\([^:]*\):.*/\1/' | awk '{print tolower($0)}')"
        _NAME="$(echo "${1}"| sed -e 's/\([^:]*\):\(.*\)/\2/')"
        mount_object_store_dataset ${_NAME} ${_CAT}
        shift
    done
}

check_for_dataset_dir()
{
    # Dataset dir is $1
    _CATEG="$(echo "${1}" | sed "s|${ALL_DATASET_DIR}/\([^/]*\)/.*|\1|" | awk '{print toupper($0)}')"
    if [ ! -d "${1}" ]; then
        echo "Error: expected ${_CATEG} dataset directory ${1} not found." 2>&1
        exit 1
    fi
}

# Read Docker Secrets files for Object Store access, if they exist
if [ -e "${ACCESS_KEY_FILE}" ]; then
    ACCESS_KEY="$(cat "${ACCESS_KEY_FILE}")"
fi
if [ -e "${SECRET_KEY_FILE}" ]; then
    SECRET_KEY="$(cat "${SECRET_KEY_FILE}")"
fi

# Execute object store routine if we have an access key
if [ -n "${ACCESS_KEY:-}" ]; then
    # Of course, bail if we don't have the secret key also
    if [ -z "${SECRET_KEY:-}" ]; then
        echo "Error: ACCESS_KEY provided for Minio object store access, but no SECRET_KEY provided" 2>&1
        exit 1
    fi

    # Configure auth for s3fs
    echo ${ACCESS_KEY}:${SECRET_KEY} > "${S3FS_PASSWD_FILE}"
    chmod 600 "${S3FS_PASSWD_FILE}"

    # Parse args and mount any object stores datasets appropriately
    parse_object_store_strings ${@:10}
fi

# Sanity check that the output, hydrofabric, and config datasets are available (i.e., their directories are in place)
check_for_dataset_dir "${REALIZATION_CONFIG_DATASET_DIR}"
check_for_dataset_dir "${BMI_CONFIG_DATASET_DIR}"
check_for_dataset_dir "${PARTITION_DATASET_DIR}"
check_for_dataset_dir "${HYDROFABRIC_DATASET_DIR}"
check_for_dataset_dir "${OUTPUT_DATASET_DIR}"

# Move to the output dataset mounted directory
cd ${OUTPUT_DATASET_DIR}

if [ "${WORKER_INDEX}" = "0" ]; then
    echo "Starting SSH daemon on main worker"
    sudo /usr/sbin/sshd -D &

    # Write hoststring to file
    echo "${MPI_HOST_STRING}" > "${MPI_HOSTS_FILE}"

    CONFIGURED_CPU_COUNT=0
    # COUNT total CPUS and make sure hosts are running ssh
    for _HOST in $(cat "${MPI_HOSTS_FILE}"); do
        _CPUS=$(echo "${_HOST}" | cut -d ':' -f 2)
        _HOST_NAME=$(echo "${_HOST}" | cut -d ':' -f 1)
        CONFIGURED_CPU_COUNT=$((CONFIGURED_CPU_COUNT+_CPUS))
        #Make sure all hosts are reachable, this also covers localhost
        until ssh -q ${_HOST_NAME} exit >/dev/null 2>&1; do :; done
    done

    # Execute the model on the linked data
    /usr/local/bin/mpirun -f hostfile -n ${CONFIGURED_CPU_COUNT} \
        ngen ${HYDROFABRIC_DATASET_DIR}/catchment_data.geojson "" \
                ${HYDROFABRIC_DATASET_DIR}/nexus_data.geojson "" \
                ${REALIZATION_CONFIG_DATASET_DIR}/realization_config.json \
                ${PARTITION_DATASET_DIR}/partition_config.json > std_out.log 2> std_err.log

    #Capture the return value to use as service exit code
    NGEN_RETURN=$?
    echo 'ngen returned with a return value: ' {NGEN_RETURN}
    # Exit with the model's exit code
    exit ${NGEN_RETURN}
else
    echo "Starting SSH daemon, waiting for main job"
    sudo /usr/sbin/sshd -D
fi
