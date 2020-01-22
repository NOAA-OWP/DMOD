#!/usr/bin/env bash

INFO='Run unit or integration tests for a group of supported Python packages'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

# Import shared default script startup source
. ${SCRIPT_PARENT_DIR}/shared/default_script_setup.sh

# Import shared functions used for python-dev-related scripts
. ${SCRIPT_PARENT_DIR}/shared/py_dev_func.sh

# Paths relative to project root
SUPPORTED_PACKAGES=(lib/access lib/communication lib/externalrequests lib/scheduler)
PACKAGE_TESTING_SCRIPT=${SCRIPT_PARENT_DIR}/test_package.sh

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} [opts]

Options:

    --integration | -it
        Execute integration tests on supported packages via
        passed '-it' option

    --list-packages | -l
        List the supported packages that are tested

    --venv <dir>
        Set the directory of the virtual environment to use.
        By default, the following directories will be checked,
        with the first apparently valid virtual env being used:
        - ./venv/
        - ./.venv/
        - ${SCRIPT_PARENT_DIR:-?}/venv/
        - ${SCRIPT_PARENT_DIR:-?}/.venv/

    -v
        Set verbose output

    -vv
        Set very verbose output (include not just output, but
        verbose output from package testing script)
"
    echo "${_O}" 2>&1
}

list_packages()
{
    echo "Supported Packages:"
    for p in "${SUPPORTED_PACKAGES[@]}"; do
        echo "    ${p}"
    done
}

print_test_result()
{
    # 1: name
    # 2: result (0 or 1)
    if [ ${2} == 0 ]; then
        echo "Results for package ${1} : passed"
    else
        echo "Results for package ${1} : failed"
        TOTAL_RESULT=$((TOTAL_RESULT+1))
    fi
    return ${2}
}

test_package_quietly()
{
    ${PACKAGE_TESTING_SCRIPT} ${IT_ARG:-} ${VERBOSE_ARG:-} ${SUPPORTED_PACKAGES[${1}]} > /dev/null 2>&1
    return $?
}

test_package()
{
    echo "-----------------------------------"
    echo "${SUPPORTED_PACKAGES[${1}]}"
    ${PACKAGE_TESTING_SCRIPT} ${IT_ARG:-} ${VERBOSE_ARG:-} ${SUPPORTED_PACKAGES[${1}]}
    PACKAGE_RESULT[${1}]=$?
    echo ""
    echo ""
    echo ""
    return ${PACKAGE_RESULT[${1}]}
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        --integration|-it)
            [ -n "${IT_ARG:-}" ] && usage && exit 1
            IT_ARG="-it"
            ;;
        --list-packages|-l)
            list_packages
            exit
            ;;
        --venv)
            [ -n "${VENV_DIR:-}" ] && usage && exit 1
            VENV_DIR="$(py_dev_validate_venv_dir "${2}")"
            [ -z "${VENV_DIR:-}" ] && echo "Error: provided arg ${2} is not a valid virtual env directory" && exit 1
            shift
            ;;
        -v|-vv)
            [ -n "${SET_VERBOSE:-}" ] && usage && exit 1
            SET_VERBOSE='true'
            if [ "${1}" == "-vv" ]; then
                VERBOSE_ARG="-v"
            fi
            ;;

        *)
            usage
            exit 1
            ;;
    esac
    shift
done

# Sanity check all support package can be found at paths
MISSING_COUNT=0
for p in "${SUPPORTED_PACKAGES[@]}"; do
    if [ ! -d ${p} ]; then
        MISSING_COUNT=$((MISSING_COUNT+1))
        [ ${MISSING_COUNT} = 1 ] && >&2 echo "Error: missing expected package directories"
        >&2 echo "  - ${p}"
    fi
done
if [ ${MISSING_COUNT} -gt 0 ]; then
    exit 1
fi

# Output a line so its clear script is working when not verbose
if [ -z "${SET_VERBOSE:-}" ]; then
    if [ -n "${IT_ARG:-}" ]; then
        echo "Executing integration tests on supported packages ..."
    else
        echo "Executing unit tests on supported packages ..."
    fi
    echo ""
fi

# Perform testing on the supported packages
len=${#SUPPORTED_PACKAGES[@]}
for (( i=0; i<${len}; i++)); do
    if [ -z "${SET_VERBOSE:-}" ]; then
        test_package_quietly ${i}
        # When testing quietly, print results immediately, since they won't get buried in the noise
        print_test_result ${SUPPORTED_PACKAGES[${i}]} $?
    else
        # For verbose, test function saves results to PACKAGE_RESULT
        # This is so we can wait to print results in a summary all at the end
        test_package ${i}
    fi
done

TOTAL_RESULT=0

# If we got verbose output, print summary at the end, along with something extra to have stand out
if [ -n "${SET_VERBOSE:-}" ]; then
    echo "**************************************************"
    echo "* Results Summary:                               *"
    echo "**************************************************"
    for (( j=0; j<${len}; j++)); do
        _P_RES=${PACKAGE_RESULT[${j}]}
        print_test_result ${SUPPORTED_PACKAGES[${j}]} ${_P_RES}
    done
fi

echo ""

# Return based on whether there were any failures
if [ ${TOTAL_RESULT} == 0 ]; then
    exit
else
    exit 1
fi
