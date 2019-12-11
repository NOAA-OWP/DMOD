#!/usr/bin/env sh

NAME="`basename ${0}`"
# Default to using the directory of this script as a base directory
DEFAULT_BASE_DIR="$(cd "$(dirname "${0}")"; pwd)"
# Keep note of whether the script has activated a virtual python environment, and must later deactivate it
# Uses the shell-style conventions of 0 => true and 1 => false
VENV_WAS_ACTIVATED=1
# Keep track of the working directory for the parent shell at the time the script was called
STARTING_DIR=`pwd`
# Name for package when running unit tests
UNIT_TESTED_PACKAGE_NAME='communication.nwmaas.test'

usage()
{
    local _O="Usage:
    ${NAME} -h|-help|--help
    ${NAME} [options] <action>

Options:
    -d|--base_dir <dir_path>
        Set the base directory from which to run specified action(s)
        Default: ${DEFAULT_BASE_DIR}

    --clean-finish
        After specified action(s) performed, also run 'clean' action
        Note: not compatible with all actions; e.g., 'build'

    --venv <virtual_env_dir>
        Set the directory of the virtual environment to load
        (Required for 'test' and 'upgrade'; unsupported otherwise)

    -v|--verbose
        Increased verbosity where supported

Actions:
    build
        Build new distribution files for the project package

    clean
        Clean up any directories and artifacts from a previous build

    test
        Run tests for the package
        (Requires '--venv' option to specify testing environment)

    upgrade
        Perform the steps of a 'clean' and a 'build', and then install
        built distribution files into a local environment
        (Requires '--venv' option to specify)
"
    echo "${_O}" 2>&1
}

get_egg_info_dir()
{
    if [ -z "${EGG_DIR:-}" ]; then
        _EGG_DIR_BASE=`ls "${BASE_DIR}" | grep -e '.*\.egg-info$'`
        if [ -n "${_EGG_DIR_BASE:-}" ]; then
            EGG_DIR="${BASE_DIR:?}/${_EGG_DIR_BASE}"
        fi
    fi
}

build()
{
    python setup.py sdist bdist_wheel
}

clean_all()
{
    python setup.py clean --all 2>/dev/null
    [ -d ${BASE_DIR:?}/build ] && echo "Removing ${BASE_DIR}/build" && rm -r ${BASE_DIR}/build
    [ -d ${BASE_DIR:?}/dist ] && echo "Removing ${BASE_DIR}/dist" && rm -r ${BASE_DIR}/dist

    get_egg_info_dir
    #echo "EGG dir is ${EGG_DIR:-<not set>}"
    [ -n "${EGG_DIR:-}" ] && [ -d ${EGG_DIR:?} ] && echo "Removing ${EGG_DIR}" && rm -r "${EGG_DIR}"
}

build_and_upgrade()
{
    clean_all
    build
    pip uninstall -y ${PACKAGE_NAME:-nwmaas-communication}
    pip install --upgrade --find-links=${BASE_DIR}/dist ${PACKAGE_NAME:-nwmaas-communication}
}

# If the CLEAN_FINISH option was set to clean up at the end, check that the action being run is compatible
# E.g., it probably doesn't make sense to automatically clean up just-built artifacts when running the 'build' action
check_clean_finish_compat()
{
    if [ -n "${CLEAN_FINISH:-}" ]; then
        if [ "${ACTION}" != 'clean' ] && [ "${ACTION}" != 'upgrade' ]; then
            echo "Error: usage of '--clean-finish' option not supported with '${ACTION}' action"
            usage
            exit 1
        fi
    fi
}

run_tests()
{
    # From the base dir (where the package is at), we probably need to go up one directory level
    cd ..
    python -m unittest discover -s ${UNIT_TESTED_PACKAGE_NAME} ${SET_VERBOSE:-}
}

handle_venv_activation()
{
    # Handle setting up specified virtual environment when applicable
    if [ -n "${VENV_DIR:-}" ]; then
        # First, if not in any virtual environment, activate the specified one and note that the script has done so
        if [ -z "${VIRTUAL_ENV}" ]; then
            VENV_WAS_ACTIVATED=0
            ${VENV_DIR}/bin/activate
        # If already in the specified virtual environment, simply make note so script doesn't deactivate it when done
        elif [ "${VIRTUAL_ENV:-x}" == "${VENV_DIR}" ]; then
            VENV_WAS_ACTIVATED=1
        # However, bail in the case the shell has a virtual environment activated, but NOT the one it expects
        else
            echo "Error: given virtual env directory '${VENV_DIR}' does not match already activated venv '${VIRTUAL_ENV}'"
            exit 1
        fi
    fi
}

# Reset shell state the script may have modified - like the working directory and virtual environment - then exit
reset_and_exit()
{
    [ "$(pwd)" != "${STARTING_DIR:?}" ] && cd "${STARTING_DIR:?}"
    [ ${VENV_WAS_ACTIVATED} -eq 0 ] && deactivate
    # If a code was passed (as the first arg), use it when exiting; assume 0 if nothing provided
    exit ${1:-0}
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        --clean-finish)
            [ -n "${CLEAN_FINISH:-}" ] && usage && exit 1
            CLEAN_FINISH='true'
            ;;
        -d|--base_dir)
            [ -n "${BASE_DIR:-}" ] && usage && exit 1
            BASE_DIR="${2}"
            shift
            ;;
        --venv)
            [ -n "${VENV_DIR:-}" ] && usage && exit 1
            VENV_DIR="`cd ${2} && pwd`"
            shift
            ;;
        -v|--verbose)
            [ -n "${SET_VERBOSE:-}" ] && usage && exit 1
            SET_VERBOSE='-v'
            ;;
        build|clean|upgrade|test)
            [ -n "${ACTION:-}" ] && usage && exit 1
            ACTION="${1}"
            ;;
        *)
            usage
            exit 1
            ;;
   esac
   shift
done

[ -z "${ACTION:-}" ] && echo "Error: no action specified" && usage && exit 1
check_clean_finish_compat
[ ! -d "${BASE_DIR:=${DEFAULT_BASE_DIR}}" ] && echo "Error: base dir ${BASE_DIR} does not exist" 1>&2 && usage && exit 1

# Sanity check venv is provided correctly when needed ...
if [ "${ACTION}" == "upgrade" ] || [ "${ACTION}" == "test" ]; then
    [ -z "${VENV_DIR:-}" ] && echo "Error: no directory given for required virtual env" && usage && exit 1
    [ ! -d "${VENV_DIR:-}" ] && echo "Error: given virtual env directory path is not an existing directory" && exit 1
    [ ! -e "${VENV_DIR}/bin/activate" ] && echo "Error: given virtual env directory does not appear to be valid venv" && exit 1
# ... or venv dir was provided unexpectedly when not needed (i.e., actions other than those in the leading 'if') ...
elif [ -n "${VENV_DIR:-}" ]; then
    echo "Error: --venv option not supported for action '${ACTION}'"
    usage
    exit 1
fi

handle_venv_activation

cd "${BASE_DIR:?}"

if [ "${ACTION}" == "build" ]; then
    build
elif [ "${ACTION}" == "clean" ]; then
    clean_all
    # Supports --clean-finish, but just ignore for this case
elif [ "${ACTION}" == "test" ]; then
    run_tests
elif [ "${ACTION}" == "upgrade" ]; then
    build_and_upgrade
    [ -n "${CLEAN_FINISH}" ] && clean_all
else
    echo "Error: unknown action '${ACTION}'"
    reset_and_exit 1
fi

reset_and_exit
