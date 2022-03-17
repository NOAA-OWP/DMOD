#!/bin/sh
# $1 will have the number of nodes associated with this run
# $2 will have the host string in MPI form, i.e. hostname:N, hostname:M
# $3 will have the unique job id
# $4 will be the name of the output dataset (which will imply a directory location)
# $5 will be the name of the hydrofabric dataset (which will imply a directory location)
# $6 will be the name of the configuration dataset (which will imply a directory location)
# $7 and beyond will have colon-joined category+name strings (e.g., FORCING:aorc_csv_forcings_1) for Minio object store
#       datasets to mount

MPI_NODE_COUNT="${1:?No MPI node count given}"
MPI_HOST_STRING="${2:?No MPI host string given}"
JOB_ID=${3:?No Job id given}
OUTPUT_DATASET_NAME="${4:?}"
HYDROFABRIC_DATASET_NAME="${5:?}"
CONFIG_DATASET_NAME="${6:?}"

ACCESS_KEY_SECRET="object_store_exec_user_name"
SECRET_KEY_SECRET="object_store_exec_user_passwd"
DOCKER_SECRETS_DIR="/run/secrets"
ACCESS_KEY_FILE="${DOCKER_SECRETS_DIR}/${ACCESS_KEY_SECRET}"
SECRET_KEY_FILE="${DOCKER_SECRETS_DIR}/${SECRET_KEY_SECRET}"

ALL_DATASET_DIR="/dmod/dataset"
OUTPUT_DATASET_DIR="${ALL_DATASET_DIR}/output/${OUTPUT_DATASET_DIR}"
HYDROFABRIC_DATASET_DIR="${ALL_DATASET_DIR}/hydrofabric/${HYDROFABRIC_DATASET_NAME}"
CONFIG_DATASET_DIR="${ALL_DATASET_DIR}/config/${HYDROFABRIC_DATASET_NAME}"

S3FS_PASSWD_FILE="${HOME}/.passwd-s3fs"

# Mount an object store dataset of the given name and data category (which implies mount point directory)
mount_object_store_dataset()
{
    # Dataset name is $1
    # Dataset category (lower case) is $2
    _MOUNT_DIR="${ALL_DATASET_DIR}/${2}/${1}"
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
    parse_object_store_strings ${@:7}
fi

# Sanity check that the output, hydrofabric, and config datasets are available (i.e., their directories are in place)
check_for_dataset_dir "${CONFIG_DATASET_DIR}"
check_for_dataset_dir "${HYDROFABRIC_DATASET_DIR}"
check_for_dataset_dir "${OUTPUT_DATASET_DIR}"

# Move to the output dataset mounted directory
cd ${OUTPUT_DATASET_DIR}

#Execute the model on the linked data
ngen ${HYDROFABRIC_DATASET_DIR}/catchment_data.geojson "" ${HYDROFABRIC_DATASET_DIR}/nexus_data.geojson "" ${CONFIG_DATASET_DIR}/realization_config.json > std_out.log 2> std_err.log

#Capture the return value to use as service exit code
ngen_return=$?
echo 'ngen returned with a return value: ' $ngen_return
#Exit with the model's exit code
exit $ngen_return
