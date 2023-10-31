#!/usr/bin/env bash

INFO='Perform control tasks for a stack.'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

SHARED_FUNCS_DIR="${SCRIPT_PARENT_DIR}/shared"

# Import shared default script startup source
. ${SHARED_FUNCS_DIR}/default_script_setup.sh

# Import shared functions used for python-dev-related scripts
. ${SHARED_FUNCS_DIR}/py_dev_func.sh

# Import shared functions used for Docker-dev-related scripts
. ${SHARED_FUNCS_DIR}/docker_dev_func.sh

if [ -e "${PROJECT_ROOT}/.env" ]; then
    . "${PROJECT_ROOT}/.env"
fi

DEFAULT_COMPOSE_FILENAME="docker-compose.yml"

DOCKER_DIR="${PROJECT_ROOT:?}/docker"

ACTION_ORDER_STRING="networks check stop build push deploy"
ACTION_COUNT=0

details()
{
    local _O_DETAILS="
Action Execution Order:
    Including multiple actions to be executed is supported.
    Regardless of argument ordering, actions will be performed
    according to the following ordering:

    ${ACTION_ORDER_STRING}

    E.g., if \"deploy stop build\" are provided, the \"stop\"
    task will be executed first, followed by \"build,\" followed
    by \"deploy.\"

Config File Selection:
    When no explicit setting is supplied via command line option,
    the script will try to automatically find the appropriate
    Docker Compose config file when required for executing a
    particular action.

    The script will prioritize using a 'docker-build.yml' file,
    if present, for the 'build' and/or 'push' action.  Similarly,
    it will prioritize using 'docker-deploy.yml' for the 'deploy'
    action. It will use a '${DEFAULT_COMPOSE_FILENAME}' file by default
    for any action if a better file for that action is not
    available.

    Note that the script does not consider, when a prioritized
    config file exists, whether or not it is invalid (i.e., even
    in cases when a valid file of the default name does also
    exist).

"
    echo "${_O_DETAILS}" 2>&1
}

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} -hh
    ${NAME:?} [opts] <stack_dir_name> <action>[ <action>]*

Stack Selection:
    The stack to operate on is selected by giving the config
    sub-directory for the stack under the main directory:

    ${DOCKER_DIR}

Actions:
    networks
        Just check for and create any required Docker networks
        that don't yet exist.

    check
        Check and display whether the stack is running.

    build
        Build the Docker images as specified in the stack
        config file.

    push
        Push last built Docker images to the configured
        registry.

    deploy
        Deploy the stack.

    start
        An alias for the 'deploy' action.

    stop
        Stop the stack if it is currently running.

    restart
        Alias for combo of 'stop' and 'deploy' actions.

    See full help section on ACTION EXECUTION ORDER when there
    are multiple Actions.

Options:
    --[build-|deploy-]config <path>, -[b|d]c <path>
        Specify the Docker Compose config file for the stack,
        either for all purposes or specifically for building
        or deploying, either as a path or a file basename.

        Note that --config or -c cannot be used if either
        --build-config or --deploy-config is specified.

        Supplying as a file basename (i.e., an arg with no '/'
        characters), implies the file is in the main stack
        sub-directory, as determined from the 'stack_dir_name'
        argument.

    --build-args <args_string>
        Provide additional custom arguments to docker-compose
        command when building, passed as a single string arg to
        this script.

    --env-file <path>
        Set path to the environment file to use for sourcing
        config variables to use as part of Docker commands
        (defaults to ./.env if it exists).

    --init-networks, --no-init-networks
        Check for required/expected Docker networks and create
        any that don't exist, prior to executing the specified
        action(s). Effectively the same thing as adding the
        'networks' action. This is done by default for the 'build'
        and 'deploy' actions, but can be prevented using the 'no'
        variant.

    --stack-name <name>
        Specify explicitly the name of the stack to work with.
        This will override the typical logic for determining
        stack name, which is usually based on the path to config
        files.
"
    echo "${_O}" 2>&1
}

short_usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} -hh
    ${NAME:?} [opts] <stack_dir_name> <action>[ <action>]*

Actions:
    networks check build push deploy|start stop restart

Options:
    --[build-|deploy-]config <path> | -[b|d]|c <path>
    --build-args <args_string>
    --env-file <path>
    --[no-]init-networks
    --stack-name <name>

Use '-hh' for more descriptive help, or '-hhh' for further details.
"
    echo "${_O}" 2>&1
}

full_usage()
{
    usage
    details
}

determine_stack_name()
{
    if [ -n "${STACK_NAME:-}" ]; then
        return 0
    fi

    if [ "${STACK_DIR_NAME}" = "main" ]; then
        # Source from env kinda if determined this is the "main" stack
        STACK_NAME="nwm-${NWM_NAME:-master}"
    else
        STACK_NAME="${STACK_DIR_NAME}"
    fi
    #  If a prefix is defined, prepend it to the stack name
    if  [ ! -z "${STACK_PREFIX}" ]; then
        STACK_NAME="${STACK_PREFIX}_${STACK_NAME}"
    fi
}

process_deploy_action_arg()
{
    if [ -n "${DO_DEPLOY_ACTION:-}" ]; then
        short_usage
        exit 1
    else
        if [ -z "${DOCKER_NETWORK_IMPLICIT_FLAG:-}" ]; then
            DOCKER_NETWORK_IMPLICIT_FLAG='true'
        fi
        DO_DEPLOY_ACTION='true'
    fi
}

process_stop_action_arg()
{
    if [ -n "${DO_STOP_ACTION:-}" ]; then
        short_usage
        exit 1
    else
        DO_STOP_ACTION='true'
    fi
}

# Process the last group of command line args for actions (after setting the stack dir name)
process_action_args()
{
    case "${1}" in
        networks)
            [ -n "${DO_NETWORKS_ACTION:-}" ] && short_usage && exit 1
            DO_NETWORKS_ACTION='true'
            ;;
        check)
            [ -n "${DO_CHECK_ACTION:-}" ] && short_usage && exit 1
            DO_CHECK_ACTION='true'
            ;;
        stop)
            process_stop_action_arg
            ;;
        build)
            [ -n "${DO_BUILD_ACTION:-}" ] && short_usage && exit 1
            if [ -z "${DOCKER_NETWORK_IMPLICIT_FLAG:-}" ]; then
                DOCKER_NETWORK_IMPLICIT_FLAG='true'
            fi
            DO_BUILD_ACTION='true'
            ;;
        push)
            [ -n "${DO_PUSH_ACTION:-}" ] && short_usage && exit 1
            DO_PUSH_ACTION='true'
            ;;
        deploy|start)
            process_deploy_action_arg
            ;;
        restart)
            process_stop_action_arg
            process_deploy_action_arg
            ;;
        *)
            >&2 echo "Error: unsupported action argument '${1}'"
            short_usage
            exit 1
            ;;
    esac
}

bail_if_action_failed()
{
    # 1 : action return code
    # 2 : action name
    # 3 : (optional) when error, exit quietly without message to stderr
    if [ ${1:?} -ne 0 ]; then
        if [ "${3:-}" != "-q" ]; then
            >&2 echo "Error: requested '${2:?}' action failed (${1}); exiting without proceeding further"
        fi
        exit ${1}
    fi
}

deployment_networks_init()
{
    # First the mpi-net
    if [ "${DOCKER_MPI_NET_USE_CONFIG:-}" == "true" ]; then
        docker_dev_init_swarm_network_from_config ${DOCKER_MPI_NET_NAME:=mpi-net} \
                ${DOCKER_MPI_NET_NAME}-config \
                ${DOCKER_MPI_NET_DRIVER:=macvlan} \
                ${DOCKER_MPI_NET_VXLAN_ID:=4097}
    else
        docker_dev_init_swarm_network ${DOCKER_MPI_NET_NAME:=mpi-net} \
                ${DOCKER_MPI_NET_SUBNET:?Cannot init ${DOCKER_MPI_NET_NAME} network without configured subnet} \
                ${DOCKER_MPI_NET_GATEWAY:?Cannot init ${DOCKER_MPI_NET_NAME} network without configured gateway} \
                ${DOCKER_MPI_NET_DRIVER:-overlay}
    fi

    # Then the requests-net
    docker_dev_init_swarm_network ${DOCKER_REQUESTS_NET_NAME:=requests-net} \
            ${DOCKER_REQUESTS_NET_SUBNET:?Cannot init ${DOCKER_REQUESTS_NET_NAME} network without configured subnet} \
            ${DOCKER_REQUESTS_NET_GATEWAY:?Cannot init ${DOCKER_REQUESTS_NET_NAME} network without configured gateway} \
            ${DOCKER_REQUESTS_NET_DRIVER:-overlay}

    # Finally the main-internal-net
    docker_dev_init_swarm_network ${DOCKER_MAIN_INTERNAL_NET_NAME:=main-internal-net} \
            ${DOCKER_MAIN_INTERNAL_NET_SUBNET:?Cannot init ${DOCKER_MAIN_INTERNAL_NET_NAME} network without configured subnet} \
            ${DOCKER_MAIN_INTERNAL_NET_GATEWAY:?Cannot init ${DOCKER_MAIN_INTERNAL_NET_NAME} network without configured gateway} \
            ${DOCKER_MAIN_INTERNAL_NET_DRIVER:-overlay}
}

gen_docker_build_ssh_dirs()
{
    # 1 - expected SSH directory
    if [ ! -d "${1:?No SSH build arg given}" ]; then
        mkdir "${1}"
    fi
    if [ ! -f "${1}/id_rsa" ]; then
        ssh-keygen -N "" -f "${1}/id_rsa" -t rsa
    fi
}

exec_requested_actions()
{
    # First, handle network init if set to
    if [ "${DO_NETWORKS_ACTION:-}" ] || [ "${DO_DOCKER_NETWORK:-false}" == "true" ]; then
        deployment_networks_init
    fi

    if [ -n "${DO_CHECK_ACTION:-}" ]; then
        docker_dev_check_stack_running "${STACK_NAME:?}"
        bail_if_action_failed $? check -q
    fi

    if [ -n "${DO_STOP_ACTION:-}" ]; then
        docker_dev_remove_stack ${STACK_NAME:?}
        bail_if_action_failed $? stop
    fi

    if [ -n "${DO_BUILD_ACTION:-}" ]; then
        gen_docker_build_ssh_dirs ${DOCKER_BASE_IMAGE_SSH_HOST_DIR:-./docker/main/base/ssh}
        gen_docker_build_ssh_dirs ${DOCKER_NGEN_IMAGE_SSH_HOST_DIR:-./docker/main/ngen/ssh}
        docker_pre_deploy_create_secrets ${STACK_DIR_NAME:?Stack dir name not known; cannot create secrets pre-deploy}
        echo "Building Docker images for stack ${STACK_NAME:?}"
        docker_dev_build_stack_images "${DOCKER_BUILD_CONFIG:?}" "${STACK_NAME:?}" ${DOCKER_IMAGE_BUILD_EXTRA_ARGS:-}
        bail_if_action_failed $? build
    fi

    if [ -n "${DO_PUSH_ACTION:-}" ]; then
        # TODO: do health check or something to make sure registry is available
        echo "Pushing ${STACK_NAME:?} images to internal registry"
        docker-compose -f ${DOCKER_BUILD_CONFIG:?} push
        bail_if_action_failed $? push
    fi

    if [ -n "${DO_DEPLOY_ACTION:-}" ]; then
        # TODO: sanity check that given stack directory name exists
        # Run some checks/default setup first
        docker_pre_deploy_bind_mount_dir_check ${STACK_DIR_NAME:?No stack directory name; cannot check bind mounts prior to deploying}
        docker_pre_deploy_create_secrets ${STACK_DIR_NAME:?No stack directory name; cannot check Docker secret files prior to deploying}
        docker_pre_deploy_scheduler_resources ${STACK_DIR_NAME:?No stack directory name; cannot create scheduler resource files prior to deploying}
        echo "Deploying stack ${STACK_NAME:?}"
        docker_dev_deploy_stack_from_compose_using_env "${DOCKER_DEPLOY_CONFIG:?}" "${STACK_NAME:?}"
        bail_if_action_failed $? deploy
    fi
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
        -h)
            short_usage
            exit
            ;;
        -hh|--help|-help)
            usage
            exit
            ;;
        -hhh)
            full_usage
            exit
            ;;
        --config|-c)
            [ -n "${DOCKER_BUILD_CONFIG_ARG:-}" ] && short_usage && exit 1
            [ -n "${DOCKER_DEPLOY_CONFIG_ARG:-}" ] && short_usage && exit 1
            DOCKER_BUILD_CONFIG_ARG="${2}"
            DOCKER_DEPLOY_CONFIG_ARG="${2}"
            shift
            ;;
        --build-config|-bc)
            [ -n "${DOCKER_BUILD_CONFIG_ARG:-}" ] && short_usage && exit 1
            DOCKER_BUILD_CONFIG_ARG="${2}"
            shift
            ;;
        --deploy-config|-dc)
            [ -n "${DOCKER_DEPLOY_CONFIG_ARG:-}" ] && short_usage && exit 1
            DOCKER_DEPLOY_CONFIG_ARG="${2}"
            shift
            ;;
        --env-file)
            [ -n "${DOCKER_ENV_FILE_PATH:-}" ] && short_usage && exit 1
            DOCKER_ENV_FILE_PATH="${2}"
            if [ ! -f "${DOCKER_ENV_FILE_PATH}" ]; then
                echo "Error: provided env file '${DOCKER_ENV_FILE_PATH}' not found"
                exit 1
            fi
            shift
            ;;
        --build-args)
            [ -n "${DOCKER_IMAGE_BUILD_EXTRA_ARGS:-}" ] && short_usage && exit 1
            DOCKER_IMAGE_BUILD_EXTRA_ARGS="${2}"
            shift
            ;;
        --init-networks)
            [ -n "${DOCKER_NETWORK_EXPLICIT_FLAG:-}" ] && short_usage && exit 1
            DOCKER_NETWORK_EXPLICIT_FLAG=${1}
            ;;
        --no-init-networks)
            [ -n "${DOCKER_NETWORK_EXPLICIT_FLAG:-}" ] && short_usage && exit 1
            DOCKER_NETWORK_EXPLICIT_FLAG=${1}
            ;;
        --stack-name)
            [ -n "${STACK_NAME:-}" ] && short_usage && exit 1
            STACK_NAME="${2}"
            shift
            ;;
        *)
            if [ -z "${STACK_DIR_NAME:-}" ]; then
                STACK_DIR_NAME="${1}"
            else
                process_action_args "${1}"
                ACTION_COUNT=$((ACTION_COUNT+1))
            fi
            ;;
    esac
    shift
done

# Default to using .env if that file exists
if [ -z "${DOCKER_ENV_FILE_PATH:-}" ]; then
    if [ -f ./.env ]; then
        DOCKER_ENV_FILE_PATH="./.env"
    fi
fi
# Then, if we have a env file, export its contents (filtering out comment lines)
if [ -n "${DOCKER_ENV_FILE_PATH:-}" ]; then
    for line in `cat "${DOCKER_ENV_FILE_PATH:-}" | sed '/\s*\#.*/d' | sed '/^[[:space:]]*$/d'`; do
        #echo "exporting: ${line}"
        export "${line}"
    done
fi

# Set the appropriate value for whether networks should be checked
# When explicit arg is given, respect that
if [ -n "${DOCKER_NETWORK_EXPLICIT_FLAG:-}" ]; then
    if [ "${DOCKER_NETWORK_EXPLICIT_FLAG}" == "--init-networks" ]; then
        DO_DOCKER_NETWORK='true'
    else
        DO_DOCKER_NETWORK='false'
    fi
# Otherwise, if one of the build actions was processed, the implied flag will be set
elif [ -n "${DOCKER_NETWORK_IMPLICIT_FLAG:-}" ]; then
    DO_DOCKER_NETWORK='true'
# Otherwise, explicitly set false
else
    DO_DOCKER_NETWORK='false'
fi

# Validate stack directory
if [ -z "${STACK_DIR_NAME:-}" ]; then
    short_usage
    exit 1
fi
STACK_DIR_PATH="${DOCKER_DIR}/${STACK_DIR_NAME}"
if [ ! -d "${STACK_DIR_PATH}" ]; then
    >&2 echo "Error: stack directory '${STACK_DIR_PATH}' does not exist!"
    short_usage
    exit 1
fi

# If we got command line args, set the build/deploy config paths appropriately from them
# Make sure to consider whether they are basenames or paths
if [ -n "${DOCKER_BUILD_CONFIG_ARG}" ]; then
    if [[ ${DOCKER_BUILD_CONFIG_ARG} =~ "/" ]]; then
        DOCKER_BUILD_CONFIG="${DOCKER_BUILD_CONFIG_ARG}"
    else
        DOCKER_BUILD_CONFIG="${STACK_DIR_PATH}/${DOCKER_BUILD_CONFIG_ARG}"
    fi
fi
if [ -n "${DOCKER_DEPLOY_CONFIG_ARG}" ]; then
    if [[ ${DOCKER_DEPLOY_CONFIG_ARG} =~ "/" ]]; then
        DOCKER_DEPLOY_CONFIG="${DOCKER_DEPLOY_CONFIG_ARG}"
    else
        DOCKER_DEPLOY_CONFIG="${STACK_DIR_PATH}/${DOCKER_DEPLOY_CONFIG_ARG}"
    fi
fi

# Set docker configs if not already set (if actions require), first for build ...
if [ -n "${DO_BUILD_ACTION}" ] || [ -n "${DO_PUSH_ACTION}" ]; then
    if [ -z "${DOCKER_BUILD_CONFIG:-}" ]; then
        if [ -e "${STACK_DIR_PATH}/docker-build.yml" ]; then
            DOCKER_BUILD_CONFIG="${STACK_DIR_PATH}/docker-build.yml"
        else
            DOCKER_BUILD_CONFIG="${STACK_DIR_PATH}/${DEFAULT_COMPOSE_FILENAME}"
        fi
    fi
fi
# ... then for deploy config
if [ -z "${DOCKER_DEPLOY_CONFIG:-}" ] && [ -n "${DO_DEPLOY_ACTION}" ]; then
    if [ "$(docker_check_daemon_os)" == "${DOCKER_DESKTOP_OS_NAME}" ] && [ -e "${STACK_DIR_PATH}/docker-single-node.yml" ]; then
        DOCKER_DEPLOY_CONFIG="${STACK_DIR_PATH}/docker-single-node.yml"
    elif [ $(docker node ls -q | wc -l) -eq 1 ] && [ -e "${STACK_DIR_PATH}/docker-single-node.yml" ]; then
        DOCKER_DEPLOY_CONFIG="${STACK_DIR_PATH}/docker-single-node.yml"
    elif [ -e "${STACK_DIR_PATH}/docker-deploy.yml" ]; then
        DOCKER_DEPLOY_CONFIG="${STACK_DIR_PATH}/docker-deploy.yml"
    else
        DOCKER_DEPLOY_CONFIG="${STACK_DIR_PATH}/${DEFAULT_COMPOSE_FILENAME}"
    fi
fi

# Validate Docker Configs exist and are valid
if [ -n "${DOCKER_BUILD_CONFIG:-}" ]; then
    docker_dev_validate_compose_config "${DOCKER_BUILD_CONFIG}"
    if [ $? -ne 0 ]; then
        exit 1
    fi
fi
if [ -n "${DOCKER_DEPLOY_CONFIG:-}" ]; then
    docker_dev_validate_compose_config "${DOCKER_DEPLOY_CONFIG}"
    if [ $? -ne 0 ]; then
        exit 1
    fi
fi

# Derive STACK_NAME if not already set (probably from STACK_DIR_NAME), as this is required for certain stack commands
determine_stack_name

# Finally, execute requested actions in appropriate order
exec_requested_actions
