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
if [ -z "${PROJECT_ROOT:-}" ]; then
    set_project_root
    PROJ_SCRIPTS_SRC_DIR="${PROJECT_ROOT:?}/scripts"
    HOOKS_SRC_DIR="${PROJ_SCRIPTS_SRC_DIR}/hooks"

    # TODO: for any other common script paths that may be needed, set them here, so if ever changed, only need updating
    # TODO:     in one place.
fi