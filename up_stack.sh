#!/bin/bash
NAME=$(basename "${0}")
DOCKER_READY_PUSH_REGISTRY_TIME=0

usage()
{
    local _O="${NAME}
    Build images, push to internal registry, and deploy NWM Docker stack

Usage:
    ${NAME} [opts]          Perform full build for images
    ${NAME} [opts] update   Only build image for the 'nwm' service, without using cache

Options
    --build-only            Only build the image(s); do not push or deploy

    --init-env              Initialize a default .env file, not already existing, then exit
                            This will be done by default when necessary before image builds

    --init-env-clear        Initialize a default .env file, clearing any existing, then exit

    --init-env-show         Output values used when initializing a default .env, then exit

    --no-deploy             Build the image(s) and push to registry, but do not deploy

    --skip-registry         Skip the step of pushing built images to registry

    --no-internal-registry  Do not check for or start an internal Docker registry (requires
                            all pushes/pulls be from other configured registries)
"
    echo "${_O}" 1>&2
}

# For local development, get/set the base directory for bind-mount subdirectories
get_dev_bind_mounts_root()
{
    local _PARENT_DIR

    if [[ -z ${DEV_BIND_MOUNTS_BASE_DIR:-} ]]; then
        _PARENT_DIR=$(cd "`dirname "${0}"`" && pwd)
        echo "${_PARENT_DIR}" && exit
        DEV_BIND_MOUNTS_BASE_DIR="${_PARENT_DIR}/docker_host_volumes"
    fi
}

determine_default_image_store_bind_mount()
{
    local _SD
    # Use /opt/nwm_c/images as default image store host volume directory, if it exists on the host
    if [[ -e /opt/nwm_c/images ]]; then
        _SD=/opt/nwm_c/images
    # Otherwise, use a local (and git ignored) directory
    else
        get_dev_bind_mounts_root
        _SD=${DEV_BIND_MOUNTS_BASE_DIR}/docker_host_volumes/images
        [ ! -d ${_SD} ] && mkdir -p ${_SD}
    fi
    echo "${_SD}"
}

determine_default_domains_data_bind_mount()
{
    local _DD
    # Use /opt/nwm_c/images as default image store host volume directory, if it exists on the host
    if [[ -e /opt/nwm_c/images ]]; then
        _DD=/opt/nwm_c/images
    # Otherwise, use a local (and git ignored) directory
    else
        get_dev_bind_mounts_root
        _DD=${DEV_BIND_MOUNTS_BASE_DIR}/docker_host_volumes/domains
        [ ! -d ${_DD} ] && mkdir -p ${_DD}
    fi
    echo "${_DD}"
}

generate_default_env_file()
{
    if [[ ! -e ${DEFAULT_ENV_OUTPUT_FILE:-.env} ]]; then
        local _EXAMPLE_ENV="./example.env"
        # Make sure the expected example default env file exists
        if [[ ! -f ${_EXAMPLE_ENV} ]]; then
            echo "Error: cannot proceed; basis for generated ${DEFAULT_ENV_OUTPUT_FILE:-.env} file '${_EXAMPLE_ENV}' does not exist"
            exit 1
        fi

        _IMBM=`determine_default_image_store_bind_mount`
        _DDBM=`determine_default_domains_data_bind_mount`

        cat ${_EXAMPLE_ENV} \
            | sed "s|\(DOCKER_HOST_IMAGE_STORE=\).*|\1${_IMBM}|" \
            | sed "s|\(DOCKER_VOL_DOMAINS=\).*|\1${_DDBM}|" \
            >> ${DEFAULT_ENV_OUTPUT_FILE:-.env}
    fi
}

# Work-around to use the .env file loading for compose files when deploying with docker stack (which doesn't by itself)
# See: https://github.com/moby/moby/issues/29133
deploy_docker_stack_from_compose_using_env()
{
    local _COMPOSE_FILE="${1}"
    local _STACK_NAME="${2}"

    if docker-compose -f "${_COMPOSE_FILE}" config > /dev/null 2>&1; then
        docker stack deploy --compose-file <(docker-compose -f "${_COMPOSE_FILE}" config 2>/dev/null) "${_STACK_NAME}"
    else
        echo "Error: invalid docker-compose file; cannot start stack; exiting"
        exit 1
    fi
}

init_if_not_exist_docker_networks()
{
    # Make sure the Docker mpi-net network is defined
    if [[ $(docker network ls --filter name=${DOCKER_MPI_NET_NAME:=mpi-net} -q | wc -l) -eq 0 ]]; then
        docker network create \
            -d overlay \
            --scope swarm \
            --attachable \
            -o "{\"com.docker.network.driver.overlay.vxlanid_list\": \"${DOCKER_MPI_NET_VXLAN_ID:=4097}\"}" \
            --subnet ${DOCKER_MPI_NET_SUBNET} \
            --gateway ${DOCKER_MPI_NET_GATEWAY} \
            ${DOCKER_MPI_NET_NAME}
    fi

    # Make sure the Docker requests-net network is defined
    if [[ $(docker network ls --filter name=${DOCKER_REQUESTS_NET_NAME:=requests-net} -q | wc -l) -eq 0 ]]; then
        docker network create \
            -d overlay \
            --scope swarm \
            --attachable \
            --subnet ${DOCKER_REQUESTS_NET_SUBNET} \
            --gateway ${DOCKER_REQUESTS_NET_GATEWAY} \
            ${DOCKER_REQUESTS_NET_NAME:=requests-net}
    fi
}

init_registry_service_if_needed()
{
    # Make sure the internal Docker image registry container is running if configured to use it

    [[ -z "${DOCKER_INTERNAL_REGISTRY_STACK_NAME:-}" ]] && DOCKER_INTERNAL_REGISTRY_STACK_NAME=dev_registry_stack
    [[ -z "${DOCKER_INTERNAL_REGISTRY_SERVICE_NAME:-}" ]] && DOCKER_INTERNAL_REGISTRY_SERVICE_NAME="${DOCKER_INTERNAL_REGISTRY_STACK_NAME}_registry"

    if [[ ${DO_SKIP_INTERNAL_REGISTRY} == 'true' ]]; then
        echo "Options set to not use internal Docker registry for pushing or pulling of images; skipping init steps"
    elif [[ $(docker stack services -q --filter "name=${DOCKER_INTERNAL_REGISTRY_SERVICE_NAME}" "${DOCKER_INTERNAL_REGISTRY_STACK_NAME}" | wc -l) -eq 0 ]]; then
        echo "Starting internal Docker registry"
        #docker stack deploy --compose-file docker-registry.yml "${DOCKER_STACK_NAME}"
        deploy_docker_stack_from_compose_using_env docker-registry.yml "${DOCKER_INTERNAL_REGISTRY_STACK_NAME}"
        # If starting, set our "ready-to-push" time to 5 seconds in the future
        DOCKER_READY_PUSH_REGISTRY_TIME=$((5+$(date +%s)))
    else
        echo "Internal Docker registry is online"
        # If the registry was already started, we can push starting right now
        DOCKER_READY_PUSH_REGISTRY_TIME=$(date +%s)
    fi
}

build_docker_images()
{
    echo "Building custom Docker images"
    if [[ -n "${DO_UPDATE:-}" ]]; then
        if ! docker-compose -f docker-build.yml build --no-cache nwm; then
            echo "Previous build command failed; exiting"
            exit 1
        fi
    else
        if ! docker-compose -f docker-build.yml build; then
            echo "Previous build command failed; exiting"
            exit 1
        fi
    fi
}

# If no .env file exists, create one with some default values
if [[ ! -e .env ]]; then
    echo "Creating default .env file in current directory"
    ENV_JUST_CREATED='true'
    generate_default_env_file
fi
# Source .env
[[ -e .env ]] && source .env

while [[ ${#} -gt 0 ]]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        --build-only)
            DO_BUILD_ONLY='true'
            ;;
        --init-env)
            # This will have just happened (if necessary) from the code above the loop, so just exit
            [[ -z "${ENV_JUST_CREATED:-}" ]] && echo "File .env already exists; not re-initializing"
            exit
            ;;
        --init-env-clear)
            # Remove whatever exists and re-init a default file
            [[ -e .env ]] && rm .env
            generate_default_env_file
            exit
            ;;
        --init-env-show)
            DEFAULT_ENV_OUTPUT_FILE="/tmp/temp_upstack_env_$(date +'%Y%m%d%H%M%S')"
            generate_default_env_file
            cat "${DEFAULT_ENV_OUTPUT_FILE}"
            rm "${DEFAULT_ENV_OUTPUT_FILE}"
            exit
            ;;
        --skip-registry)
            DO_SKIP_REGISTRY_PUSH='true'
            ;;
        --no-internal-registry)
            DO_SKIP_INTERNAL_REGISTRY='true'
            ;;
        --no-deploy)
            DO_SKIP_DEPLOY='true'
            ;;
        update|--update|-update)
            DO_UPDATE='true'
            ;;
        *)
            usage
            exit 1
            ;;
    esac
    shift
done

# TODO: consider doing some sanity checking on sourced .env values

init_if_not_exist_docker_networks

# Make sure the local SSH keys are generated for the base image
[[ ! -d ./base/ssh ]] && mkdir ./base/ssh
[[ ! -e ./base/ssh/id_rsa ]] && ssh-keygen -t rsa -N '' -f ./base/ssh/id_rsa

init_registry_service_if_needed

# Build (or potentially just update) our images
build_docker_images

# Bail here if option set to only build
if [[ -n "${DO_BUILD_ONLY:-}" ]]; then
    exit
fi
# Otherwise, proceed ...

# Push to registry (unless we should skip)
if [[ -z "${DO_SKIP_REGISTRY_PUSH:-}" ]]; then
    # Make sure we wait until the "ready-to-push" time determine in the logic for starting the registry service
    # Make sure if we start the registry here that we give it a little time to come all the way up before pushing
    # TODO: maybe change this to a health check later
    while [[ $(date +%s) -lt ${DOCKER_READY_PUSH_REGISTRY_TIME} ]]; do
        sleep 1
    done
    echo "Pushing custom Docker images to internal registry"
    if ! docker-compose -f docker-build.yml push; then
        echo "Previous push command failed; exiting"
        exit 1
    fi
else
    echo "Skipping step to push images to registry"
fi

# Or bail here if this option is set
if [[ -n "${DO_SKIP_DEPLOY:-}" ]]; then
    exit
fi
echo "Deploying NWM stack"
#docker stack deploy --compose-file docker-deploy.yml "nwm-${NWM_NAME:-master}"
deploy_docker_stack_from_compose_using_env docker-deploy.yml "nwm-${NWM_NAME:-master}"
