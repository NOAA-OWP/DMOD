#!/usr/bin/env bash
### Functions and shared behavior that only is applicable in a Bash shell

LIB_PACKAGE_ROOT='python/lib'
SERVICE_PACKAGE_ROOT='python/services'

# Generate LIB_PACKAGE_NAMES and SERVICE_PACKAGE_NAMES that are arrays of the simple (non-namespaced) names of existing
# Python library and service packages respectively
py_dev_bash_get_package_simple_names()
{
    local _START_DIR="$(pwd)"

    cd "${LIB_PACKAGE_ROOT}"
    LIB_PACKAGE_NAMES=(*)

    cd "${_START_DIR}"

    cd "${SERVICE_PACKAGE_ROOT}"
    SERVICE_PACKAGE_NAMES=(*)

    cd "${_START_DIR}"
}

# Generate the arrays of library and service package directories (and names using the function above, if necessary)
py_dev_bash_get_package_directories()
{
    # This just checks if LIB_PACKAGE_NAMES is unset, which implies py_dev_bash_get_package_simple_names has not been called
    # and, therefore, SERVICE_PACKAGE_DIRS is also unset
    if [ -z ${LIB_PACKAGE_NAMES+x} ]; then
        py_dev_bash_get_package_simple_names
    fi

    LIB_PACKAGE_DIRS=()
    for i in $(seq 0 $((${#LIB_PACKAGE_NAMES[@]}-1))); do
        LIB_PACKAGE_DIRS[${i}]="${LIB_PACKAGE_ROOT}/${LIB_PACKAGE_NAMES[${i}]}"
    done

    SERVICE_PACKAGE_DIRS=()
    for i in $(seq 0 $((${#SERVICE_PACKAGE_NAMES[@]}-1))); do
        SERVICE_PACKAGE_DIRS[${i}]="${SERVICE_PACKAGE_ROOT}/${SERVICE_PACKAGE_NAMES[${i}]}"
    done
}
