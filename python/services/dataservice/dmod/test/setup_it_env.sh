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

    # Start object-store stack
    if [ -e .bring_down_obj_store ]; then rm .bring_down_obj_store; fi
    if [ $(./scripts/control_stack.sh object-store check) = 'false' ]; then
        touch .bring_down_obj_store
        ./scripts/control_stack.sh object-store deploy
    fi
}

do_teardown()
{
    # Shutdown (and cleanup) Docker container with Redis instance
    docker stop ${IT_REDIS_CONTAINER_NAME:?}

    # Stop object store stack, if we started it
    if [ -e .bring_down_obj_store ]; then
        rm .bring_down_obj_store
        if [ $(./scripts/control_stack.sh object-store check) != 'false' ]; then
            ./scripts/control_stack.sh object-store stop
        fi
    fi
}
