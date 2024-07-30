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
    # Need Docker container with Redis instance
    it_redis_startup
}

do_teardown()
{
    # Shutdown (and cleanup) Docker container with Redis instance
    docker stop ${IT_REDIS_CONTAINER_NAME:?}
}
