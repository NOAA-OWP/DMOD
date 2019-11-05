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
        local _ANALYSIS_ASSIM=''
        if [[ -e /apd_common/analysis_assim_extended ]]; then
            _ANALYSIS_ASSIM=/apd_common/analysis_assim_extended
        else
            _ANALYSIS_ASSIM=./docker_host_volumes/analysis_assim_extended
            [ ! -d ${_ANALYSIS_ASSIM} ] && mkdir -p ${_ANALYSIS_ASSIM}
        fi


        cat > .env << EOF
DOCKER_STACK_NAME='nwm'

DOCKER_MPI_NET_NAME='mpi-net'
DOCKER_MPI_NET_SUBNET='10.0.0.0/24'
DOCKER_MPI_NET_GATEWAY='10.0.0.1'

DOCKER_HOST_IMAGE_STORE="${_STORE}"
DOCKER_VOL_ANALYSIS_ASSIM="${_ANALYSIS_ASSIM}"

DOCKER_INTERNAL_REGISTRY_PORT='5000'

NWM_NAME='master'
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

start_docker_registry()
{
    echo "Deploying registry container to ${DOCKER_STACK_NAME} stack"
    docker stack deploy --compose-file docker-registry.yml "${DOCKER_STACK_NAME}"
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
if [[ $(docker stack services -q --filter name=registry | wc -l) -eq 0 ]]; then
    start_docker_registry
fi

echo "Building custom Docker images"
#docker-compose -f docker-build.yml build
if [[ -n "${DO_UPDATE:-}" ]]; then
    docker-compose -f docker-build.yml build --no-cache nwm
else
    docker-compose -f docker-build.yml build
fi

# Bail here if option set
if [[ -n "${DO_BUILD_ONLY:-}" ]]; then
    exit
fi
# Otherwise, proceed and push to registry
echo "Pushing custom Docker images to internal registry"
docker-compose -f docker-build.yml push

# Or bail here if this option is set
if [[ -n "${DO_SKIP_DEPLOY:-}" ]]; then
    exit
fi
echo "Deploying NWM stack"
docker stack deploy --compose-file docker-deploy.yml "nwm-${NWM_NAME:-master}"
