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
        --calibration-config-file)
            CALIBRATION_CONFIG_BASENAME="${2:?}"
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
    if [ -n "${PARTITION_DATASET_DIR:-}" ]; then
        echo "$(print_date) Starting ngen calibration with parallel ngen execution"
    else
        echo "$(print_date) Starting ngen calibration with serial ngen execution"
    fi

    # Find and use copy of config in output dataset
    if [ -n "${CALIBRATION_CONFIG_BASENAME:-}" ]; then
        CALIBRATION_CONFIG_FILE=$(find ${OUTPUT_DATASET_DIR:?} -type f -name "${CALIBRATION_CONFIG_BASENAME}" -maxdepth 1 | head -1)
    else
        CALIBRATION_CONFIG_FILE=$(find ${OUTPUT_DATASET_DIR:?} -type f -iname "*.yaml" -o -iname "*.yml" -maxdepth 1 | head -1)
    fi

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

# We can allow worker index to not be supplied when executing serially
if [ "${WORKER_INDEX:-0}" = "0" ]; then
    if [ "$(whoami)" = "${MPI_USER:?MPI user not defined}" ]; then
        # This will only have an effect when running with multiple MPI nodes, so its safe to have even in serial exec
        trap close_remote_workers EXIT
        # Have "main" (potentially only) worker copy config files to output dataset for record keeping
        # TODO: perform copy of configs to output dataset outside of image (in service) for better performance
        cp -a ${CONFIG_DATASET_DIR:?Config dataset directory not defined}/. ${OUTPUT_DATASET_DIR:?}
        if [ -n "${PARTITION_DATASET_DIR:-}" ]; then
            # Include partition config dataset too if appropriate
            # TODO: perform copy of configs to output dataset outside of image (in service) for better performance
            cp -a ${PARTITION_DATASET_DIR}/. ${OUTPUT_DATASET_DIR:?}
        fi

        # Run the same function to execute ngen_cal (it's config will handle whether MPI is used internally)
        start_calibration
    else
        # Start SSHD on the main worker if have an MPI job
        if [ -n "${PARTITION_DATASET_DIR:-}" ]; then
            echo "$(print_date) Starting SSH daemon on main worker"
            /usr/sbin/sshd -D &
            _SSH_D_PID="$!"

            trap cleanup_sshuser_exit EXIT
        fi

        # Make sure we run ngen/ngen-cal as our MPI_USER
        echo "$(print_date) Running exec script as '${MPI_USER:?}'"
        # Do this by just re-running this script with the same args, but as the other user
        # The script will modify its behavior as needed depending on current user (see associated "if" for this "else")
        _EXEC_STRING="${0} ${@}"
        su ${MPI_USER:?} --session-command "${_EXEC_STRING}"
        #time su ${MPI_USER:?} --session-command "${_EXEC_STRING}"
    fi
else
    run_secondary_mpi_ssh_worker_node
fi
