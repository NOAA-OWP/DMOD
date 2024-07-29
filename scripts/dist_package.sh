#!/usr/bin/env sh

INFO='Build the distribution files for the local-source Python package at given path in the implied or specified Python virtual env'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

# Set SHARED_FUNCS_DIR (as needed by default_script_setup.sh) to the correct path before using it to source its contents
SHARED_FUNCS_DIR="${SCRIPT_PARENT_DIR}/shared"
if [ ! -d "${SHARED_FUNCS_DIR}" ]; then
    >&2 echo "Error: could not find shared script functions script at expected location:"
    >&2 echo "    ${SHARED_FUNCS_DIR}"
    exit 1
fi

# Import shared default script startup source
. ${SHARED_FUNCS_DIR}/default_script_setup.sh

# Import shared functions used for python-dev-related scripts
. ${SHARED_FUNCS_DIR}/py_dev_func.sh

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
    # Assuming a VENV_DIR wasn't set via command line ...
    if [ -z "${VENV_DIR:-}" ]; then
        # Look for a default venv to use if needed
        py_dev_detect_default_venv_directory
        # Bail here if a valid venv is not set
        [ -z "${VENV_DIR:-}" ] && echo "Error: no valid virtual env directory could be determined or was given" && exit 1
    fi
    # Also make sure we validate the directory before proceeding
    py_dev_validate_venv_dir "${VENV_DIR}" > /dev/null
    # Then exit unless that was validated
    exit_with_if_non_zero $?
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
    py_dev_clean_dist && python -m build
fi
