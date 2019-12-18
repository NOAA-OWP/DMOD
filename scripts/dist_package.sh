#!/usr/bin/env sh

INFO='Build the distribution files for the local-source Python package at given path in the implied or specified Python virtual env'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

# Import shared default script startup source
. ${SCRIPT_PARENT_DIR}/shared/default_script_setup.sh

# Import shared functions used for python-dev-related scripts
. ${SCRIPT_PARENT_DIR}/shared/py_dev_func.sh

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} [opts] <directory>

Options:
    -c|--clean
        Clean up previously built dist artifacts (which happens
        by default), but don't build new artifacts.

    --venv <dir>
        Set the directory of the virtual environment to use.
        By default, the following directories will be checked,
        with the first apparently valid virtual env being used:
        - ./venv/
        - ./.venv/
        - ${SCRIPT_PARENT_DIR:-?}/venv/
        - ${SCRIPT_PARENT_DIR:-?}/.venv/

    --sys|--no-venv
        Set that the base system Python environment is to be
        used instead of a virtual environment.
        Note: conflicts with --venv option.
"
    echo "${_O}" 2>&1
}

# Make sure we end up in the same starting directory, and deactivate venv if it was activated
cleanup_before_exit()
{
    # Make sure we don't accidentally run this more than once
    CLEANUP_DONE=$((${CLEANUP_DONE:=0}+1))
    if [ ${CLEANUP_DONE} -gt 1 ]; then
        >&2 echo "Warning: cleanup function being run for ${CLEANUP_DONE} time"
    fi
    # Go back to shell starting dir
    cd "${STARTING_DIR:?}"

    # If the flag is set that a virtual environment was activated, then deactivate it
    if [ ${VENV_WAS_ACTIVATED:-1} -eq 0 ]; then
        >&2 echo "Deactiving active virtual env at ${VIRTUAL_ENV}"
        deactivate
    fi
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        -c|--clean)
            [ -n "${CLEAN_ONLY:-}" ] && usage && exit 1
            CLEAN_ONLY='true'
            ;;
        --venv)
            [ -n "${VENV_DIR:-}" ] && usage && exit 1
            [ -n "${USE_SYS_PYTHON:-}" ] && usage && exit 1
            VENV_DIR="$(py_dev_validate_venv_dir "${2}")"
            [ -z "${VENV_DIR:-}" ] && echo "Error: provided arg ${2} is not a valid virtual env directory" && exit 1
            shift
            ;;
        --sys|--no-venv)
            [ -n "${USE_SYS_PYTHON:-}" ] && usage && exit 1
            [ -n "${VENV_DIR:-}" ] && usage && exit 1
            USE_SYS_PYTHON='true'
            ;;
        *)
            [ -n "${PACKAGE_DIR:-}" ] && usage && exit 1
            [ ! -d "${1}" ] && >&2 echo "Error: package directory arg is not an existing directory" && usage && exit 1
            PACKAGE_DIR="${1}"
            ;;
    esac
    shift
done

# Unless --sys or --no-venv was set, make sure we have a valid VENV_DIR value, attempting to set a default if needed.
if [ -z "${USE_SYS_PYTHON:-}" ]; then
    # Look for a default venv to use if needed
    py_dev_detect_default_venv_directory

    # Bail here if a valid venv is not set
    [ -z "${VENV_DIR:-}" ] && echo "Error: no valid virtual env directory could be determined or was given" && exit 1
fi

# Take appropriate action to activate the virtual environment if needed
py_dev_activate_venv

# Trap to make sure we "clean up" script activity before exiting
trap cleanup_before_exit 0 1 2 3 6 15

# Finally, go into the package directory and build new dists
cd "${PACKAGE_DIR}"
if [ "${CLEAN_ONLY}" == 'true' ]; then
    py_dev_clean_dist
elif [ -n "${CLEAN_ONLY}" ]; then
    >&2 echo "Error: unexpected value set for variable CLEAN_ONLY (${CLEAN_ONLY}); exiting without building"
    exit 1
else
    py_dev_clean_dist && python setup.py sdist bdist_wheel
fi