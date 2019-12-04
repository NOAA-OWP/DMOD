#!/usr/bin/env bash

NAME=$(basename ${0})
DEFAULT_SLEEP_TIME=5
SERVICES_DOWN_COUNT=0

[[ -e .env ]] && source .env

usage()
{
    local _O="Usage:
    ${NAME} [--nwm-version <version>] [-s|--sleep [sleep_time]]
Options:
    --nwm-version   Set a particular NWM version, which effects used stack name
                    Default: master

    -s,--sleep      Set an amount of time to sleep after taking down the stack,
                    if there were any services running in the stack (max: 19 secs)
                    Default: ${DEFAULT_SLEEP_TIME} secs
"
    echo "${_O}" 2>&1
}

down_stack()
{
    local _STACK="${1}"
    local _COUNT=''
    _COUNT=$(docker stack services ${_STACK} 2>/dev/null | wc -l)
    SERVICES_DOWN_COUNT=$((${SERVICES_DOWN_COUNT}+${_COUNT}))
    docker stack rm ${_STACK}
}

while [[ ${#} -gt 0 ]]; do
    case "${1}" in
        --nwm-version)
            NWM_VER="${2}"
            shift
            ;;
        -s|--sleep)
            [[ -n "${SLEEP_TIME:-}" ]] && usage && exit 1
            if [[ ${2} =~ ^[0-9]+$ ]]; then
                SLEEP_TIME="${2}"
                shift
            else
                SLEEP_TIME=${DEFAULT_SLEEP_TIME}
            fi
            ;;
        *)
            echo "Error: invalid args"
            usage
            exit 1
            ;;
    esac
    shift
done

if [[ -z "${SLEEP_TIME:-}" ]]; then
    SLEEP_TIME=${DEFAULT_SLEEP_TIME}
elif [[ ! ${SLEEP_TIME} =~ ^[0-1]?[0-9]$ ]]; then
    echo "Warning: sleep time of ${SLEEP_TIME} is out of allowed range; using default"
    SLEEP_TIME=${DEFAULT_SLEEP_TIME}
fi

#docker stack rm ${DOCKER_INTERNAL_REGISTRY_STACK_NAME:-dev_registry_stack}
#docker stack rm nwm-${NWM_VER:-master}
#docker rmi 127.0.0.1:5000/nwm-master 127.0.0.1:5000/nwm-deps 127.0.0.1:5000/nwm-base 127.0.0.1:5000/mpi-scheduler

down_stack nwm-${NWM_VER:-master}
if [[ ${SERVICES_DOWN_COUNT} -gt 0 ]]; then
    sleep ${SLEEP_TIME}
fi