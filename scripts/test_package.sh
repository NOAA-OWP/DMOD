#!/usr/bin/env sh

INFO='Run tests for the Python package rooted at the given directory'
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

# Import shared functions used for Docker-dev-related scripts
. ${SHARED_FUNCS_DIR}/docker_dev_func.sh

DEFAULT_TEST_DIR_BASENAME='test'
DEFAULT_UNIT_TEST_FILE_PATTERN="test_*.py"
DEFAULT_INTEGRATION_TEST_FILE_PATTERN="it_*.py"

# Basename for file in test directories that should be sourced and have functions run per global test exec (i.e., not
# once per individual test) to setup and teardown appropriate parts of the integration testing environment
INTEGRATION_TEST_SETUP_FILE_BASENAME="setup_it_env.sh"
# The valid argument options for aforementioned file
INTEGRATION_TEST_SETUP_FUNC="do_setup"
INTEGRATION_TEST_TEARDOWN_FUNC="do_teardown"

# A basename for testing-specific environment file (i.e., like a .env file)
TEST_ENV_FILE_BASENAME='.test_env'

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} [opts] <directory>

Options:
    --generate-config | -g
        Just generate the global '.test_env' config file, if it
        does not already exist, without running tests

    --test-class <class_pattern>
        Specify (as a matching pattern, not an guaranteed
        exact name) the name of a particular class for which
        tests should be run

    --test-method <method_pattern>
        Specify (as a matching pattern, not an guaranteed
        exact name) the name of a particular method for which
        tests should be run

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

verbose_output_both()
{
    local _NL=""

    if [ "${1}" = "-n" ]; then
        _NL="${1}"
        shift
    fi

    if [ -n "${SET_VERBOSE:-}" ]; then
        echo "${@}" 2>&1
        [ -n "${_NL}" ] && echo "" 2>&1
    fi
}

generate_test_config()
{
    if [ -e "${PROJECT_ROOT:?No project root set}/${TEST_ENV_FILE_BASENAME:?No test env basename set}" ]; then
        # Add a little output if JUST_GEN_CONFIG was set and the config already exists
        if [ -n "${JUST_GEN_CONFIG:-}" ]; then
            echo "Project global ${TEST_ENV_FILE_BASENAME} already exists; exiting"
        fi
    else
        # If file doesn't already exist, create a global .test_env file

        # Generate a random value for things below that we don't set explicitly
        _PY_CODE="import random; import string; print(''.join(random.choice(string.ascii_letters) for i in range(32)))"
        _RAND="$(python -c "${_PY_CODE}")"

        # Cat the example file and set the value strings, either specifically or with randomized values
        cat "${PROJECT_ROOT}/example_test_env" \
            | sed 's/\(IT_REDIS_CONTAINER_NAME=\).*/\1"it_redis_container"/' \
            | sed 's/\(IT_REDIS_CONTAINER_HOST_PORT=\).*/\119639/' \
            | sed "s/\(IT_REDIS_CONTAINER_PASS=\).*/\1\"${_RAND}\"/" > "${PROJECT_ROOT:?}/${TEST_ENV_FILE_BASENAME:?}"
    fi
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
        --generate-config|-g)
            [ -n "${JUST_GEN_CONFIG:-}" ] && usage && exit 1
            JUST_GEN_CONFIG='true'
            shift
            ;;
        -h|--help|-help)
            usage
            exit
            ;;
        --all|-a)
            [ -n "${TEST_FILE_PATTERN:-}" ] && usage && exit 1
            # Also, balk at anything else if we've asked to just generate a config
            [ -n "${JUST_GEN_CONFIG:-}" ] && usage && exit 1
            TEST_FILE_PATTERN='both'
            ;;
        --integration|-it)
            [ -n "${TEST_FILE_PATTERN:-}" ] && usage && exit 1
            # Also, balk at anything else if we've asked to just generate a config
            [ -n "${JUST_GEN_CONFIG:-}" ] && usage && exit 1
            TEST_FILE_PATTERN="${DEFAULT_INTEGRATION_TEST_FILE_PATTERN}"
            ;;
        -n|--test-dir-basename)
            [ -n "${TEST_DIR_BASENAME:-}" ] && usage && exit 1
            # Also, balk at anything else if we've asked to just generate a config
            [ -n "${JUST_GEN_CONFIG:-}" ] && usage && exit 1
            TEST_DIR_BASENAME="${2}"
            shift
            ;;
        --setup-it)
            [ -n "${DO_TEARDOWN_IT:-}" ] && usage && exit 1
            # Also, balk at anything else if we've asked to just generate a config
            [ -n "${JUST_GEN_CONFIG:-}" ] && usage && exit 1
            DO_SETUP_IT='true'
            ;;
        --test-class)
            [ -n "${TEST_CLASS_PATTERN:-}" ] && usage && exit
            # Also, balk at anything else if we've asked to just generate a config
            [ -n "${JUST_GEN_CONFIG:-}" ] && usage && exit 1
            TEST_CLASS_PATTERN="${2}"
            shift
            ;;
        --test-method)
            [ -n "${TEST_METHOD_PATTERN:-}" ] && usage && exit
            # Also, balk at anything else if we've asked to just generate a config
            [ -n "${JUST_GEN_CONFIG:-}" ] && usage && exit 1
            TEST_METHOD_PATTERN="${2}"
            shift
            ;;
        --teardown-it)
            [ -n "${DO_SETUP_IT:-}" ] && usage && exit 1
            # Also, balk at anything else if we've asked to just generate a config
            [ -n "${JUST_GEN_CONFIG:-}" ] && usage && exit 1
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
            # Also, balk at anything else if we've asked to just generate a config
            [ -n "${JUST_GEN_CONFIG:-}" ] && usage && exit 1
            [ ! -d "${1}" ] && >&2 echo "Error: package directory arg is not an existing directory" && usage && exit 1
            PACKAGE_DIR="${1}"
            ;;
    esac
    shift
done

verbose_output_both -n "Generating test config"
generate_test_config
verbose_output_both -n "Finished test config generation"

# If this was set, then exit after generating the config
[ -n "${JUST_GEN_CONFIG:-}" ] && exit

[ -z "${TEST_FILE_PATTERN}" ] && TEST_FILE_PATTERN="${DEFAULT_UNIT_TEST_FILE_PATTERN}"

verbose_output_both -n "Starting detecting default venv"\
# Look for a default venv to use if needed
py_dev_detect_default_venv_directory
verbose_output_both -n "Finished detecting default venv"

# Bail here if a valid venv is not set
[ -z "${VENV_DIR:-}" ] && echo "Error: no valid virtual env directory could be determined or was given" && exit 1

# Take appropriate action to activate the virtual environment if needed
verbose_output_both -n "Activating venv if appropriate"
py_dev_activate_venv
verbose_output_both -n "Logic for venv activation completed"

# Trap to make sure we "clean up" script activity before exiting
trap cleanup_before_exit 0 1 2 3 6 15

verbose_output_both -n "Cleaning up trailing slash for directory if present"

# Clean up trailing slash if included on package dir arg, as it seems to mess things up
PACKAGE_DIR="$(echo "${PACKAGE_DIR}" | sed 's|\(.*\)/$|\1|')"
# Clean up relative ./ if included on package dir arg, as it breaks unittest
PACKAGE_DIR="$(echo "${PACKAGE_DIR}" | sed 's|\./\(.*\)$|\1|')"
# Sanity check that the package's test directory exists; otherwise, they'll be no tests to run
PACKAGE_TEST_DIRECTORY="${PACKAGE_DIR}/${PACKAGE_NAMESPACE_ROOT:?}/${TEST_DIR_BASENAME:-${DEFAULT_TEST_DIR_BASENAME:?}}"
if [ ! -d "${PACKAGE_TEST_DIRECTORY}" ]; then
    echo "Error: expected test directory ${PACKAGE_TEST_DIRECTORY} not found"
    exit 1
fi

exec_test_files()
{
    _TOP_DIR="`pwd`"
    _ADJUSTED_TEST_DIR="`echo "${1}" | sed \"s|${PACKAGE_DIR}/||\"`"
    cd "${PACKAGE_DIR}"
    if [ -n "${TEST_CLASS_PATTERN:-}" ] || [ -n "${TEST_METHOD_PATTERN:-}" ]; then
        python -m unittest -k ${TEST_CLASS_PATTERN:-}.${TEST_METHOD_PATTERN:-} ${_ADJUSTED_TEST_DIR} ${SET_VERBOSE:-}
        _EXEC_FIlES_R=${?}
    else
        python -m unittest ${_ADJUSTED_TEST_DIR} ${SET_VERBOSE:-}
        _EXEC_FIlES_R=${?}
    fi
    cd "${_TOP_DIR}"
    return ${_EXEC_FIlES_R}
}

source_it_env_and_funcs()
{
    # Source the setup file
    . "${PACKAGE_TEST_DIRECTORY}/${INTEGRATION_TEST_SETUP_FILE_BASENAME}"

    # Source any global testing env settings
    if [ -e "${PROJECT_ROOT}/${TEST_ENV_FILE_BASENAME}" ]; then
        . "${PROJECT_ROOT}/${TEST_ENV_FILE_BASENAME}"
    fi

    # Then, source any package-specific testing env settings (which should allow these to override earlier sourced values)
    if [ -e "${PACKAGE_TEST_DIRECTORY}/${TEST_ENV_FILE_BASENAME}" ]; then
        . "${PACKAGE_TEST_DIRECTORY}/${TEST_ENV_FILE_BASENAME}"
    fi
}

find_and_exec_test_files()
{
    # Unit testing
    if [ "${1}" = "${DEFAULT_UNIT_TEST_FILE_PATTERN}" ]; then
        exec_test_files "$(find "${PACKAGE_TEST_DIRECTORY}" -type f -name "${1}")"
        return ${?}
    # Integration testing, with existing setup file in directory
    elif [ -e "${PACKAGE_TEST_DIRECTORY}/${INTEGRATION_TEST_SETUP_FILE_BASENAME}" ]; then
        # Source the setup file and env
        source_it_env_and_funcs
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
        _R=${?}
        # Finally, run the sourced teardown function
        ${INTEGRATION_TEST_TEARDOWN_FUNC}
        return ${_R}
    # Integration testing, but without the setup file in directory
    else
        exec_test_files "$(find "${PACKAGE_TEST_DIRECTORY}" -type f -name "${1}")"
        return ${?}
    fi
}

echo "==========================================================================="

if [ "${DO_SETUP_IT}" = "true" ]; then
    # Source the setup file and env
    [ -n "${SET_VERBOSE:-}" ] && echo "Sourcing integration testing functions" 2>&1 && echo "" 2>&1
    source_it_env_and_funcs
    [ -n "${SET_VERBOSE:-}" ] && echo "Setting up integration tests environment" 2>&1 && echo "" 2>&1
    # Then run the setup function
    ${INTEGRATION_TEST_SETUP_FUNC}
elif [ "${DO_TEARDOWN_IT}" = "true" ]; then
    # Source the setup file and env
    [ -n "${SET_VERBOSE:-}" ] && echo "Sourcing integration testing functions" 2>&1 && echo "" 2>&1
    source_it_env_and_funcs
    # Then run the teardown function
    [ -n "${SET_VERBOSE:-}" ] && echo "Tearing down integration tests environment" 2>&1 && echo "" 2>&1
    ${INTEGRATION_TEST_TEARDOWN_FUNC}
elif [ "${TEST_FILE_PATTERN}" = "both" ]; then
    echo "Running unit tests:"
    echo "--------------------------"
    find_and_exec_test_files "${DEFAULT_UNIT_TEST_FILE_PATTERN}"
    _R1=${?}
    echo "=================================="
    echo "Running integration tests:"
    echo "--------------------------"
    find_and_exec_test_files "${DEFAULT_INTEGRATION_TEST_FILE_PATTERN}"
    _R2=${?}
    _R_FINAL=$((_R1+_R2))

else
    [ -n "${SET_VERBOSE:-}" ] && echo "Executing unit test files" 2>&1 && echo "" 2>&1
    find_and_exec_test_files "${TEST_FILE_PATTERN}"
    _R_FINAL=${?}
fi

echo "==========================================================================="
exit ${_R_FINAL}
