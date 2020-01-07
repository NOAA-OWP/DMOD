#!/usr/bin/env sh

INFO='Run tests for the Python package rooted at the given directory'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

# Import shared default script startup source
. ${SCRIPT_PARENT_DIR}/shared/default_script_setup.sh

# Import shared functions used for python-dev-related scripts
. ${SCRIPT_PARENT_DIR}/shared/py_dev_func.sh

DEFAULT_TEST_DIR_BASENAME='test'

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} [opts] <directory>

Options:
    --test-dir-basename | -n <name>
        Set the expected basename of the subdirectory in a
        (namespace) package directory where test files are
        expected (default: '${DEFAULT_TEST_DIR_BASENAME}')

    --venv <dir>
        Set the directory of the virtual environment to use.
        By default, the following directories will be checked,
        with the first apparently valid virtual env being used:
        - ./venv/
        - ./.venv/
        - ${SCRIPT_PARENT_DIR:-?}/venv/
        - ${SCRIPT_PARENT_DIR:-?}/.venv/

    -v
        Set verbose output.
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
        -n|--test-dir-basename)
            [ -n "${TEST_DIR_BASENAME:-}" ] && usage && exit 1
            TEST_DIR_BASENAME="${2}"
            shift
            ;;
        --venv)
            [ -n "${VENV_DIR:-}" ] && usage && exit 1
            VENV_DIR="$(py_dev_validate_venv_dir "${2}")"
            [ -z "${VENV_DIR:-}" ] && echo "Error: provided arg ${2} is not a valid virtual env directory" && exit 1
            shift
            ;;
        -v)
            [ -n "${SET_VERBOSE:-}" ] && usage && exit 1
            SET_VERBOSE='-v'
            ;;
        *)
            [ -n "${PACKAGE_DIR:-}" ] && usage && exit 1
            [ ! -d "${1}" ] && >&2 echo "Error: package directory arg is not an existing directory" && usage && exit 1
            PACKAGE_DIR="${1}"
            ;;
    esac
    shift
done

# Look for a default venv to use if needed
py_dev_detect_default_venv_directory

# Bail here if a valid venv is not set
[ -z "${VENV_DIR:-}" ] && echo "Error: no valid virtual env directory could be determined or was given" && exit 1

# Take appropriate action to activate the virtual environment if needed
py_dev_activate_venv

# Trap to make sure we "clean up" script activity before exiting
trap cleanup_before_exit 0 1 2 3 6 15

# Sanity check that the package's test directory exists; otherwise, they'll be no tests to run
PACKAGE_TEST_DIRECTORY="${PACKAGE_DIR}/${PACKAGE_NAMESPACE_ROOT:?}/${TEST_DIR_BASENAME:-${DEFAULT_TEST_DIR_BASENAME:?}}"
if [ ! -d "${PACKAGE_TEST_DIRECTORY}" ]; then
    echo "Error: expected test directory ${PACKAGE_TEST_DIRECTORY} not found"
    exit 1
fi

echo "==========================================================================="

if [ $(find "${PACKAGE_TEST_DIRECTORY}" -type f -name "test_*.py" | wc -l) -lt 1 ]; then
    echo "No test Python test files found in ${PACKAGE_TEST_DIRECTORY}"
else
    TEST_FILES="$(ls "${PACKAGE_TEST_DIRECTORY}"/test_*.py)"
    python -m unittest ${TEST_FILES} ${SET_VERBOSE:-}
fi

echo "==========================================================================="
