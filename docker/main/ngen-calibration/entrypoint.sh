#!/bin/bash
# Args are managed by the _generate_docker_cmd_args function in scheduler.py of dmod.scheduler

# TODO: Docker secret variable values need to be parameterized
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
RUN_SENTINEL="/home/${MPI_USER}/.run_sentinel"

MPI_RUN="mpirun"

NGEN_SERIAL_EXECUTABLE="/ngen/ngen/cmake_build_serial/ngen"
NGEN_PARALLEL_EXECUTABLE="/ngen/ngen/cmake_build_parallel/ngen"
# This will be symlinked to the parallel one currently
NGEN_EXECUTABLE="/ngen/ngen/cmake_build/ngen"

ALL_DATASET_DIR="/dmod/datasets"

while [ ${#} -gt 0 ]; do
    case "${1}" in
        --config-dataset)
            CONFIG_DATASET_NAME="${2:?}"
            shift
            ;;
        --host-string)
            MPI_HOST_STRING="${2:?}"
            shift
            ;;
        --hydrofabric-dataset)
            HYDROFABRIC_DATASET_NAME="${2:?}"
            shift
            ;;
        --job-id)
            JOB_ID="${2:?}"
            shift
            ;;
        --node-count)
            MPI_NODE_COUNT="${2:?}"
            shift
            ;;
        --output-dataset)
            OUTPUT_DATASET_NAME="${2:?}"
            shift
            ;;
        --partition-dataset)
            PARTITION_DATASET_NAME="${2:?}"
            shift
            ;;
        --worker-index)
            WORKER_INDEX="${2:?}"
            shift
            ;;
    esac
    shift
done

# Run some sanity checks
# TODO: not sure if this is appropriate or not for calibration exec
if [ -z "${MPI_HOST_STRING:?No MPI hosts string given}" ]; then
    echo "Error: MPI host string is empty" > 2>&1
    exit 1
fi
# Using complement of valid range to catch non-integer values
if ! [ "${WORKER_INDEX:?No MPI worker index/rank given}" -ge 0 ] 2>/dev/null; then
    echo "Error: invalid value '${WORKER_INDEX}' given for MPI worker index/rank" > 2>&1
    exit 1
fi
if ! [ "${MPI_NODE_COUNT:?No MPI node count provided}" -gt 0 ] 2>/dev/null; then
    echo "Error: invalid value '${MPI_NODE_COUNT}' given for MPI node count" > 2>&1
    exit 1
fi

# These serve as both sanity checks and initialization of some derived values
OUTPUT_DATASET_DIR="${ALL_DATASET_DIR:?}/output/${OUTPUT_DATASET_NAME:?No output dataset provided}"
HYDROFABRIC_DATASET_DIR="${ALL_DATASET_DIR}/hydrofabric/${HYDROFABRIC_DATASET_NAME:?No hydrofabric dataset provided}"
CONFIG_DATASET_DIR="${ALL_DATASET_DIR}/config/${CONFIG_DATASET_NAME:?No config dataset provided}"

# Require a partitioning config unless using just a single node for serial exec
# TODO: account for CPU count more appropriately when that gets merged in for ngen image
if [ ${MPI_NODE_COUNT:?No MPI node count provided} -gt 1 ]; then
    PARTITION_DATASET_DIR="${ALL_DATASET_DIR:?}/config/${PARTITION_DATASET_NAME:?No partition config dataset name given}"
fi

print_date() {
    date "+%Y-%m-%d,%H:%M:%S"
}

check_for_dataset_dir() {
    # Dataset dir is $1
    _CATEG="$(echo "${1}" | sed "s|${ALL_DATASET_DIR}/\([^/]*\)/.*|\1|" | awk '{print toupper($0)}')"
    if [ ! -d "${1}" ]; then
        echo "Error: expected ${_CATEG} dataset directory ${1} not found." 2>&1
        exit 1
    fi
}

load_object_store_keys_from_docker_secrets() {
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

start_calibration() {
    # Start ngen calibration
    echo "$(print_date) Starting serial ngen calibration"

    # Find and use copy of config in output dataset
    CALIBRATION_CONFIG_FILE=$(find ${OUTPUT_DATASET_DIR} -name "*.yaml" -maxdepth 1 | head -1)

    if [ -z "${CALIBRATION_CONFIG_FILE}" ]; then
        echo "Error: NGEN calibration yaml file not found" 2>&1
        exit 1
    fi
    python3 -m ngen.cal "${CALIBRATION_CONFIG_FILE}"

    #Capture the return value to use as service exit code
    NGEN_RETURN=$?

    echo "$(print_date) ngen calibration finished with return value: ${NGEN_RETURN}"

    # Exit with the model's exit code
    return ${NGEN_RETURN}
}

# Sanity check that the output, hydrofabric, and config datasets are available (i.e., their directories are in place)
check_for_dataset_dir "${OUTPUT_DATASET_DIR}"
check_for_dataset_dir "${CONFIG_DATASET_DIR}"
if [ -n "${PARTITION_DATASET_DIR:-}" ]; then
    check_for_dataset_dir "${PARTITION_DATASET_DIR:?No partition dataset directory defined}"
fi
check_for_dataset_dir "${HYDROFABRIC_DATASET_DIR}"

# Copy config files to output dataset for record keeping, but only from the "main" worker node
if [ ${WORKER_INDEX} -eq 0 ]; then
    # TODO: perform copy of configs to output dataset outside of image (in service) for better performance
    cp -a ${CONFIG_DATASET_DIR}/. ${OUTPUT_DATASET_DIR}
    if [ -n "${PARTITION_DATASET_DIR:-}" ]; then
        # Also, when partition config present, copy that for record keeping
        # TODO: perform copy of configs to output dataset outside of image (in service) for better performance
        cp -a ${PARTITION_DATASET_DIR}/. ${OUTPUT_DATASET_DIR}
    fi
fi

# Move to the output dataset mounted directory
cd ${OUTPUT_DATASET_DIR}

start_calibration
