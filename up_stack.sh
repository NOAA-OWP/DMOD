#!/bin/bash

NAME=$(basename "${0}")

usage()
{
    local _O="${NAME}
    Build images, push to internal registry, and deploy NWM Docker stack

Usage:
    ${NAME} [options]           Perform full build for images
    ${NAME} [options] update    Only build image for the 'nwm' service, without using cache

Options
    --build-only                Only build the image(s); do not push or deploy
    --no-deploy                 Build the image(s) and push to registry, but do not deploy
    --skip-registry             Skip the step of pushing built images to registry
"
    echo "${_O}" 1>&2
}

generate_default_env_file()
{
    if [[ ! -e .env ]]; then
        local _STORE=''
        # Use /opt/nwm_c/images as default image store host volume directory, if it exists on the host
        if [[ -e /opt/nwm_c/images ]]; then
            _STORE=/opt/nwm_c/images
        # Otherwise, use a local (and git ignored) directory
        else
            _STORE=./docker_host_volumes/images
            [ ! -d ${_STORE} ] && mkdir -p ${_STORE}
        fi
        # Similar for this directory
        local _DOMAINS_DIR=''
        if [[ -e /apd_common/analysis_assim_extended ]]; then
            _DOMAINS_DIR=/apd_common/analysis_assim_extended
        else
            _DOMAINS_DIR=./docker_host_volumes/domains
            [ ! -d ${_DOMAINS_DIR} ] && mkdir -p ${_DOMAINS_DIR}
        fi


        cat > .env << EOF
DOCKER_STACK_NAME=nwm

DOCKER_MPI_NET_NAME=mpi-net
DOCKER_MPI_NET_SUBNET=10.0.0.0/24
DOCKER_MPI_NET_GATEWAY=10.0.0.1

DOCKER_HOST_IMAGE_STORE=${_STORE}
DOCKER_VOL_DOMAINS=${_DOMAINS_DIR}

DOCKER_INTERNAL_REGISTRY_HOST=127.0.0.1
DOCKER_INTERNAL_REGISTRY_PORT=5000

NWM_NAME=master
EOF
    fi
}

create_docker_mpi_net()
{
    docker network create \
        -d overlay \
        --scope swarm \
        --attachable \
        -o "{\"com.docker.network.driver.overlay.vxlanid_list\": \"4097\"}" \
        --subnet ${DOCKER_MPI_NET_SUBNET} \
        --gateway ${DOCKER_MPI_NET_GATEWAY} \
        mpi-net
}

# Work-around to use the .env file loading for compose files when deploying with docker stack (which doesn't by itself)
# See: https://github.com/moby/moby/issues/29133
deploy_docker_stack_from_compose_using_env()
{
    local _COMPOSE_FILE="${1}"
    local _STACK_NAME="${2}"

    if docker-compose -f "${_COMPOSE_FILE}" config > /dev/null; then
        docker stack deploy --compose-file <(docker-compose -f "${_COMPOSE_FILE}" config) "${_STACK_NAME}"
    else
        echo "Error: invalid docker-compose file; cannot start stack; exiting"
        exit 1
    fi
}

# If no .env file exists, create one with some default values
if [[ ! -e .env ]]; then
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
        --skip-registry)
            DO_SKIP_REGISTRY='true'
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

# Make sure the Docker mpi-net network is defined
if [[ $(docker network ls --filter name=mpi-net -q | wc -l) -eq 0 ]]; then
    create_docker_mpi_net
fi

# Make sure the local SSH keys are generated for the base image
[[ ! -d ./base/ssh ]] && mkdir ./base/ssh
[[ ! -e ./base/ssh/id_rsa ]] && ssh-keygen -t rsa -N '' -f ./base/ssh/id_rsa

# Make sure the internal Docker image registry container is running
if [[ $(docker stack services -q --filter "name=${DOCKER_STACK_NAME}_registry" "${DOCKER_STACK_NAME}" | wc -l) -eq 0 ]]; then
    echo "Starting internal Docker registry"
    #docker stack deploy --compose-file docker-registry.yml "${DOCKER_STACK_NAME}"
    deploy_docker_stack_from_compose_using_env docker-registry.yml "${DOCKER_STACK_NAME}"
else
    echo "Internal Docker registry is online"
fi

echo "Building custom Docker images"
#docker-compose -f docker-build.yml build
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

# Bail here if option set to only build
if [[ -n "${DO_BUILD_ONLY:-}" ]]; then
    exit
fi
# Otherwise, proceed ...

# Push to registry (unless we should skip)
if [[ -z "${DO_SKIP_REGISTRY:-}" ]]; then
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
