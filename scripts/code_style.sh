#!/usr/bin/env bash

INFO='Execute Python code style helper tasks on specified packages or modules'
SCRIPT_PARENT_DIR="$( cd "$( dirname "${0}" )" >/dev/null 2>&1 && pwd )"

# Import shared default script startup source
. ${SCRIPT_PARENT_DIR}/shared/default_script_setup.sh

# Import shared functions used for python-dev-related scripts
. ${SCRIPT_PARENT_DIR}/shared/py_dev_func.sh

LINTER_CMD='flake8'
AUTOPEP_CMD='autopep8'
DEFAULT_MAX_LINE_LENGTH=120

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|--help
    ${NAME:?} [options...] <action>

Options:
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

    --path <path>
        Path to file or directory of interest for action

    --diff
        For 'fix' action, show a diff rather than actually making
        changes

    --extra-aggressive | -aa
        For 'fix' action, be extra aggressive in changes

    --max-line-length <number>
        Set the max line length (default for this script is ${DEFAULT_MAX_LINE_LENGTH})
Actions:
    fix     Make automatic style corrections
    check   Execute the linter (currently ${LINTER_CMD})
"

    echo "${_O}" 2>&1
}

run_linter()
{
    ${LINTER_CMD} \
        --max-line-length=${MAX_LINE_LENGTH:-${DEFAULT_MAX_LINE_LENGTH}} \
        --count \
        "${CHECK_PATH:-}"
}

run_autofix()
{
    ${AUTOPEP_CMD} \
        -r \
        ${FIX_CHANGE_METHOD:---in-place}  \
        ${AGGRESSIVENESS--a} \
        --max-line-length ${MAX_LINE_LENGTH:-${DEFAULT_MAX_LINE_LENGTH}} \
        "${LIST_FIXES:-}" \
        "${CHECK_PATH:-.}"
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

# Options args loop
while [[ ${#} -gt 0 ]]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        --direct)
            shift
            break
            ;;
        --path)
            [[ -n "${CHECK_PATH:-}" ]] && usage && exit 1
            CHECK_PATH="${2}"
            [[ ! -e "${CHECK_PATH}" ]] && echo "Error: check path ${CHECK_PATH} does not exist" && usage && exit 1
            shift
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
        --max-line-length)
            [[ -n "${MAX_LINE_LENGTH:-}" ]] && usage && exit 1
            MAX_LINE_LENGTH="${2}"
            re='^[0-9]+$'
            if ! [[ $MAX_LINE_LENGTH =~ $re ]]; then
                usage
                exit 1
            fi
            shift
            ;;
        --diff)
            [[ -n "${FIX_CHANGE_METHOD:-}" ]] && usage && exit 1
            FIX_CHANGE_METHOD="--diff"
            ;;
        --extra-aggressive|-aa)
            # This echos if val is set non-null or val not declared
            if  [[ -n "${AGGRESSIVENESS-blah}" ]]; then
                [[ -n "${AGGRESSIVENESS:-}" ]] && usage && exit 1
            fi
            AGGRESSIVENESS="-aa"
            ;;
        *)
            # Break out of options loop to proceed to actions loop
            break
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

# Action args loop
while [[ ${#} -gt 0 ]]; do
    case "${1}" in
        fix|autopep8)
            ! command -v  ${AUTOPEP_CMD} > /dev/null && echo "Error: cannot find command ${AUTOPEP_CMD} in environment path" && exit 1
            if [[ "${SCRIPT_OPTS_FINISHED:-}" == 'true' ]]; then
                shift
                ${AUTOPEP_CMD} "${@}"
                exit $?
            else
                [[ -n "${ACTION:-}" ]] && usage && exit 1
                ACTION="run_autofix"
            fi
            ;;
        check|linter|flake8)
            ! command -v ${LINTER_CMD} > /dev/null && echo "Error: cannot find command ${LINTER_CMD} in environment path" && exit 1
            if [[ "${SCRIPT_OPTS_FINISHED:-}" == 'true' ]]; then
                shift
                ${LINTER_CMD} "${@}"
                exit $?
            else
                [[ -n "${ACTION:-}" ]] && usage && exit 1
                ACTION="run_linter"
            fi
            ;;
        *)
            usage
            exit 1
    esac
    shift
done

[[ -z "${ACTION:-}" ]] && usage && exit

${ACTION}

# Deactivate virtual environment if one was loaded
[[ -n "${USE_VENV:-}" ]] && deactivate
