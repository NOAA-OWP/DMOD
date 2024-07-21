#!/usr/bin/env bash

INFO='Rebuild and update the local-source Python package at given path in the implied or specified Python virtual env.

Defaults to all local packages in the event no single directory is provided.'
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

# Statically set this for now
_REQ_FILE="${PROJECT_ROOT:?}/requirements.txt"

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} [opts] [<directory>]

Options:
    --dependencies | -d
        Install Python dependency packages defined in the
        requirements.txt file in the project root

    --dependencies-only | -D
        Like the --dependencies option, except only do this
        step, without performing any other package building or
        updating

    --libraries-only | --no-service-packages | -l
        Include only library packages when default installing
        all local-source packages (ignored if single package
        directory is specified)

    --print-directories | -pd
        Do not install, but rather just print the directories
        of the local packages that will be installed (cannot be
        run with --dependencies, --dependencies-only, or
        --print-packages).

    --print-packages | -pp
        Print just the names of the packages to be installed,
        without actually installing (cannot be run with
        --print-directories).

    --venv <dir>
        Set the directory of the virtual environment to use.
        By default, the following directories will be checked,
        with the first apparently valid virtual env being used:
        - ./venv/
        - ./.venv/
        - ${SCRIPT_PARENT_DIR:-?}/venv/
        - ${SCRIPT_PARENT_DIR:-?}/.venv/
"
    echo "${_O}" 2>&1
}

check_and_install_wheel() {
    if ! pip show wheel > /dev/null 2>&1; then
        echo "wheel package is not installed. Installing..."
        pip install wheel
    fi
}

init_package_dirs_array_when_empty()
{
    # Only initialize if nothing was provided (i.e., via command line args)
    if [ -z ${PACKAGE_DIRS+x} ]; then

        # First, get all them, in the separate arrays for lib and service packages.
        py_dev_bash_get_package_directories

        spi=0
        for i in ${LIB_PACKAGE_DIRS[@]}; do
            # Include package directory, as long as there is a setup.py for the package
            if [ -e "${i}/setup.py" ]; then
                PACKAGE_DIRS[${spi}]="${i}"
                spi=$((spi+1))
            fi
        done

        # Though check for option indicating only library packages should be installed.
        if [ -z "${NO_SERVICE_PACKAGES:-}" ]; then
            for i in ${SERVICE_PACKAGE_DIRS[@]}; do
                # Include package directory, as long as there is a setup.py for the package
                if [ -e "${i}/setup.py" ]; then
                    PACKAGE_DIRS[${spi}]="${i}"
                    spi=$((spi+1))
                fi
            done
        fi
    fi
    [ ${#PACKAGE_DIRS[@]} -le 0 ] && >&2 echo "Error: Invalid package empty directory list." && exit 1
}

print_package_names()
{
    init_package_dirs_array_when_empty
    for pd in ${PACKAGE_DIRS[@]}; do
        cd "${pd}"
        py_dev_extract_package_dist_name_from_setup
        cd "${STARTING_DIR:?}"
    done
    if [ -n "${DO_DEPS:-}" ]; then
        cat "${_REQ_FILE:?}"
    fi
}

print_package_directories()
{
    init_package_dirs_array_when_empty
    for pd in ${PACKAGE_DIRS[@]}; do
        echo "${pd}"
    done
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
        --dependencies|-d)
            [ -n "${DO_DEPS:-}" ] && usage && exit 1
            DO_DEPS='true'
            ;;
        --dependencies-only|-D)
            [ -n "${DO_DEPS:-}" ] && usage && exit 1
            # Also, this shouldn't be set, as it assumes we will be building, which conflicts with this option
            [ -n "${NO_SERVICE_PACKAGES:-}" ] && usage && exit 1
            DO_DEPS='true'
            DEPS_ONLY='true'
            ;;
        -h|--help|-help)
            usage
            exit
            ;;
        --libraries-only|--no-service-packages|-l)
            [ -n "${NO_SERVICE_PACKAGES:-}" ] && usage && exit 1
            # Also, make sure we aren't marked for dependencies only
            [ -n "${DEPS_ONLY:-}" ] && usage && exit 1
            NO_SERVICE_PACKAGES='true'
            ;;
        --print-directories|-pd)
            [ -n "${DO_PRINT_DIRS:-}" ] && usage && exit 1
            [ -n "${DO_PRINT_PACKAGES:-}" ] && usage && exit 1
            [ -n "${DO_DEPS:-}" ] && usage && exit 1
            DO_PRINT_DIRS='true'
            ;;
        --print-packages|-pp)
            [ -n "${DO_PRINT_PACKAGES:-}" ] && usage && exit 1
            [ -n "${DO_PRINT_DIRS:-}" ] && usage && exit 1
            DO_PRINT_PACKAGES='true'
            ;;
        --venv)
            [ -n "${VENV_DIR:-}" ] && usage && exit 1
            VENV_DIR="$(py_dev_validate_venv_dir "${2}")"
            [ -z "${VENV_DIR:-}" ] && echo "Error: provided arg ${2} is not a valid virtual env directory" && exit 1
            shift
            ;;
        *)
            # Checks that PACKAGE_DIRS is, in fact, set (if it is, it'll get replaced with x)
            [ ${#PACKAGE_DIRS[@]} -gt 0 ] && usage && exit 1
            [ ! -d "${1}" ] && >&2 echo "Error: directory arg '${1}' is not an existing directory" && usage && exit 1
            PACKAGE_DIRS[0]="${1}"
            ;;
    esac
    shift
done

# If a virtual environment isn't already activated, make sure a the variable for a venv directory gets set
if [ -z "${VIRTUAL_ENV:-}" ]; then
    # This function will try to detect a valid venv directory from defaults, unless one has already been set
    py_dev_detect_default_venv_directory
    # Bail if, at this point, a valid venv directory was neither provided nor detected
    [ -z "${VENV_DIR:-}" ] && echo "Error: no valid virtual env directory could be determined or was given" && exit 1
fi

# Sanity check the requirements file exists and can be read if it is needed
if [ -n "${DO_DEPS:-}" ]; then
    if [ ! -f "${_REQ_FILE:?}" ]; then
        >&2 echo "Error: unable to find valid Python requirements file at ${_REQ_FILE}"
        exit 1
    elif [ ! -r "${_REQ_FILE:?}" ]; then
        >&2 echo "Error: Python requirements file '${_REQ_FILE}' is not readable"
        exit 1
    fi
fi

# If args given to just print, then do just those things
if [ -n "${DO_PRINT_PACKAGES:-}" ]; then
    print_package_names
    exit ${?}
elif [ -n "${DO_PRINT_DIRS:-}" ]; then
    print_package_directories
    #exit 0
    exit ${?}
fi

# Take appropriate action to activate a virtual environment if needed
py_dev_activate_venv

# Trap to make sure we "clean up" script activity before exiting
trap cleanup_before_exit 0 1 2 3 6 15

# Ensure wheel is installed
check_and_install_wheel

# After setting VENV, if set to get dependencies, do that, optionally exiting after if that's all we are set to do
if [ -n "${DO_DEPS:-}" ]; then
    pip install --upgrade -r "${_REQ_FILE}"

    # Also, if set to only get dependencies, exit here
    [ -n "${DEPS_ONLY:-}" ] && exit
fi

# If unset, meaning no single package directory was specified, assume all packages should be installed.
init_package_dirs_array_when_empty

PACKAGE_DIST_NAMES=()
# The --find-links=.../dist/ arguments needed for the dist/ directories when doing the local pip instal
PACKAGE_DIST_DIR_LINK_ARGS=()

build_package_and_collect_dist_details()
{
    if [ ${#} -lt 1 ]; then
        >&2 echo "Error: unable to build package without package directory argument"
        exit 1
    elif [ ${#} -lt 2 ]; then
        >&2 echo "Error: unable to build package without starting directory argument"
        exit 1
    fi
    # Go into the package directory, build new dists, and install them
    cd "${1}"

    # Collect dist names and dist link args as we go.
    # Of course, this means we need to figure out the index of the next array values.
    # Fortunately, this should just be the current size of the arrays
    local _N=${#PACKAGE_DIST_NAMES[@]}

    PACKAGE_DIST_NAMES[${_N}]="$(py_dev_extract_package_dist_name_from_setup)"

    # Bail if we can't detect the appropriate package dist name
    if [ -z "${PACKAGE_DIST_NAMES[${_N}]}" ]; then
        >&2 echo "Error: unable to determine package dist name from ${1}/setup.py"
        exit 1
    fi

    # Then add the generated dist directory pip arg value to that array
    PACKAGE_DIST_DIR_LINK_ARGS[${_N}]="--find-links=${1}/dist"

    # Clean any previous artifacts and build
    py_dev_clean_dist && python setup.py sdist bdist_wheel

    # Return to starting directory if one was given
    cd "${2}"
}

cd "${STARTING_DIR:?}"

# Build the packages, and build lists/arrays of dist names and '--find-links=' pip arg values as we go
for pd in ${PACKAGE_DIRS[@]}; do
    build_package_and_collect_dist_details "${pd}" "${STARTING_DIR:?}"
done

# Uninstall all existing package dists
pip uninstall -y ${PACKAGE_DIST_NAMES[@]}

# Install new dists, using the generated '--find-links=' args so we can find the local copies of build package dists
pip install --upgrade ${PACKAGE_DIST_DIR_LINK_ARGS[@]} ${PACKAGE_DIST_NAMES[@]}

# Finally, clean up all the created build artifacts in the package directories
for pd in ${PACKAGE_DIRS[@]}; do
    cd "${pd}"
    py_dev_clean_dist
    cd "${STARTING_DIR:?}"
done
