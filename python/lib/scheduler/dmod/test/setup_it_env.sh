#!/usr/bin/env sh

it_redis_startup()
{
    docker run \
        --detach \
        --rm \
        --name ${IT_REDIS_CONTAINER_NAME:?} \
        -p 127.0.0.1:${IT_REDIS_CONTAINER_HOST_PORT:?}:6379/tcp \
        --entrypoint=redis-server \
        redis \
         --requirepass "${IT_REDIS_CONTAINER_PASS:?}"
}

do_setup()
{

    # Make sure the necessary Docker networks have been set up, as the tests will fail otherwise
    if [ -z "${DOCKER_MPI_NET_VXLAN_ID:-}" ]; then
        docker_dev_init_swarm_network ${DOCKER_MPI_NET_NAME:=mpi-net} \
                    ${DOCKER_MPI_NET_SUBNET:?Need to set MPI net subnet value for testing within .test_env} \
                    ${DOCKER_MPI_NET_GATEWAY:?Need to set MPI net gateway value for testing within .test_env} \
                    ${DOCKER_MPI_NET_DRIVER:-overlay}
    else
        docker_dev_init_swarm_network ${DOCKER_MPI_NET_NAME:=mpi-net} \
                ${DOCKER_MPI_NET_SUBNET:?Need to set MPI net subnet value for testing within .test_env} \
                ${DOCKER_MPI_NET_GATEWAY:?Need to set MPI net gateway value for testing within .test_env} \
                ${DOCKER_MPI_NET_DRIVER:=macvlan} \
                ${DOCKER_MPI_NET_VXLAN_ID}
    fi
    # Then the requests-net
    docker_dev_init_swarm_network ${DOCKER_REQUESTS_NET_NAME:=requests-net} \
            ${DOCKER_REQUESTS_NET_SUBNET:?Need to set requests net subnet value for testing within .test_env} \
            ${DOCKER_REQUESTS_NET_GATEWAY:?Need to set requests net gateway value for testing within .test_env} \
            ${DOCKER_REQUESTS_NET_DRIVER:-overlay}
    # Need Docker container with Redis instance
    it_redis_startup
}

do_teardown()
{
    # Shutdown (and cleanup) Docker container with Redis instance
    docker stop ${IT_REDIS_CONTAINER_NAME:?}
}