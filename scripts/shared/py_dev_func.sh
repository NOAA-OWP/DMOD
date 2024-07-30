#!/usr/bin/env sh

# Keep note of whether the script has activated a virtual python environment, and must later deactivate it
# Uses the shell-style conventions of 0 => true and 1 => false
VENV_WAS_ACTIVATED=1

PACKAGE_NAMESPACE_ROOT=dmod

# Validate that an arg is a path to a valid venv directory, echoing the path to stdout if it is, and also returning 0 or
# 1 consistent with standard shell T/F.
# Also, print out messages to stderr when not valid, unless suppressed with '-q' arg.
py_dev_validate_venv_dir()
{
    # Allow for one extra arg '-q' to indicate option for quiet error output
    if [ ${#} -gt 0 ] && [ "${1}" = '-q' ]; then
        _VENV_VALIDATE_DIR_PRINT_MESSAGE='true'
        shift
    # Also nested call if -q arg is second
    elif [ ${#} -gt 0 ] && [ "${2}" = '-q' ]; then
        py_dev_validate_venv_dir -q "${1}" ${@:3}
        return $?
    fi

    if [ ${#} -lt 1 ]; then
        [ -z "${_VENV_VALIDATE_DIR_PRINT_MESSAGE:-}" ] && >&2 echo "Error: invalid attempt to verify virtual env directory"
        return 1
    elif [ ${#} -gt 1 ]; then
        [ -z "${_VENV_VALIDATE_DIR_PRINT_MESSAGE:-}" ] && >&2 echo "Warning: unexpected arguments passed to function verifying virtual env directory"
    fi

    if [ ! -d "${1}" ]; then
        [ -z "${_VENV_VALIDATE_DIR_PRINT_MESSAGE:-}" ] && >&2 echo "Error: proposed venv directory '${1}' does not exist"
        return 1
    elif [ ! -e "${1}/bin/activate" ]; then
        [ -z "${_VENV_VALIDATE_DIR_PRINT_MESSAGE:-}" ] && >&2 echo "Error: proposed venv directory '${1}' does not have a 'bin/activate' file"
        return 1
    else
        echo "${1}"
        return $?
    fi
}

# Detect a valid default virtual env (if one is not already set in the VENV_DIR variable) from a preset group
py_dev_detect_default_venv_directory()
{
    # Bail right away if VENV_DIR was already set
    if [ -z "${VENV_DIR:-}" ]; then
        for d in "${STARTING_DIR:?}/venv" "${STARTING_DIR:?}/.venv" "${SCRIPT_PARENT_DIR:?}/venv" "${SCRIPT_PARENT_DIR:?}/.venv"; do
            if py_dev_validate_venv_dir "${d}" > /dev/null; then
                VENV_DIR="${d}"
                echo "Detected default virtual env directory: ${VENV_DIR}"
                break
            fi
        done
    fi
}

#
py_dev_get_egg_info_dir()
{
    _EGG_DIR_BASE=`ls | grep -e '.*\.egg-info$'`

    if [ -z "${EGG_DIR:-}" ]; then
        if [ -n "${_EGG_DIR_BASE:-}" ]; then
            EGG_DIR="${BASE_DIR:?}/${_EGG_DIR_BASE}"
        fi
    fi
}

# Clean up artifacts from a previous python dist build execution in the current directory
py_dev_clean_dist()
{
    _PY_DEV_CLEAN_DIST_EGG_DIR="$(ls | grep -e '.*\.egg-info$')"
    python setup.py clean --all 2>/dev/null
    [ -d ./build ] && echo "Removing $(pwd)/build" && rm -r ./build
    [ -d ./dist ] && echo "Removing $(pwd)/dist" && rm -r ./dist

    if [ -n "${_PY_DEV_CLEAN_DIST_EGG_DIR}" ] && [ -d "${_PY_DEV_CLEAN_DIST_EGG_DIR}" ]; then
        echo "Removing ${_PY_DEV_CLEAN_DIST_EGG_DIR}"
        rm -r "${_PY_DEV_CLEAN_DIST_EGG_DIR}"
    fi
}

# Determine the distribution name of the Python package based in the current working directory from its setup.py
py_dev_extract_package_dist_name_from_setup()
{
    if [ ! -e setup.py ]; then
        >&2 echo "Error: expected $(pwd)/setup.py not found; cannot determine package dist name"
        return 1
    fi

    cat setup.py \
        | grep -v import \
        | grep -e '^\(.*,\)\?[ ]*name[ ]*=[ ]*\(.\)\([^,]*\)[^, ][ ]*,' \
        | sed -E 's/^(.*,)*[ ]*name[ ]*=[ ]*.([^,]*)[^,],.*/\2/g'
}

# If appropriate, activate the virtual env set within VENV_DIR, and note whether this is done in VENV_WAS_ACTIVATED.
#
# Function returns with an error if venv activation was appropriate but could not be done due to an error or ambiguity
# (e.g., an already-active venv where VIRTUAL_ENV != VENV_DIR)
#
# It is not an error in the context of this function for no VENV_DIR value to be set (basically, this just returns).
py_dev_activate_venv()
{
    # Handle setting up specified virtual environment when applicable
    if [ -n "${VENV_DIR:-}" ]; then
        # First, if not in any virtual environment, activate the specified one and note that the script has done so
        if [ -z "${VIRTUAL_ENV:-}" ]; then
            >&2 echo "Activating virtual environment from ${VENV_DIR}"
            VENV_WAS_ACTIVATED=0
            . ${VENV_DIR}/bin/activate
        # If already in the specified virtual environment, simply make note so script doesn't deactivate it when done
        elif [ "${VIRTUAL_ENV:-x}" = "${VENV_DIR}" ]; then
            >&2 echo "Virtual environment from ${VENV_DIR} is already active in the current shell"
            VENV_WAS_ACTIVATED=1
        # However, bail in the case the shell has a virtual environment activated, but NOT the one it expects
        else
            >&2 echo "Error: given virtual env directory '${VENV_DIR}' does not match already activated venv '${VIRTUAL_ENV}'"
            return 1
        fi
    else
        VENV_WAS_ACTIVATED=1
    fi
}

# If appropriate, deactivate the virtual env set within VENV_DIR, and note whether this is done in VENV_WAS_ACTIVATED.
py_dev_deactivate_venv()
{
    # If the flag is set that a virtual environment was activated, then deactivate it
    if [ ${VENV_WAS_ACTIVATED:-1} -eq 0 ]; then
        >&2 echo "Deactiving active virtual env at ${VIRTUAL_ENV}"
        >&2 echo ""
        deactivate
        VENV_WAS_ACTIVATED=1
    fi
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

    py_dev_deactivate_venv
}
