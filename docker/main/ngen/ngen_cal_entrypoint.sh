#!/bin/bash
# Args are managed by the _generate_docker_cmd_args function in scheduler.py of dmod.scheduler

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

# Get some universally applicable functions and constants
source ./funcs.sh

ngen_sanity_checks_and_derived_init
init_script_mpi_vars
init_ngen_executable_paths

# Move to the output dataset mounted directory
cd ${OUTPUT_DATASET_DIR:?Output dataset directory not defined}

start_calibration() {
    # Start ngen calibration
    echo "$(print_date) Starting serial ngen calibration"

    # Find and use copy of config in output dataset
    CALIBRATION_CONFIG_FILE=$(find ${OUTPUT_DATASET_DIR:?} -type f -iname "*.yaml" -o -iname "*.yml" -maxdepth 1 | head -1)

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

# Copy config files to output dataset for record keeping, but only from the "main" worker node
# We can allow worker index to not be supplied when executing serially, so apply default substitution
if [ ${WORKER_INDEX:-0} -eq 0 ]; then
    # TODO: perform copy of configs to output dataset outside of image (in service) for better performance
    cp -a ${CONFIG_DATASET_DIR:?Config dataset directory not defined}/. ${OUTPUT_DATASET_DIR:?}
    if [ -n "${PARTITION_DATASET_DIR:-}" ]; then
        # Also, when partition config present, copy that for record keeping
        # TODO: perform copy of configs to output dataset outside of image (in service) for better performance
        cp -a ${PARTITION_DATASET_DIR}/. ${OUTPUT_DATASET_DIR:?}
    fi
fi

start_calibration
