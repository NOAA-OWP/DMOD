#!/usr/bin/env sh

NAME="`basename ${0}`"
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

# Source the main project .env file if we find it in the directory one level above the parent of this script
if [ -e "${SCRIPT_PARENT_DIR}/../.env" ]; then
    . "${SCRIPT_PARENT_DIR}/../.env"
fi

# Default to using the directory of this script as a base directory
DEFAULT_BASE_DIR="${SCRIPT_PARENT_DIR}"

# Keep note of whether the script has activated a virtual python environment, and must later deactivate it
# Uses the shell-style conventions of 0 => true and 1 => false
VENV_WAS_ACTIVATED=1

# Keep track of the working directory for the parent shell at the time the script was called
STARTING_DIR="$(pwd)"

# Name of dist/pip package when installing, which should be available from sourced .env
PACKAGE_DIST_NAME="${PYTHON_PACKAGE_DIST_NAME_REQUEST_SERVICE:?}"

# Name for package when running unit tests
UNIT_TESTED_PACKAGE_NAME='request-handler.nwmaas.test'

# Source several external common/shared 'pkb_*' functions for build scripts
PKB_SOURCE_FILE="${SCRIPT_PARENT_DIR}/../scripts/package_build.sh"
. "${PKB_SOURCE_FILE}" || exit 1

usage()
{
    pkb_default_usage
}

# If the CLEAN_FINISH option was set to clean up at the end, check that the action being run is compatible
check_clean_finish_compat()
{
    if [ -n "${CLEAN_FINISH:-}" ]; then
        # For now, just use default logic (though potentially add additional, script-specific logic for bailing)
        pkb_check_clean_finish_compat
    fi
}

# Reset shell state the script may have modified - like the working directory and virtual environment - then exit
reset_and_exit()
{
    # No custom, special stuff right now, but still pass -r arg to not exit until we get back here
    pkb_reset_and_exit -r
    # If a code was passed (as the first arg), use it when exiting; assume 0 if nothing provided
    exit ${1:-0}
}

sanity_checks()
{
    pkb_default_sanity_checks
}

pkb_default_arg_parse ${@}

sanity_checks

pkb_handle_venv_activation

cd "${BASE_DIR:?}"

if [ "${ACTION}" == "build" ]; then
    pkb_build
elif [ "${ACTION}" == "clean" ]; then
    pkb_clean_all
    # Supports --clean-finish, but just ignore for this case
elif [ "${ACTION}" == "test" ]; then
    pkb_run_tests
elif [ "${ACTION}" == "upgrade" ]; then
    pkb_build_and_upgrade
    [ -n "${CLEAN_FINISH}" ] && pkb_clean_all
else
    echo "Error: unknown action '${ACTION}'"
    reset_and_exit 1
fi

reset_and_exit