# Central location for reuseable functions to source for various package-specific build.sh helper script.
# Functions are prefixed with 'pkb_' to effectively namespace them.

# Note that several functions require implemented-script analogs to be present. E.g., several
# functions rely on there being a function named 'usage' defined, though there is none herein.
# This can be addressed with something as simple as the following definition in another script
# sourcing functions from this file:
#
# usage()
# {
#     pkb_default_usage
# }
#
# Additionally, several variables are assumed to have already been defined by an external script
# sourcing and using certain functions in this file.  Some (but not necessarily all) examples of
# these are:
#
# - NAME
# - DEFAULT_BASE_DIR
# - BASE_DIR *
# - PACKAGE_NAME
# - ACTION *
# - STARTING_DIR
#
# * For some variables, it is possible for one function here to require the variable has been set,
#   while some second function here actually sets (or could set) the variable, but such is not
#   guaranteed to happen before the first function is called.  A relatively simple example is ACTION,
#   which may be, but is not necessarily, set by a call to pkb_default_arg_parse(), and nothing here
#   ensures pkb_default_arg_parse() is called before, e.g., pkb_default_sanity_checks() (which
#   requires ACTION be set).


# Standard usage function for helpful output for default behavior/arguments
pkb_default_usage()
{
    local _O="Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} [options] <action>

Options:
    -d|--base_dir <dir_path>
        Set the base directory from which to run specified action(s)
        Default: ${DEFAULT_BASE_DIR:?}

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

# Corresponding default argument parsing function, paired with the above-defined pkb_default_usage
pkb_default_arg_parse()
{
    while [ ${#} -gt 0 ]; do
        case "${1}" in
            -h|--help|-help)
                pkb_default_usage
                exit
                ;;
            --clean-finish)
                [ -n "${CLEAN_FINISH:-}" ] && pkb_default_usage && exit 1
                CLEAN_FINISH='true'
                ;;
            -d|--base_dir)
                [ -n "${BASE_DIR:-}" ] && pkb_default_usage && exit 1
                BASE_DIR="${2}"
                shift
                ;;
            --venv)
                [ -n "${VENV_DIR:-}" ] && pkb_default_usage && exit 1
                # Handle absolute versus relative paths properly
                if expr "${2}" : '[/]' > /dev/null; then
                    VENV_DIR="${2}"
                else
                    VENV_DIR="$(pwd)/${2}"
                fi
                shift
                ;;
            -v|--verbose)
                [ -n "${SET_VERBOSE:-}" ] && pkb_default_usage && exit 1
                SET_VERBOSE='-v'
                ;;
            build|clean|upgrade|test)
                [ -n "${ACTION:-}" ] && pkb_default_usage && exit 1
                ACTION="${1}"
                ;;
            *)
                pkb_default_usage
                exit 1
                ;;
       esac
       shift
    done
}

# Set the EGG_DIR variable, if it has not been set, based in part on the value of BASE_DIR
pkb_get_egg_info_dir()
{
    if [ -z "${EGG_DIR:-}" ]; then
        _EGG_DIR_BASE=`ls "${BASE_DIR:?}" | grep -e '.*\.egg-info$'`
        if [ -n "${_EGG_DIR_BASE:-}" ]; then
            EGG_DIR="${BASE_DIR:?}/${_EGG_DIR_BASE}"
        fi
    fi
}

# Build python dist files for package
pkb_build()
{
    python setup.py sdist bdist_wheel
}

# Clean up artifacts from a previous python dist build execution
pkb_clean_all()
{
    python setup.py clean --all 2>/dev/null
    [ -d ${BASE_DIR:?}/build ] && echo "Removing ${BASE_DIR}/build" && rm -r ${BASE_DIR}/build
    [ -d ${BASE_DIR:?}/dist ] && echo "Removing ${BASE_DIR}/dist" && rm -r ${BASE_DIR}/dist

    pkb_get_egg_info_dir
    #echo "EGG dir is ${EGG_DIR:-<not set>}"
    [ -n "${EGG_DIR:-}" ] && [ -d ${EGG_DIR} ] && echo "Removing ${EGG_DIR}" && rm -r "${EGG_DIR}"
}

# Clean and build with above functions for such, then install the build dist files for the package with Pip
pkb_build_and_upgrade()
{
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        echo "Error: building and upgrading pip packages requires specifying and activating a virtual environment"
        usage
        exit 1
    fi
    pkb_clean_all
    pkb_build
    # This is just to make sure the variable is set, or bail
    ls ${BASE_DIR:?} > /dev/null
    pip uninstall -y ${PACKAGE_NAME:?}
    pip install --upgrade --find-links=${BASE_DIR:?}/dist ${PACKAGE_NAME?}
}

# If the CLEAN_FINISH option was set to clean up at the end, check that the action being run is compatible
# E.g., it probably doesn't make sense to automatically clean up just-built artifacts when running the 'build' action
pkb_check_clean_finish_compat()
{
    if [ -n "${CLEAN_FINISH:-}" ]; then
        if [ "${ACTION:?}" != 'clean' ] && [ "${ACTION:?}" != 'upgrade' ]; then
            echo "Error: usage of '--clean-finish' option not supported with '${ACTION:?}' action"
            usage
            exit 1
        fi
    fi
}

# If appropriate, activate the provided virtual environment, and note this is done; or, error-exit if an attempt failed
pkb_handle_venv_activation()
{
    # Handle setting up specified virtual environment when applicable
    if [ -n "${VENV_DIR:-}" ]; then
        # First, if not in any virtual environment, activate the specified one and note that the script has done so
        if [ -z "${VIRTUAL_ENV:-}" ]; then
            VENV_WAS_ACTIVATED=0
            . ${VENV_DIR}/bin/activate
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

# Run (unit) tests, changing temporarily into the directory above the set BASE_DIR to run them
pkb_run_tests()
{
    local _FUNC_START_DIR="$(pwd)"
    # From the base dir (where the package is at), we probably need to go up one directory level
    cd "${BASE_DIR:?}/.."
    python -m unittest discover -s ${UNIT_TESTED_PACKAGE_NAME} ${SET_VERBOSE:-}
    cd "${_FUNC_START_DIR}"
}

# Default commands to reset shell state script may have modified - like working directory and virtual environment - then exit
# Pass argument "-r" to avoid exiting directly from function call
pkb_reset_and_exit()
{
    [ "$(pwd)" != "${STARTING_DIR:?}" ] && cd "${STARTING_DIR:?}"
    [ ${VENV_WAS_ACTIVATED:-1} -eq 0 ] && deactivate
    # If a code was passed (as the first arg), use it when exiting; assume 0 if nothing provided
    if [ ${#} -lt 1 ] || [ "${1:-}" != "-r" ]; then
        exit ${1:-0}
    fi
}

pkb_default_sanity_checks()
{
    # use implemented-script-specific versions of usage and check_clean_finish_compat
    [ -z "${ACTION:-}" ] && echo "Error: no action specified" && usage && exit 1

    check_clean_finish_compat

    [ ! -d "${BASE_DIR:=${DEFAULT_BASE_DIR:?}}" ] && echo "Error: base dir ${BASE_DIR} does not exist" 1>&2 && usage && exit 1

    # Sanity check venv is provided correctly when needed ...
    if [ "${ACTION}" == "upgrade" ] || [ "${ACTION}" == "test" ] || [ "${ACTION}" == "build" ]; then
        [ -z "${VENV_DIR:-}" ] && echo "Error: no directory given for required virtual env" && usage && exit 1
        [ ! -d "${VENV_DIR:-}" ] && echo "Error: given virtual env directory path is not an existing directory" && exit 1
        [ ! -e "${VENV_DIR}/bin/activate" ] && echo "Error: given virtual env directory does not appear to be valid venv" && exit 1
    # ... or venv dir was provided unexpectedly when not needed (i.e., actions other than those in the leading 'if') ...
    elif [ -n "${VENV_DIR:-}" ]; then
        echo "Error: --venv option not supported for action '${ACTION}'"
        usage
        exit 1
    fi
}