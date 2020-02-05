#!/usr/bin/env sh
# A template meant to be sourced by several other projects scripts to get some standard startup behavior

NAME="`basename ${0}`"

if [ -z "${SCRIPT_PARENT_DIR:-}" ]; then
    SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"
fi

# In order for certain things to make sense, this file really need this set before being sourced ...
if [ -z "${SHARED_FUNCS_DIR:-}" ] || [ ! -d "${SHARED_FUNCS_DIR:-}" ]; then
    >&2 echo "Error: SHARED_FUNCS_DIR not set properly before sourcing shared functions"
    >&2 echo ""
    >&2 echo "Set this to the directory where this script is located before sourcing it."
    >&2 echo "See logic at the beginning of the test_package.sh as an example."
    exit 1
fi
# To make sure the value is an absolute path, reset this like so ...
SHARED_FUNCS_DIR="$(cd "${SHARED_FUNCS_DIR}"; pwd)"

# Keep note of whether the script has activated a virtual python environment, and must later deactivate it
# Uses the shell-style conventions of 0 => true and 1 => false
VENV_WAS_ACTIVATED=1

# Keep track of the working directory for the parent shell at the time the script was called
STARTING_DIR=`pwd`

PACKAGE_NAMESPACE_ROOT=nwmaas

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

set_project_root