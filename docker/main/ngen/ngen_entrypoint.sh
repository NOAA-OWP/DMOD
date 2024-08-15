#!/bin/bash
# Args are managed by the _generate_docker_cmd_args function in scheduler.py of dmod.scheduler

while [ ${#} -gt 0 ]; do
    case "${1}" in
        --config-dataset)
            declare -x CONFIG_DATASET_NAME="${2:?}"
            shift
            ;;
        --host-string)
            declare -x MPI_HOST_STRING="${2:?}"
            shift
            ;;
        --hydrofabric-dataset)
            declare -x HYDROFABRIC_DATASET_NAME="${2:?}"
            shift
            ;;
        --job-id)
            declare -x JOB_ID="${2:?}"
            shift
            ;;
        --node-count)
            declare -x MPI_NODE_COUNT="${2:?}"
            shift
            ;;
        --output-dataset)
            declare -x OUTPUT_DATASET_NAME="${2:?}"
            shift
            ;;
        --partition-dataset)
            declare -x PARTITION_DATASET_NAME="${2:?}"
            shift
            ;;
        --worker-index)
            declare -x WORKER_INDEX="${2:?}"
            shift
            ;;
        --primary-workers)
            declare -x PRIMARY_WORKERS="${2:?}"
            shift
            ;;
    esac
    shift
done

# TODO: (later) in both ngen and ngen-cal entrypoints, add controls for whether this is temp dir or output dataset dir
declare -x JOB_OUTPUT_WRITE_DIR="/tmp/job_output"

# Get some universally applicable functions and constants
source /ngen/funcs.sh

# Run make_data_local Python functions to make necessary data local
# Called for every worker, but Python code will make sure only one worker per node makes a call that has effect
py_funcs make_data_local ${WORKER_INDEX:-0} ${PRIMARY_WORKERS:-0}

ngen_sanity_checks_and_derived_init
init_script_mpi_vars
init_ngen_executable_paths

# Move to the output write directory
# TODO: (later) in both ngen and ngen-cal entrypoints, control whether this is needed, based on if write dir is output dataset dir
#cd ${OUTPUT_DATASET_DIR:?Output dataset directory not defined}
mkdir ${JOB_OUTPUT_WRITE_DIR:?}
chown ${MPI_USER}:${MPI_USER} ${JOB_OUTPUT_WRITE_DIR}
cd ${JOB_OUTPUT_WRITE_DIR}
#Needed for routing
if [ ! -e /dmod/datasets/linked_job_output ]; then
    ln -s ${JOB_OUTPUT_WRITE_DIR} /dmod/datasets/linked_job_output
fi

# We can allow worker index to not be supplied when executing serially
if [ "${WORKER_INDEX:-0}" = "0" ]; then
    if [ "$(whoami)" = "${MPI_USER:?MPI user not defined}" ]; then
        # This will only have an effect when running with multiple MPI nodes, so its safe to have even in serial exec
        trap close_remote_workers EXIT
        # Have "main" (potentially only) worker copy config files to output dataset for record keeping
        # TODO: (later) in ngen and ngen-cal entrypoints, consider adding controls for whether this is done or a simpler
        # TODO:     'cp' call, based on whether we write directly to output dataset dir or some other output write dir
        # Do a dry run first to sanity check directory and fail if needed before backgrounding process
        py_funcs tar_and_copy --dry-run --compress ${CONFIG_DATASET_DIR:?Config dataset directory not defined} config_dataset.tgz ${OUTPUT_DATASET_DIR:?}
        # Then actually run the archive and copy function in the background
        py_funcs tar_and_copy --compress ${CONFIG_DATASET_DIR:?} config_dataset.tgz ${OUTPUT_DATASET_DIR:?} &
        _CONFIG_COPY_PROC=$!
        # If there is partitioning, which implies multi-processing job ...
        if [ -n "${PARTITION_DATASET_DIR:-}" ]; then
            # Include partition config dataset too if appropriate, though for simplicity, just copy directly
            cp -a ${PARTITION_DATASET_DIR}/. ${OUTPUT_DATASET_DIR:?}
            # Then run execution
            exec_main_worker_ngen_run

            # TODO: (later) in ngen and ngen-cal entrypoints, add controls for whether this is done base on whether we
            # TODO:     are writing directly to output dataset dir or some other output write dir; this will be
            # TODO:     important once netcdf output works
            # Then gather output from all worker hosts
            py_funcs gather_output ${MPI_HOST_STRING:?} ${JOB_OUTPUT_WRITE_DIR:?}
            # Then wait at this point (if necessary) for our background config copy to avoid taxing things
            echo "$(print_date) Waiting for compression and copying of configuration files to output dataset"
            wait ${_CONFIG_COPY_PROC}
            echo "$(print_date) Compression/copying of config data to output dataset complete"
            echo "$(print_date) Copying results to output dataset"
            py_funcs move_job_output --job_id ${JOB_ID:?} ${JOB_OUTPUT_WRITE_DIR} to_directory ${OUTPUT_DATASET_DIR:?}
            echo "$(print_date) Results copied to output dataset"
        # Otherwise, we just have a serial job ...
        else
            # Execute it first
            exec_serial_ngen_run

            # TODO: (later) in ngen and ngen-cal entrypoints, add controls for whether this is done base on whether we
            # TODO:     are writing directly to output dataset dir or some other output write dir; this will be
            # TODO:     important once netcdf output works
            echo "$(print_date) Waiting for compression and copying of configuration files to output dataset"
            wait ${_CONFIG_COPY_PROC}
            echo "$(print_date) Compression/copying of config data to output dataset complete"

            echo "$(print_date) Copying results to output dataset"
            py_funcs move_job_output --job_id ${JOB_ID:?} ${JOB_OUTPUT_WRITE_DIR} to_directory ${OUTPUT_DATASET_DIR:?}
            echo "$(print_date) Results copied to output dataset"
        fi
    else
        # Start SSHD on the main worker if have an MPI job
        if [ -n "${PARTITION_DATASET_DIR:-}" ]; then
            echo "$(print_date) Starting SSH daemon on main worker"
            /usr/sbin/sshd -D &
            _SSH_D_PID="$!"

            trap cleanup_sshuser_exit EXIT
        fi

        # Make sure we run the model as our MPI_USER
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
