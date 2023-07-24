#!/bin/sh
# Managed by the _generate_docker_cmd_args function in scheduler.py of dmod.scheduler
#
# $1 will have the number of nodes associated with this run
# $2 will have comma-delimited host strings in MPI form; e.g., hostname:N,hostname:M
# $3 will have the unique job id
# $4 is the worker index
# $5 will be the name of the output dataset (which will imply a directory location)
# $6 will be the name of the hydrofabric dataset (which will imply a directory location)
# $7 will be the name of the realization configuration dataset (which will imply a directory location)
# $8 will be the name of the BMI configuration dataset (which will imply a directory location)
# $9 will be the name of the partition configuration dataset (which will imply a directory location)

MPI_NODE_COUNT="${1:?No MPI node count given}"
MPI_HOST_STRING="${2:?No MPI host string given}"
JOB_ID=${3:?No Job id given}
WORKER_INDEX=${4:?No worker index given}
OUTPUT_DATASET_NAME="${5:?}"
HYDROFABRIC_DATASET_NAME="${6:?}"
REALIZATION_CONFIG_DATASET_NAME="${7:?}"
BMI_CONFIG_DATASET_NAME="${8:?}"
# Don't require a partitioning config when only using a single node
if [ ${MPI_NODE_COUNT:?} -gt 1 ]; then
    PARTITION_DATASET_NAME="${9:?No argument for partition config dataset when expecting one for MPI-based job}"
fi

ACCESS_KEY_SECRET="object_store_exec_user_name"
SECRET_KEY_SECRET="object_store_exec_user_passwd"
DOCKER_SECRETS_DIR="/run/secrets"
ACCESS_KEY_FILE="${DOCKER_SECRETS_DIR}/${ACCESS_KEY_SECRET}"
SECRET_KEY_FILE="${DOCKER_SECRETS_DIR}/${SECRET_KEY_SECRET}"

MPI_USER="mpi"
if [ "$(whoami)" = "${MPI_USER}" ]; then
    MPI_HOSTS_FILE="${HOME}/.mpi_hosts"
else
    MPI_HOSTS_FILE="$(su ${MPI_USER} -c 'echo "${HOME}"')/.mpi_hosts"
fi

MPI_RUN="mpirun"
#NGEN_EXECUTABLE="ngen"
NGEN_SERIAL_EXECUTABLE="/ngen/ngen/cmake_build_serial/ngen"
NGEN_PARALLEL_EXECUTABLE="/ngen/ngen/cmake_build_parallel/ngen"
# This will be symlinked to the parallel one currently
NGEN_EXECUTABLE="/ngen/ngen/cmake_build/ngen"

ALL_DATASET_DIR="/dmod/datasets"
OUTPUT_DATASET_DIR="${ALL_DATASET_DIR}/output/${OUTPUT_DATASET_NAME}"
HYDROFABRIC_DATASET_DIR="${ALL_DATASET_DIR}/hydrofabric/${HYDROFABRIC_DATASET_NAME}"
REALIZATION_CONFIG_DATASET_DIR="${ALL_DATASET_DIR}/config/${REALIZATION_CONFIG_DATASET_NAME}"
BMI_CONFIG_DATASET_DIR="${ALL_DATASET_DIR}/config/${BMI_CONFIG_DATASET_NAME}"
# Don't require a partitioning dataset when only using a single node
if [ ${MPI_NODE_COUNT:?} -gt 1 ]; then
    PARTITION_DATASET_DIR="${ALL_DATASET_DIR}/config/${PARTITION_DATASET_NAME:?No partition config dataset name for directory}"
fi

RUN_SENTINEL="/home/${MPI_USER}/.run_sentinel"

print_date()
{
    date "+%Y-%m-%d,%H:%M:%S"
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

load_object_store_keys_from_docker_secrets()
{
    # Read Docker Secrets files for Object Store access, if they exist
    if [ -z "${ACCESS_KEY_FILE:-}" ]; then
        echo "WARN: Cannot load object store access key when Docker secret file name not set"
    elif [ -e "${ACCESS_KEY_FILE}" ]; then
        ACCESS_KEY="$(cat "${ACCESS_KEY_FILE}")"
    else
        echo "WARN: Cannot load object store access key when Docker secret file does not exist"
    fi

    if [ -z "${SECRET_KEY_FILE:-}" ]; then
            echo "WARN: Cannot load object store secret key when Docker secret file name not set"
    elif [ -e "${SECRET_KEY_FILE}" ]; then
        SECRET_KEY="$(cat "${SECRET_KEY_FILE}")"
    else
        echo "WARN: Cannot load object store secret key when Docker secret file does not exist"
    fi

    test -n "${ACCESS_KEY:-}" && test -n "${SECRET_KEY:-}"
}

exec_main_worker_ngen_run()
{
    # Write (split) hoststring to a proper file
    if [ -e "${MPI_HOSTS_FILE}" ]; then
        rm "${MPI_HOSTS_FILE}"
    fi

    _TOTAL_CPUS = 0
    echo "$(print_date) Preparing hosts file and checking ${MPI_NODE_COUNT} worker hosts are online for SSH"
    for i in $(echo "${MPI_HOST_STRING}" | sed 's/,/ /g'); do
        _HOST_NAME=$(echo "${i}" | awk -F: '{print $1}')
        _HOST_CPUS=$(echo "${i}" | awk -F: '{print $2}')

        # TODO: consider parameterizing this in the future, just in case we adopt openmpi
        # OpenMPI uses the "slots=" format, though we aren't currently using that implementation
        #echo "${i}" | awk -F: '{print $1 " slots=" $2}' >> "${MPI_HOSTS_FILE}"

        # MPICH uses the hosts file format "hostname:numCores" (which is what we get from the split host string arg)
        echo "${i}" >> "${MPI_HOSTS_FILE}"

        ((_TOTAL_CPUS = _TOTAL_CPUS+$_HOST_CPUS))

        # Make sure all hosts are reachable, this also covers localhost
        until ssh -q ${_HOST_NAME} exit >/dev/null 2>&1; do :; done
        echo "DEBUG: Confirmed MPI host ${_HOST_NAME} is online for SSH and has ${_HOST_CPUS} cpus available"
    done

    # Execute the model on the linked data
    echo "$(print_date) Executing mpirun command for ngen on ${MPI_NODE_COUNT} workers with ${_TOTAL_CPUS} total cpus"
    ${MPI_RUN:?} -f "${MPI_HOSTS_FILE}" -n ${_TOTAL_CPUS} \
        ${NGEN_EXECUTABLE:?} ${HYDROFABRIC_DATASET_DIR}/catchment_data.geojson "" \
                ${HYDROFABRIC_DATASET_DIR}/nexus_data.geojson "" \
                ${REALIZATION_CONFIG_DATASET_DIR}/realization_config.json \
                ${PARTITION_DATASET_DIR}/partition_config.json \
                --subdivided-hydrofabric

    #Capture the return value to use as service exit code
    NGEN_RETURN=$?

    echo "$(print_date) ngen mpirun command finished with return value: ${NGEN_RETURN}"

    # Close the other workers by removing this file
    for i in $(echo "${MPI_HOST_STRING}" | sed 's/,/ /g'); do
        _HOST_NAME=$(echo "${i}" | awk -F: '{print $1}')
        ssh -q ${_HOST_NAME} rm ${RUN_SENTINEL} >/dev/null 2>&1
    done

    echo "$(print_date) DEBUG: closed other worker SSH processes"

    # Exit with the model's exit code
    return ${NGEN_RETURN}
}

exec_serial_ngen_run()
{
    echo "$(print_date) Skipping host checks since job uses ${MPI_NODE_COUNT} worker hosts and framework will run serially"

    # Execute the model on the linked data
    echo "$(print_date) Executing serial build of ngen"
    ${NGEN_SERIAL_EXECUTABLE:?} ${HYDROFABRIC_DATASET_DIR}/catchment_data.geojson "" \
        ${HYDROFABRIC_DATASET_DIR}/nexus_data.geojson "" \
        ${REALIZATION_CONFIG_DATASET_DIR}/realization_config.json

    #Capture the return value to use as service exit code
    NGEN_RETURN=$?

    echo "$(print_date) serial ngen command finished with return value: ${NGEN_RETURN}"

    # Exit with the model's exit code
    return ${NGEN_RETURN}
}

# Sanity check that the output, hydrofabric, and config datasets are available (i.e., their directories are in place)
check_for_dataset_dir "${REALIZATION_CONFIG_DATASET_DIR}"
check_for_dataset_dir "${BMI_CONFIG_DATASET_DIR}"
# Don't require a partitioning dataset when only using a single node
if [ ${MPI_NODE_COUNT:?} -gt 1 ]; then
    check_for_dataset_dir "${PARTITION_DATASET_DIR:?No partition dataset directory defined}"
fi
check_for_dataset_dir "${HYDROFABRIC_DATASET_DIR}"
check_for_dataset_dir "${OUTPUT_DATASET_DIR}"

# Move to the output dataset mounted directory
cd ${OUTPUT_DATASET_DIR}

if [ "${WORKER_INDEX}" = "0" ]; then
    if [ "$(whoami)" = "${MPI_USER}" ]; then
        if [ ${MPI_NODE_COUNT:-1} -gt 1 ]; then
            exec_main_worker_ngen_run
        else
            exec_serial_ngen_run
        fi
    else
        echo "$(print_date) Starting SSH daemon on main worker"
        /usr/sbin/sshd -D &
        _SSH_D_PID="$!"

        # Start the SSH daemon as a power user, but then actually run the model as our MPI_USER
        echo "$(print_date) Running exec script as '${MPI_USER:?}'"
        # Do this by just re-running this script with the same args, but as the other user
        # The script will modify its behavior as needed depending on current user (see associated "if" for this "else")
        _EXEC_STRING="${0} ${@}"
        su ${MPI_USER:?} --session-command "${_EXEC_STRING}"
        #time su ${MPI_USER:?} --session-command "${_EXEC_STRING}"

        # Once running the model finishes, kill the SSH daemon process
        kill ${_SSH_D_PID}
    fi
else
    echo "$(print_date) Starting SSH daemon, waiting for main job"
    /usr/sbin/sshd -D &
    _SSH_D_PID="$!"

    touch ${RUN_SENTINEL}
    chown ${MPI_USER} ${RUN_SENTINEL}
    while [ -e ${RUN_SENTINEL} ]; do
        sleep 5
    done

    kill ${_SSH_D_PID}
fi