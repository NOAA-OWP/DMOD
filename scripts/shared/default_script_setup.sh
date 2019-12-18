#!/usr/bin/env sh
# A template meant to be sourced by several other projects scripts to get some standard startup behavior

NAME="`basename ${0}`"

# Keep note of whether the script has activated a virtual python environment, and must later deactivate it
# Uses the shell-style conventions of 0 => true and 1 => false
VENV_WAS_ACTIVATED=1

# Keep track of the working directory for the parent shell at the time the script was called
STARTING_DIR=`pwd`

PACKAGE_NAMESPACE_ROOT=nwmaas