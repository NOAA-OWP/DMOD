#!/usr/bin/env bash

INFO='Run unit or integration tests for a group of supported Python packages'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

# Set SHARED_FUNCS_DIR (as needed by default_script_setup.sh) to the correct path before using it to source its contents
SHARED_FUNCS_DIR="${SCRIPT_PARENT_DIR}/shared"
if [ ! -d "${SHARED_FUNCS_DIR}" ]; then
    >&2 echo "Error: could not find shared script functions script at expected location:"
    >&2 echo "    ${SHARED_FUNCS_DIR}"
    exit 1
fi

# Import shared default script startup source
. ${SHARED_FUNCS_DIR}/default_script_setup.sh

# Import shared functions used for python-dev-related scripts
. ${SHARED_FUNCS_DIR}/py_dev_func.sh

# Import bash-only shared functions used for python-dev-related scripts
. ${SHARED_FUNCS_DIR}/py_dev_bash_func.sh

DJANGO_TEST_SCRIPT_PATH="${SCRIPT_PARENT_DIR}/test_django.py"

SUPPORTED_PACKAGES=()

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

    --quiet | -q
        Quieter output; in particular, don't display count of
        number of tests run for each package (conflicts with -v)

    --service-packages | -srv
        Include service packages in what is supported and tested,
        which are ignored by default

    --django | -d
        Include Django services in what is supported and tested,
        which are ignored by default

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

determine_supported_packages()
{
    # Check if unset, and if so, run the shared function to set it
    if [ -z ${LIB_PACKAGE_DIRS+x} ]; then
        py_dev_bash_get_package_directories
    fi

    # Determine which packages are supported by testing by whether they have a test/ subdirectory
    spi=0
    for i in ${LIB_PACKAGE_DIRS[@]}; do
        if [ $(find ${i} -type d -name test | wc -l) -gt 0 ]; then
            for j in $(find ${i} -type d -name test); do
                if [ $(find ${j} -type f -name "*.py" | wc -l) -gt 0 ]; then
                    SUPPORTED_PACKAGES[${spi}]="${i}"
                    spi=$((spi+1))
                    break
                fi
            done
        fi
    done

    if [ -n "${DO_SERVICE_PACKAGES:-}" ]; then
        for i in ${SERVICE_PACKAGE_DIRS[@]}; do
            if [ $(find ${i} -type d -name test | wc -l) -gt 0 ]; then
                for j in $(find ${i} -type d -name test); do
                    if [ $(find ${j} -type f -name "*.py" | wc -l) -gt 0 ]; then
                        SUPPORTED_PACKAGES[${spi}]="${i}"
                        spi=$((spi+1))
                        break
                    fi
                done
            fi
        done
    fi
}

list_packages()
{
    if [ ${#SUPPORTED_PACKAGES[@]} -eq 0 ]; then
        determine_supported_packages
    fi
    if [ -z "${DO_QUIET:-}" ]; then
        echo "Supported Packages:"
    fi
    for p in "${SUPPORTED_PACKAGES[@]}"; do
        echo "    ${p}"
    done
    if [ -z "${TEST_DJANGO_SERVICES:-}" ]; then
        echo "Supported Django Services:"
        ${DJANGO_TEST_SCRIPT_PATH} --list
    fi
}

print_test_result()
{
    # 1: name
    # 2: result (0 or 1)
    if [ ${2} == 0 ]; then
        echo "${1} : passed"
    else
        echo "${1} : failed"
        TOTAL_RESULT=$((TOTAL_RESULT+1))
    fi
    return ${2}
}

test_package_quietly()
{
    if [ -n "${VENV_DIR:-}" ]; then
        ${PACKAGE_TESTING_SCRIPT} --venv "${VENV_DIR}" ${IT_ARG:-} ${VERBOSE_ARG:-} ${SUPPORTED_PACKAGES[${1}]} > /dev/null 2>&1
        return $?
    else
        ${PACKAGE_TESTING_SCRIPT} ${IT_ARG:-} ${VERBOSE_ARG:-} ${SUPPORTED_PACKAGES[${1}]} > /dev/null 2>&1
        return $?
    fi
}

test_package()
{
    echo "${SUPPORTED_PACKAGES[${1}]}"
    if [ -n "${VENV_DIR:-}" ]; then
        ${PACKAGE_TESTING_SCRIPT} --venv "${VENV_DIR}" ${IT_ARG:-} ${VERBOSE_ARG:-} ${SUPPORTED_PACKAGES[${1}]}
        PACKAGE_RESULT[${1}]=$?
    else
        ${PACKAGE_TESTING_SCRIPT} ${IT_ARG:-} ${VERBOSE_ARG:-} ${SUPPORTED_PACKAGES[${1}]}
        PACKAGE_RESULT[${1}]=$?
    fi
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
            [ -n "${DO_LIST:-}" ] && usage && exit 1
            DO_LIST='true'
            ;;
        --quiet|-q)
            [ -n "${DO_QUIET:-}" ] && usage && exit 1
            [ -n "${SET_VERBOSE:-}" ] && usage && exit 1
            DO_QUIET='true'
            ;;
        --service-packages|-srv)
            [ -n "${DO_SERVICE_PACKAGES:-}" ] && usage && exit 1
            DO_SERVICE_PACKAGES='true'
            ;;
        --django|-d)
            [ -n "${TEST_DJANGO_SERVICES:-}" ] && usage && exit 1;
            TEST_DJANGO_SERVICES='true';
            ;;
        --venv)
            [ -n "${VENV_DIR:-}" ] && usage && exit 1
            VENV_DIR="$(py_dev_validate_venv_dir "${2}")"
            [ -z "${VENV_DIR:-}" ] && echo "Error: provided arg ${2} is not a valid virtual env directory" && exit 1
            shift
            ;;
        -v|-vv)
            [ -n "${SET_VERBOSE:-}" ] && usage && exit 1
            [ -n "${DO_QUIET:-}" ] && usage && exit 1
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

if [ ${#SUPPORTED_PACKAGES[@]} -eq 0 ]; then
    determine_supported_packages
fi

if [ -n "${DO_LIST:-}" ]; then
    list_packages
    exit
fi

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

TOTAL_RESULT=0

# Perform testing on the supported packages
len=${#SUPPORTED_PACKAGES[@]}
for (( i=0; i<${len}; i++)); do
    if [ -n "${DO_QUIET:-}" ]; then
        test_package_quietly ${i}
        # When testing quietly, print results immediately, since they won't get buried in the noise
        print_test_result ${SUPPORTED_PACKAGES[${i}]} $?
    elif [ -z "${SET_VERBOSE:-}" ]; then
        _TEMP_FILE="./.run_tests_temp_package_test_output_${i}"
        test_package ${i} > "${_TEMP_FILE}" 2>&1
        _P_RES=${PACKAGE_RESULT[${i}]}
        [ ${_P_RES} -eq 0 ] || TOTAL_RESULT=$((TOTAL_RESULT+1))
        _TEST_COUNTS=`cat "${_TEMP_FILE}" | grep Ran`
        _RESULTS=`cat "${_TEMP_FILE}" | tail -n 5 | grep -i 'fail\|ok'`
        echo "${SUPPORTED_PACKAGES[${i}]}: ${_RESULTS} (${_TEST_COUNTS})"
        rm "${_TEMP_FILE}"
    else
        # For verbose, test function saves results to PACKAGE_RESULT
        # This is so we can wait to print results in a summary all at the end
        echo "-----------------------------------"
        test_package ${i}
        echo ""
        echo ""
        echo ""
    fi
done


if [ -n "${TEST_DJANGO_SERVICES:-}" ]; then
    if [ -n "${DO_QUIET:-}" ]; then
        echo "Running django tests in quiet mode"
        ${DJANGO_TEST_SCRIPT_PATH} --quiet
    elif [ -z "${SET_VERBOSE:-}" ]; then
        ${DJANGO_TEST_SCRIPT_PATH}
    else
        echo "-----------------------------------"
        echo ""
        echo "Django Tests:"
        echo ""
        VERBOSE_DJANGO_OUTPUT=$("${DJANGO_TEST_SCRIPT_PATH}" --verbose)
        echo "$VERBOSE_DJANGO_OUTPUT"

        # Extract the lines containing the summary to print later
        # Knowing that there will only be 2 values is a stopgap
        DJANGO_SUMMARY=$(echo "$VERBOSE_DJANGO_OUTPUT" | tail -n 2)
        echo ""
        echo ""
        echo ""
    fi
fi


# If we got verbose output, print summary at the end, along with something extra to have stand out
if [ -n "${SET_VERBOSE:-}" ]; then
    echo "**************************************************"
    echo "* Results Summary:                               *"
    echo "**************************************************"
    for (( j=0; j<${len}; j++)); do
        _P_RES=${PACKAGE_RESULT[${j}]}
        print_test_result ${SUPPORTED_PACKAGES[${j}]} ${_P_RES}
    done

    if [ -n "${DJANGO_SUMMARY:-}" ]; then
        echo "$DJANGO_SUMMARY"
    fi
fi

echo ""

# Return based on whether there were any failures
if [ ${TOTAL_RESULT} == 0 ]; then
    exit
else
    exit 1
fi
