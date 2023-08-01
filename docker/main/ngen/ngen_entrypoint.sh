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
cd ${OUTPUT_DATASET_DIR}

if [ "${WORKER_INDEX}" = "0" ]; then
    if [ "$(whoami)" = "${MPI_USER}" ]; then
        # Blah comment
        trap close_remote_workers EXIT
        # Have "main" worker copy config files to output dataset for record keeping
        # TODO: perform copy of configs to output dataset outside of image (in service) for better performance
        cp -a ${CONFIG_DATASET_DIR}/. ${OUTPUT_DATASET_DIR}
        if [ -n "${PARTITION_DATASET_DIR:-}" ]; then
            # Include partition config dataset too if appropriate
            # TODO: perform copy of configs to output dataset outside of image (in service) for better performance
            cp -a ${PARTITION_DATASET_DIR}/. ${OUTPUT_DATASET_DIR}
            exec_main_worker_ngen_run
        else
            exec_serial_ngen_run
        fi
    else
        echo "$(print_date) Starting SSH daemon on main worker"
        /usr/sbin/sshd -D &
        _SSH_D_PID="$!"

        trap cleanup_sshuser_exit EXIT

        # Start the SSH daemon as a power user, but then actually run the model as our MPI_USER
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