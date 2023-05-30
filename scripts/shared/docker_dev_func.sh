#!/usr/bin/env sh

DOCKER_DESKTOP_OS_NAME="Docker Desktop"

docker_dev_check_volume_exists()
{
    # $1 is volume name
    for v in $(docker volume ls -q); do
        if [ "${1:?}" = "${v}" ]; then
            return 0
        fi
    done
    return 1
}

docker_dev_check_for_s3fs_volume_plugin()
{
    # $1 is the name of the plugin alias, which defaults to s3fs if left out
    if [ $(docker plugin ls | grep ${1:-s3fs} | wc -l) -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

docker_dev_init_s3fs_volume_plugin()
{
    # $1 is the access key value
    # $2 is the secret key value
    # $3 is the endpoint URL
    # $4 is the name of the plugin alias, which defaults to s3fs if left out
    # $5 is the name of the plugin Docker image, which defaults to mochoa/s3fs-volume-plugin if left out

    _S3FS_DOCKER_PLUGIN_NAME="${4:-s3fs}"

    docker plugin install ${5:-mochoa/s3fs-volume-plugin} --alias ${_S3FS_DOCKER_PLUGIN_NAME} --grant-all-permissions --disable
    docker plugin set s3fs AWSACCESSKEYID=${1:?}
    docker plugin set s3fs AWSSECRETACCESSKEY=${2:?}
    docker plugin set s3fs DEFAULT_S3FSOPTS="allow_other,uid=${DOCKER_CONTAINER_USER_ID:-1000},gid=${DOCKER_CONTAINER_GROUP_ID:-1000},url=${3:?},use_path_request_style"
    docker plugin enable ${_S3FS_DOCKER_PLUGIN_NAME}
}

# $1 is the Stack service name
# $2 (optional) is the service replica number (defaults to the first; i.e., '1')
docker_dev_get_stack_service_task_name()
{
    echo "${1:?No service name given when requesting service task id}.${2:-1}"
}

# Output the id of a running Docker service task instance (i.e. something associated with a container)
# $1 is the Docker Stack name
# $2 is the Stack service name
# $3 (optional) is the service replica number (defaults to the first; i.e., '1')
docker_dev_get_stack_service_task_id()
{
    # Service task name is just <stack_name><service_name>.<replica_number>
    docker stack ps --no-trunc \
        ${1:?No stack name given when requesting service task id} \
        -f desired-state=running \
        -f name="$(docker_dev_get_stack_service_task_name ${@:2})" \
        -q
}

# Get the id of the actual Docker container for a running service task instance
# $1 is the Docker Stack name
# $2 is the Stack service name
# $3 (optional) is the service replica number (defaults to the first; i.e., '1')
docker_dev_get_stack_service_task_container_name()
{
    # Container name is just <service_task_name>.<service_task_id>
    echo "$(docker_dev_get_stack_service_task_name ${@:2}).$(docker_dev_get_stack_service_task_id ${@})"
}

# Get the id of the actual Docker container for a running service task instance
# $1 is the Docker Stack name
# $2 is the Stack service name
# $3 (optional) is the service replica number (defaults to the first; i.e., '1')
docker_dev_get_stack_service_task_container_id()
{
    docker ps -f name="$(docker_dev_get_stack_service_task_container_name ${@})" -q

}

docker_dev_init_swarm_network()
{
    # 1 - network name
    # 2 - subnet
    # 3 - gateway
    # 4 - driver
    # 5 - VXLAN ID (optional)

    # Sanity check args
    if [[ ${#} -lt 4 ]]; then
        >&2 echo "Error: cannot init swarm network without name, subnet, gateway, and driver args"
        return 1
    # This also checks to make sure last arg is a number (e.g., driver was omitted, but VXLAN ID was supplied)
    elif [ ${4} -eq ${4} ] 2>/dev/null; then
        >&2 echo "Error: driver arg (${4}) looks like integer (VXLAN ID); check that no args were omitted"
        return 1
    fi

    if [[ ${#} -eq 5 ]]; then
        if ! [ ${5} -eq ${5} ] 2>/dev/null; then
            >&2 echo "Error: invalid VXLAN ID arg"
            return 1
        fi
    fi

    if [[ $(docker network ls --filter name=${1} -q | wc -l) -eq 0 ]]; then
        if [[ ${#} -eq 5 ]]; then
            docker network create \
                        --driver "${4}" \
                        --scope swarm \
                        --attachable \
                        --opt "com.docker.network.driver.${4}.vxlanid_list"="${5}" \
                        --subnet ${2} \
                        --gateway ${3} \
                        ${1}
        else
            docker network create --driver "${4}" --scope swarm --attachable --subnet ${2} --gateway ${3} ${1}
        fi
    fi
}

docker_dev_init_swarm_network_from_config()
{
    # 1 - network name
    # 2 - config name
    # 3 - driver
    # 4 - VXLAN ID (optional)

    # Sanity check args
    if [ ${#} -lt 3 ]; then
        >&2 echo "Error: cannot init swarm network from config without name, config, and driver args"
        return 1
    # This also checks to make sure last arg is a number (e.g., driver was omitted, but VXLAN ID was supplied)
    elif [ ${3} -eq ${3} ] 2>/dev/null; then
        >&2 echo "Error: driver arg (${3}) looks like integer (VXLAN ID); check that no args were omitted"
        return 1
    fi

    if [ ${#} -eq 4 ]; then
        if ! [ ${4} -eq ${4} ] 2>/dev/null; then
            >&2 echo "Error: invalid VXLAN ID arg"
            return 1
        fi
    fi

    if [ $(docker network ls --filter name=${1} -q | wc -l) -eq 0 ]; then
        if [ ${#} -eq 4 ]; then
            docker network create \
                        --driver "${3}" \
                        --scope swarm \
                        --attachable \
                        --opt "com.docker.network.driver.${3}.vxlanid_list"="${4}" \
                        --config-from "${2}" \
                        ${1}
        else
            docker network create --driver "${3}" --scope swarm --attachable --config-from "${2}" ${1}
        fi
    fi
}

docker_dev_validate_compose_config()
{
    if [ ! -e "${1:?}" ]; then
        >&2 echo "Error: Docker Compose config ${1} does not exist"
        return 1
    fi
    #if docker-compose -f "${1}" config > /dev/null 2>&1; then
    if docker-compose -f "${1}" config > /dev/null; then
        return 0
    else
        >&2 echo "Error: file '${1}' is not a valid Docker Compose config"
        return 1
    fi
}

docker_dev_build_stack_images()
{
    # 1 - compose file
    # 2 - stack name
    # @:3 - other optional args for docker-compose when it performs the build step
    if [ ! -e "${1:?}" ]; then
        >&2 echo "Error: cannot build ${2:?} stack images - compose file ${1} does not exist"
        return 1
    # This checks that the config is valid
    elif docker-compose -f "${1}" config > /dev/null 2>&1; then
        echo "Building container images for stack ${2} from config ${1}"
        docker-compose -f "${1}" build ${@:3}
        return $?
    else
        >&2 echo "Error: invalid stack config ${1}"
        docker-compose -f "${1}" config
        return 1
    fi
}

# Work-around to use the .env file loading for compose files when deploying with docker stack (which doesn't by itself)
# See: https://github.com/moby/moby/issues/29133
# arg 1 - the base config file
# arg 2 - the stack name
docker_dev_deploy_stack_from_compose_using_env()
{
    # Uses helper plugin referenced in https://github.com/NOAA-OWP/DMOD/issues/133

    # Start by ensuring the required plugin is installed
    docker deployx > /dev/null 2>&1
    _R="${?}"
    if [ ${_R} -ne 0 ]; then
        >&2 echo "Error: attempting to start Docker stack without required 'deployx' plugin installed"
        exit 1
    fi
    # Then, as before, make sure we have a valid compose config file, and if so, start the stack
    if docker-compose -f "${1:?}" config > /dev/null 2>&1; then
        docker deployx --compose-file "${1}" "${2}"
        return $?
    # If we don't have a good config, then, again, exit in error
    else
        >&2 echo "Error: invalid docker-compose file '${1}'; cannot start stack; exiting"
        exit 1
    fi
}

# Useful for, e.g., seeing of the OS value is "Docker Desktop" to indicate this a local dev environment
docker_check_daemon_os()
{
    docker info --format "{{.OperatingSystem}}"
}

docker_dev_check_stack_running()
{
    if [ ${#} -ne 1 ]; then
        >&2 echo "Error: invalid args to docker_dev_check_stack_running() function"
        exit 1
    fi

    # For any stack with the expected name as a substring ...
    for s in $(docker stack ls --format "{{.Name}}" | grep "${1}"); do
        # If we find a matching stack name that is an exact match ...
        if [ "${s}" = "${1}" ]; then
            echo "true"
            return 0
        fi
    done
    # Otherwise ...
    echo "false"
    return 1
}

# Remove the stack with the specified name, if it is running
docker_dev_remove_stack()
{
    if [ ${#} -ne 1 ]; then
        >&2 echo "Error: invalid args to docker_dev_remove_stack() function"
        exit 1
    fi

    if [ "$(docker_dev_check_stack_running "${1}")" = "true" ]; then
        echo "Stopping Docker stack ${1}"
        docker stack rm "${1}"
    else
        echo "Docker stack ${1} not currently running"
    fi
}