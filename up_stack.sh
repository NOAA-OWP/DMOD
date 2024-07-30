#!/usr/bin/env bash
NAME=$(basename "${0}")

SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

CONTROL_SCRIPT="./scripts/control_stack.sh"
MAIN_STACK_REF_NAME="main"
PY_SOURCES_STACK_REF_NAME="py-sources"
GUI_STACK_REF_NAME="nwm_gui"

usage()
{
    local _O="${NAME}
    Wrapper script for a series of calls to ${CONTROL_SCRIPT} to perform steps to
    start or stop a local DMoD environment.

Usage:
    ${NAME} [opts]

Options
    --down|-d
        Instead of starting, bring down an already running environment,

    --gui
        Include starting/stopping the project-internal GUI stack
"
    echo "${_O}" 1>&2
}

generate_default_env_file()
{
    # 1 : image store bind mount
    # 2 : domains data bind mount

    if [[ -e .env ]]; then
        return 0
    elif [[ ! -e example.env ]]; then
        >&2 echo "Error: cannot initialize new .env file - example.env not found in working directory"
        exit 1
    elif [ ${#} -ne 2 ]; then
        >&2 echo "Error: invalid args to generate_default_env_file()"
        exit 1
    else
        cat example.env \
            | sed "s|\(DOCKER_HOST_IMAGE_STORE=\).*|\1${1:?}|" \
            | sed "s|\(DOCKER_VOL_DOMAINS=\).*|\1${2:?}|" \
            >> .env
    fi
}

exit_if_failed()
{
    if [ ${1:?} -ne 0 ]; then
        exit ${1}
    fi
}

exec_stop()
{
    # If option set, and stack is running, stop GUI
    if [ -n "${DO_GUI:-}" ]; then
        "${CONTROL_SCRIPT}" "${GUI_STACK_REF_NAME:?}" check > /dev/null
        if [ ${?} -eq 0 ]; then
            echo "Stopping ${GUI_STACK_REF_NAME:?} stack"
            "${CONTROL_SCRIPT}" "${GUI_STACK_REF_NAME:?}" stop
        fi
    fi

    # If running, stop main stack
    "${CONTROL_SCRIPT}" "${MAIN_STACK_REF_NAME:?}" check > /dev/null
    if [ ${?} -eq 0 ]; then
        echo "Stopping previously running ${MAIN_STACK_REF_NAME:?} stack"
        "${CONTROL_SCRIPT}" "${MAIN_STACK_REF_NAME:?}" stop
    fi

    # Note that we don't stop a running registry here either
}

exec_start()
{
    # Check if registry is managed by project
    if [ "${DOCKER_INTERNAL_REGISTRY_IS_MANAGED:-}" == "true" ]; then
        # If so, make sure it is running, starting if necessary
        # Note that in this case, we want to keep any previously started service
        # Also, add option to init networks when they don't already exist
        "${CONTROL_SCRIPT}" --init-networks "${DOCKER_INTERNAL_REGISTRY_STACK_NAME:?}" check > /dev/null
        if [ ${?} -ne 0 ]; then
            "${CONTROL_SCRIPT}" -c "${DOCKER_INTERNAL_REGISTRY_STACK_CONFIG:?}" "${DOCKER_INTERNAL_REGISTRY_STACK_NAME:?}" deploy
            exit_if_failed ${?}
            # TODO: come up with a better check; for now, just pause for a few seconds
            echo "Waiting on registry service to fully start"
            sleep 5
        fi
    fi

    # Then build and push python packages
    "${CONTROL_SCRIPT}" "${PY_SOURCES_STACK_REF_NAME:?}" build push

    # TODO catch abnormal exit from py sources build and stop

    # Then build, push, and deploy main
    "${CONTROL_SCRIPT}" "${MAIN_STACK_REF_NAME:?}" check > /dev/null
    if [ ${?} -eq 0 ]; then
        echo "Stopping previously running ${MAIN_STACK_REF_NAME:?} stack"
        "${CONTROL_SCRIPT}" "${MAIN_STACK_REF_NAME:?}" stop
    fi
    "${CONTROL_SCRIPT}" "${MAIN_STACK_REF_NAME:?}" build push deploy

    # Then, potentially, build and deploy gui
    if [ -n "${DO_GUI:-}" ]; then
        "${CONTROL_SCRIPT}" "${GUI_STACK_REF_NAME:?}" check > /dev/null
        if [ ${?} -eq 0 ]; then
            echo "Stopping previously running ${GUI_STACK_REF_NAME:?} stack"
            "${CONTROL_SCRIPT}" "${GUI_STACK_REF_NAME:?}" stop
        fi
        "${CONTROL_SCRIPT}" "${GUI_STACK_REF_NAME:?}" build deploy
    fi
}

# If no .env file exists, create one with some default values
if [[ ! -e .env ]]; then
    echo "Creating default .env file in current directory"
    if [[ -d /opt/nwm_c ]]; then
        generate_default_env_file /opt/nwm_c/images /opt/nwm_c/domains
    else
        generate_default_env_file ./docker_host_volumes/images ./docker_host_volumes/domains
    fi
fi
# Source .env
[[ -e .env ]] && source .env

while [[ ${#} -gt 0 ]]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        -d|--down)
            [ -n "${DO_STOP:-}" ] && usage && exit 1
            DO_STOP='true'
            ;;
        --gui)
            [ -n "${DO_GUI:-}" ] && usage && exit 1
            DO_GUI='true'
            ;;
        *)
            usage
            exit 1
            ;;
    esac
    shift
done

# Make sure control script exists, or bail
if [ ! -e "${CONTROL_SCRIPT}" ] || [ ! -x "${CONTROL_SCRIPT}" ]; then
    >&2 echo "Error: script ${CONTROL_SCRIPT} does not exist or is not executeable"
    exit 1
fi

if [ -n "${DO_STOP:-}" ]; then
    exec_stop
    exit $?
else
    exec_start
    exit $?
fi
