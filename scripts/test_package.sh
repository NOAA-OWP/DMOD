#!/usr/bin/env sh

INFO='Run tests for the Python package rooted at the given directory'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

# Import shared default script startup source
. ${SCRIPT_PARENT_DIR}/shared/default_script_setup.sh

# Import shared functions used for python-dev-related scripts
. ${SCRIPT_PARENT_DIR}/shared/py_dev_func.sh

DEFAULT_TEST_DIR_BASENAME='test'
DEFAULT_UNIT_TEST_FILE_PATTERN="test_*.py"
DEFAULT_INTEGRATION_TEST_FILE_PATTERN="it_*.py"

# Basename for file in test directories that should be sourced and have functions run per global test exec (i.e., not
# once per individual test) to setup and teardown appropriate parts of the integration testing environment
INTEGRATION_TEST_SETUP_FILE_BASENAME="setup_it_env.sh"
# The valid argument options for aforementioned file
INTEGRATION_TEST_SETUP_FUNC="do_setup"
INTEGRATION_TEST_TEARDOWN_FUNC="do_teardown"

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

    --integration | -it
        Execute integration tests (identified as being in
        files named '${DEFAULT_INTEGRATION_TEST_FILE_PATTERN}') instead of typical unit tests
        (identified as being in files named '${DEFAULT_UNIT_TEST_FILE_PATTERN}')

    --setup-it
        Rather than run any tests, just execute the setup
        logic for integration tests for this package, without
        any teardown logic.  The expectation is that this be
        run to facilitate IDE-based execution (and debugging)
        of tests.

    --teardown-it
        Rather than run any tests, just execute the teardown
        logic for integration tests for this package, without
        any setup logic.  The expectation is that this be run
        once any desired testing is finished after having run
        --setup-it as described above.

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
        >&2 echo ""
        deactivate
    fi
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        --all|-a)
            [ -n "${TEST_FILE_PATTERN:-}" ] && usage && exit 1
            TEST_FILE_PATTERN='both'
            ;;
        --integration|-it)
            [ -n "${TEST_FILE_PATTERN:-}" ] && usage && exit 1
            TEST_FILE_PATTERN="${DEFAULT_INTEGRATION_TEST_FILE_PATTERN}"
            ;;
        -n|--test-dir-basename)
            [ -n "${TEST_DIR_BASENAME:-}" ] && usage && exit 1
            TEST_DIR_BASENAME="${2}"
            shift
            ;;
        --setup-it)
            [ -n "${DO_TEARDOWN_IT:-}" ] && usage && exit 1
            DO_SETUP_IT='true'
            ;;
        --teardown-it)
            [ -n "${DO_SETUP_IT:-}" ] && usage && exit 1
            DO_TEARDOWN_IT='true'
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

[ -z "${TEST_FILE_PATTERN}" ] && TEST_FILE_PATTERN="${DEFAULT_UNIT_TEST_FILE_PATTERN}"

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

exec_test_files()
{
    python -m unittest ${1} ${SET_VERBOSE:-}
}

find_and_exec_test_files()
{
    # Unit testing
    if [ "${1}" = "${DEFAULT_UNIT_TEST_FILE_PATTERN}" ]; then
        exec_test_files "$(find "${PACKAGE_TEST_DIRECTORY}" -type f -name "${1}")"
    # Integration testing, with existing setup file in directory
    elif [ -e "${PACKAGE_TEST_DIRECTORY}/${INTEGRATION_TEST_SETUP_FILE_BASENAME}" ]; then
        # Source the setup file
        . "${PACKAGE_TEST_DIRECTORY}/${INTEGRATION_TEST_SETUP_FILE_BASENAME}"
        # Then run the setup function
        ${INTEGRATION_TEST_SETUP_FUNC}
        _R=${?}
        if [ ${_R} -ne 0 ]; then
            >&2 echo ""
            >&2 echo "ERROR: integration testing failed - could not exec environment setup function (returned: ${_R})"
            >&2 echo ""
            exit ${_R}
        fi
        # Then execute all IT tests
        exec_test_files "$(find "${PACKAGE_TEST_DIRECTORY}" -type f -name "${1}")"
        # Finally, run the sourced teardown function
        ${INTEGRATION_TEST_TEARDOWN_FUNC}
    # Integration testing, but without the setup file in directory
    else
        exec_test_files "$(find "${PACKAGE_TEST_DIRECTORY}" -type f -name "${1}")"
    fi
}

echo "==========================================================================="

if [ "${DO_SETUP_IT}" = "true" ]; then
    # Source the setup file
    . "${PACKAGE_TEST_DIRECTORY}/${INTEGRATION_TEST_SETUP_FILE_BASENAME}"
    # Then run the setup function
    ${INTEGRATION_TEST_SETUP_FUNC}
elif [ "${DO_TEARDOWN_IT}" = "true" ]; then
    # Source the setup file
    . "${PACKAGE_TEST_DIRECTORY}/${INTEGRATION_TEST_SETUP_FILE_BASENAME}"
    # Then run the teardown function
    ${INTEGRATION_TEST_TEARDOWN_FUNC}
elif [ "${TEST_FILE_PATTERN}" == "both" ]; then
    echo "Running unit tests:"
    echo "--------------------------"
    find_and_exec_test_files "${DEFAULT_UNIT_TEST_FILE_PATTERN}"
    echo "=================================="
    echo "Running integration tests:"
    echo "--------------------------"
    find_and_exec_test_files "${DEFAULT_INTEGRATION_TEST_FILE_PATTERN}"
else
    find_and_exec_test_files "${TEST_FILE_PATTERN}"
fi

echo "==========================================================================="
