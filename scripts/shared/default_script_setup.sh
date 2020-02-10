#!/usr/bin/env sh
# A template meant to be sourced by several other projects scripts to get some standard startup behavior
#
# Note that variable settings should protected from double-sourcing this file, though they may get that for free

NAME="`basename ${0}`"

if [ -z "${SCRIPT_PARENT_DIR:-}" ]; then
    SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"
fi

# This will not be true if this file was already sourced, so _SHARED_FUNCS_ABSOLUTE_DIR can only be set (here) once
if [ -z "${_SHARED_FUNCS_ABSOLUTE_DIR:-}" ]; then
    # In order for certain things to make sense, this file really need this set before being sourced ...
    if [ -z "${SHARED_FUNCS_DIR:-}" ] || [ ! -d "${SHARED_FUNCS_DIR:-}" ]; then
        >&2 echo "Error: SHARED_FUNCS_DIR not set properly before sourcing shared functions"
        >&2 echo ""
        >&2 echo "Set this to the directory where this script is located before sourcing it."
        >&2 echo "See logic at the beginning of the test_package.sh as an example."
        exit 1
    fi
    # Then set the analogous variable that will always be an absolute path
    _SHARED_FUNCS_ABSOLUTE_DIR="$(cd "${SHARED_FUNCS_DIR}"; pwd)"
fi
# The value of _SHARED_FUNCS_ABSOLUTE_DIR should only ever be set once and always be valid (since it is absolute)
# Go ahead and re-set SHARED_FUNCS_DIR to the absolute path also (protects from any problems from double-sourcing)
SHARED_FUNCS_DIR="${_SHARED_FUNCS_ABSOLUTE_DIR:?}"

# Keep track of the working directory for the parent shell at the time the script was called
# Make sure if we double-source this that the value below doesn't get reset
if [ -z "${STARTING_DIR:-}" ]; then
    STARTING_DIR="`pwd`"
fi

# Helper script, useful when local variables aren't a thing, that receives a value (implied to be the return code of
# previous function or nested command), simply returning if the code is 0, but exiting the entire script with the value
# as the exit code if the value is non-zero.
exit_with_if_non_zero()
{
    if [ ${#} -ne 1 ]; then
        >&2 echo "Warning: called exit_with_if_non_zero() with wrong number of arguments; ignoring and proceeding"
    fi
    # Do this to test the value is an integer (-eq will be false for the same arg except for ints)
    if [ "${1}" -eq "${1}" ] 2>/dev/null; then
        if [ ${1} -ne 0 ]; then
            exit ${1}
        fi
    else
        >&2 echo "Warning: called exit_with_if_non_zero() with wrong type of argument; ignoring and proceeding"
    fi
}

set_project_root()
{
    if git rev-parse --show-toplevel > /dev/null 2>&1; then
        PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
    else
        cd "${SHARED_FUNCS_DIR}"
        PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
        cd "${STARTING_DIR}"
    fi
}

# Make sure if we double-source this that the values below don't get reset
# Also, make this compatible for running outside the actual repo (e.g., inside a Docker container)
if [ -z "${PROJECT_ROOT:-}" ] && [ -z "${OUT_OF_GIT_REPO:-}" ]; then
    set_project_root
    PROJ_SCRIPTS_SRC_DIR="${PROJECT_ROOT:?}/scripts"

    # TODO: for any other common script paths that may be needed, set them here, so if ever changed, only need updating
    # TODO:     in one place.
fi
