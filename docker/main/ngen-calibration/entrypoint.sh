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
# TODO: wire up $10
# $10 will be the name of the calibration configuration dataset (which will imply a directory location)

# Not yet supported
# no-op
MPI_NODE_COUNT="${1:?No MPI node count given}"
# no-op
MPI_HOST_STRING="${2:?No MPI host string given}"
# no-op
PARTITION_DATASET_NAME="${9:?}"

JOB_ID=${3:?No Job id given}
WORKER_INDEX=${4:?No worker index given}

OUTPUT_DATASET_NAME="${5:?}"
HYDROFABRIC_DATASET_NAME="${6:?}"
REALIZATION_CONFIG_DATASET_NAME="${7:?}"
BMI_CONFIG_DATASET_NAME="${8:?}"
CALIBRATION_CONFIG_DATASET_NAME="${10:?}"

ACCESS_KEY_SECRET="object_store_exec_user_name"
SECRET_KEY_SECRET="object_store_exec_user_passwd"
DOCKER_SECRETS_DIR="/run/secrets"
ACCESS_KEY_FILE="${DOCKER_SECRETS_DIR}/${ACCESS_KEY_SECRET}"
SECRET_KEY_FILE="${DOCKER_SECRETS_DIR}/${SECRET_KEY_SECRET}"

NGEN_EXECUTABLE="/ngen/ngen/cmake_build/ngen"

ALL_DATASET_DIR="/dmod/datasets"
OUTPUT_DATASET_DIR="${ALL_DATASET_DIR}/output/${OUTPUT_DATASET_NAME}"
HYDROFABRIC_DATASET_DIR="${ALL_DATASET_DIR}/hydrofabric/${HYDROFABRIC_DATASET_NAME}"
REALIZATION_CONFIG_DATASET_DIR="${ALL_DATASET_DIR}/config/${REALIZATION_CONFIG_DATASET_NAME}"
BMI_CONFIG_DATASET_DIR="${ALL_DATASET_DIR}/config/${BMI_CONFIG_DATASET_NAME}"
PARTITION_DATASET_DIR="${ALL_DATASET_DIR}/config/${PARTITION_DATASET_NAME}"
CALIBRATION_CONFIG_DATASET_DIR="${ALL_DATASET_DIR}/config/${CALIBRATION_CONFIG_DATASET_NAME}"

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
check_for_dataset_dir "${REALIZATION_CONFIG_DATASET_DIR}"
check_for_dataset_dir "${BMI_CONFIG_DATASET_DIR}"
check_for_dataset_dir "${PARTITION_DATASET_DIR}"
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
