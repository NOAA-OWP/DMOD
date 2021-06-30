#!/usr/bin/env sh

docker_dev_init_swarm_network()
{
    # 1 - network name
    # 2 - subnet
    # 3 - gateway
    # 4 - VXLAN ID (optional)

    # Sanity check args
    if [[ ${#} -lt 3 ]]; then
        >&2 echo "Error: cannot init swarm network without name, subnet, and gateway args"
        return 1
    # This also checks to make sure last arg is a number (e.g., gateway was omitted, but VXLAN ID was supplied)
    elif [ ${3} -eq ${3} ] 2>/dev/null; then
        >&2 echo "Error: gateway arg (${3}) looks like integer (VXLAN ID); check that no args were omitted"
        return 1
    fi

    local _VXLAN_ARGS=""

    if [[ ${#} -eq 4 ]]; then
        if ! [ ${4} -eq ${4} ] 2>/dev/null; then
            >&2 echo "Error: invalid VXLAN ID arg"
            return 1
        fi
        _VXLAN_ARGS="-o \"{\\\"com.docker.network.driver.overlay.vxlanid_list\\\": \\\"${4}\\\"}\""
    fi

    if [[ $(docker network ls --filter name=${1} -q | wc -l) -eq 0 ]]; then
        if [[ ${#} -eq 4 ]]; then
            docker network create \
                        --driver overlay \
                        --scope swarm \
                        --attachable \
                        --opt "{\"com.docker.network.driver.overlay.vxlanid_list\": \"${4}\"}" \
                        --subnet ${2} \
                        --gateway ${3} \
                        ${1}
        else
            docker network create -d overlay --scope swarm --attachable --subnet ${2} --gateway ${3} ${1}
        fi
        #echo "docker network create -d overlay --scope swarm --attachable ${_VXLAN_ARGS} --subnet ${2} --gateway ${3} ${1}"
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
# arg 3 - some unique identifier (e.g., a user name) to add to the file name to avoid collisions
docker_dev_deploy_stack_from_compose_using_env()
{
    if docker-compose -f "${1:?}" config > /dev/null 2>&1; then
        docker-compose -f "${1}" config > "/tmp/${3:?}_${2:?}_docker_compose_var_sub.yml" 2>/dev/null
        docker stack deploy --compose-file "/tmp/${3}_${2}_docker_compose_var_sub.yml" "${2}"
        return $?
    else
        echo "Error: invalid docker-compose file '${1}'; cannot start stack; exiting"
        exit 1
    fi
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