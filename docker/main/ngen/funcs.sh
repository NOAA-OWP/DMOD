#!/bin/bash

ALL_DATASET_DIR="/dmod/datasets"
DOCKER_SECRETS_DIR="/run/secrets"

print_date()
{
    date "+%Y-%m-%d,%H:%M:%S"
}

# Initialize some local MPI-related variables used by scripts
init_script_mpi_vars()
{
    MPI_USER="mpi"
    if [ "$(whoami)" = "${MPI_USER}" ]; then
        MPI_HOSTS_FILE="${HOME}/.mpi_hosts"
    else
        MPI_HOSTS_FILE="$(su ${MPI_USER} -c 'echo "${HOME}"')/.mpi_hosts"
    fi
    RUN_SENTINEL="/home/${MPI_USER}/.run_sentinel"
    MPI_RUN="mpirun"
}

init_ngen_executable_paths()
{
    NGEN_SERIAL_EXECUTABLE="/ngen/ngen/cmake_build_serial/ngen"
    NGEN_PARALLEL_EXECUTABLE="/ngen/ngen/cmake_build_parallel/ngen"
    # This will be symlinked to the parallel one currently
    NGEN_EXECUTABLE="/ngen/ngen/cmake_build/ngen"
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
    # TODO: Docker secret variable values need to be parameterized
    ACCESS_KEY_FILE="${DOCKER_SECRETS_DIR:?Docker secrets directory undefined}/${ACCESS_KEY_SECRET:-object_store_exec_user_name}"
    SECRET_KEY_FILE="${DOCKER_SECRETS_DIR:?}/${SECRET_KEY_SECRET:-object_store_exec_user_passwd}"

    test -n "${ACCESS_KEY:-}" && test -n "${SECRET_KEY:-}"
}

close_remote_workers()
{
    # Signal to remote worker nodes that they can stop their SSH process by removing this file
    if [ ${MPI_NODE_COUNT:-1} -gt 1 ]; then
        for i in $(echo "${MPI_HOST_STRING}" | sed 's/,/ /g'); do
            _HOST_NAME=$(echo "${i}" | awk -F: '{print $1}')
            ssh -q ${_HOST_NAME} rm ${RUN_SENTINEL} >/dev/null 2>&1
        done
        echo "$(print_date) DEBUG: closed other worker SSH processes"
    fi
}

exec_main_worker_ngen_run()
{
    # Write (split) hoststring to a proper file
    if [ -e "${MPI_HOSTS_FILE}" ]; then
        rm "${MPI_HOSTS_FILE}"
    fi

    echo "$(print_date) Preparing hosts file and checking ${MPI_NODE_COUNT} worker hosts are online for SSH"
    for i in $(echo "${MPI_HOST_STRING}" | sed 's/,/ /g'); do
        #echo "${i}" | awk -F: '{print $1 " slots=" $2}' >> "${MPI_HOSTS_FILE}"
        echo "${i}" | awk -F: '{print $1 ":" $2}' >> "${MPI_HOSTS_FILE}"
        _HOST_NAME=$(echo "${i}" | awk -F: '{print $1}')
        # Make sure all hosts are reachable, this also covers localhost
        until ssh -q ${_HOST_NAME} exit >/dev/null 2>&1; do :; done
        echo "DEBUG: Confirmed MPI host ${_HOST_NAME} is online for SSH"
    done

    # Execute the model on the linked data
    echo "$(print_date) Executing mpirun command for ngen on ${MPI_NODE_COUNT} workers"
    ${MPI_RUN:?} -f "${MPI_HOSTS_FILE}" -n ${MPI_NODE_COUNT} \
        ${NGEN_EXECUTABLE:?} ${HYDROFABRIC_DATASET_DIR}/catchment_data.geojson "" \
                ${HYDROFABRIC_DATASET_DIR}/nexus_data.geojson "" \
                ${CONFIG_DATASET_DIR}/realization_config.json \
                ${PARTITION_DATASET_DIR}/partition_config.json \
                --subdivided-hydrofabric

    #Capture the return value to use as service exit code
    NGEN_RETURN=$?

    echo "$(print_date) ngen mpirun command finished with return value: ${NGEN_RETURN}"

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
        ${CONFIG_DATASET_DIR}/realization_config.json

    #Capture the return value to use as service exit code
    NGEN_RETURN=$?

    echo "$(print_date) serial ngen command finished with return value: ${NGEN_RETURN}"

    # Exit with the model's exit code
    return ${NGEN_RETURN}
}

cleanup_sshuser_exit()
{
    if [ -n "${_SSH_D_PID:-}" ] && kill -s 0 "${_SSH_D_PID}" 2>/dev/null ; then
        kill "${_SSH_D_PID}"
    fi
}

# Sanity checking and initializing derived values, applicable to things executing ngen (i.e., calibration too)
ngen_sanity_checks_and_derived_init()
{
    # Run some sanity checks
    # Use complement of valid range like this in a few places to catch non-integer values
    if ! [ "${MPI_NODE_COUNT:-1}" -gt 0 ] 2>/dev/null; then
        echo "Error: invalid value '${MPI_NODE_COUNT}' given for MPI node count" > 2>&1
        exit 1
    fi
    if ! [ "${WORKER_INDEX:-0}" -ge 0 ] 2>/dev/null; then
        echo "Error: invalid value '${WORKER_INDEX}' given for MPI worker index/rank" > 2>&1
        exit 1
    fi

    # Assume that any of these being present implies the job will run via multiple MPI processes
    if [ -n "${MPI_NODE_COUNT:-}" ] || [ -n "${MPI_HOST_STRING:-}" ] || [ -n "${WORKER_INDEX:-}" ]; then
        #  ... and as such, they all must be present
        if [ -z "${MPI_HOST_STRING:-}" ]; then
            echo "Error: MPI host string not provided for job that will utilize MPI" > 2>&1
            exit 1
        fi
        if [ -z "${MPI_NODE_COUNT:-}" ]; then
            echo "Error: MPI node count not provided for job that will utilize MPI" > 2>&1
            exit 1
        fi
        if [ -z "${WORKER_INDEX:-}" ]; then
            echo "Error: MPI worker index not provided for job that will utilize MPI" > 2>&1
            exit 1
        fi
        # Also, require a partitioning config for any MPI job
        PARTITION_DATASET_DIR="${ALL_DATASET_DIR:?}/config/${PARTITION_DATASET_NAME:?No partition config dataset given}"
    fi

    # These serve as both sanity checks and initialization of some derived values
    OUTPUT_DATASET_DIR="${ALL_DATASET_DIR:?}/output/${OUTPUT_DATASET_NAME:?No output dataset given}"
    HYDROFABRIC_DATASET_DIR="${ALL_DATASET_DIR}/hydrofabric/${HYDROFABRIC_DATASET_NAME:?No hydrofabric dataset given}"
    CONFIG_DATASET_DIR="${ALL_DATASET_DIR}/config/${CONFIG_DATASET_NAME:?No composite config dataset given}"

    # Make sure that the output, hydrofabric, and config datasets are available (i.e., their directories are in place)
    check_for_dataset_dir "${CONFIG_DATASET_DIR}"
    # Don't require a partitioning dataset when only using a single node
    if [ ${MPI_NODE_COUNT:?} -gt 1 ]; then
        check_for_dataset_dir "${PARTITION_DATASET_DIR:?No partition dataset directory defined}"
    fi
    check_for_dataset_dir "${HYDROFABRIC_DATASET_DIR}"
    check_for_dataset_dir "${OUTPUT_DATASET_DIR}"
}

# Start SSHD, then create sentinel file (owned by MPI user) and loop while it exists
# Also, once SSHD is started, trap any exit with a function that will stop the SSHD process
# Expected to be used to ready worker nodes for MPI jobs, other than the primary node (index 0)
run_secondary_mpi_ssh_worker_node()
{
    echo "$(print_date) Starting SSH daemon, waiting for main job"
    /usr/sbin/sshd -D &
    _SSH_D_PID="$!"

    trap cleanup_sshuser_exit EXIT

    touch ${RUN_SENTINEL}
    chown ${MPI_USER} ${RUN_SENTINEL}
    while [ -e ${RUN_SENTINEL} ] && kill -s 0 "${_SSH_D_PID}" 2>/dev/null ; do
        sleep 5
    done
}