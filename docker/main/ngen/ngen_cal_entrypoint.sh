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
        --calibration-config-file)
            declare -x CALIBRATION_CONFIG_BASENAME="${2:?}"
            shift
            ;;
    esac
    shift
done

# TODO: (later) in both ngen and ngen-cal entrypoints, add controls for whether this is temp dir or output dataset dir
declare -x JOB_OUTPUT_WRITE_DIR="/tmp/job_output"

# Get some universally applicable functions and constants
source ./funcs.sh

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

start_calibration() {
    # Start ngen calibration
    if [ -n "${PARTITION_DATASET_DIR:-}" ]; then
        echo "$(print_date) Starting ngen calibration with parallel ngen execution"
    else
        echo "$(print_date) Starting ngen calibration with serial ngen execution"
    fi

    # Find calibration config, then copy to output dataset and use that
    if [ -n "${CALIBRATION_CONFIG_BASENAME:-}" ]; then
        #CALIBRATION_CONFIG_FILE=$(find ${OUTPUT_DATASET_DIR:?} -type f -name "${CALIBRATION_CONFIG_BASENAME}" -maxdepth 1 | head -1)
        _ORIG_CAL_CONFIG_FILE=$(find ${CONFIG_DATASET_DIR:?} -type f -name "${CALIBRATION_CONFIG_BASENAME}" -maxdepth 1 | head -1)
    else
        #CALIBRATION_CONFIG_FILE=$(find ${OUTPUT_DATASET_DIR:?} -type f -iname "*.yaml" -o -iname "*.yml" -maxdepth 1 | head -1)
        _ORIG_CAL_CONFIG_FILE=$(find ${CONFIG_DATASET_DIR:?} -type f -iname "*.yaml" -o -iname "*.yml" -maxdepth 1 | head -1)
    fi
    if [ -z "${_ORIG_CAL_CONFIG_FILE}" ]; then
        echo "Error: NGEN calibration yaml file not found" 2>&1
        exit 1
    fi
    cp -a ${_ORIG_CAL_CONFIG_FILE:?} ${OUTPUT_DATASET_DIR:?}/.
    CALIBRATION_CONFIG_FILE="${OUTPUT_DATASET_DIR:?}/$(basename ${_ORIG_CAL_CONFIG_FILE})"

    python3 -m ngen.cal "${CALIBRATION_CONFIG_FILE}"

    #Capture the return value to use as service exit code
    NGEN_RETURN=$?

    echo "$(print_date) ngen calibration finished with return value: ${NGEN_RETURN}"

    # TODO: (later) make sure outputs are handled properly, and that eventually we support toggling whether written to
    # TODO:     output dataset dir directly or somewhere else

    # Exit with the model's exit code
    return ${NGEN_RETURN}
}

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
            # Include partition config dataset too if appropriate
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
