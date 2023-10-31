#!/usr/bin/env bash

INFO='Create a scheduler resources config file.'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

SHARED_FUNCS_DIR="${SCRIPT_PARENT_DIR}/shared"

# Import shared default script startup source
. ${SHARED_FUNCS_DIR}/default_script_setup.sh

if [ -e "${PROJECT_ROOT}/.env" ]; then
    . "${PROJECT_ROOT}/.env"
fi

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} [params]

Required Params:
    --cpus|-c <N>       Available CPU resources
    --memory|-m <M>     Available memory resources
"
    echo "${_O}" 2>&1
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
        -h|-help|--help)
            usage
            exit
            ;;
        --cpus|-c)
            [ -n "${NUM_CPUS:-}" ] && usage && exit 1
            NUM_CPUS="${2:?No CPU count arg included}"
            shift
            ;;
        --memory|-m)
            [ -n "${MEM_AMOUNT:-}" ] && usage && exit 1
            MEM_AMOUNT="${2:?No memory amount arg included}"
            shift
            ;;
        *)
            usage
            exit 1
            ;;
    esac
    shift
done

if [ -e ${SCHEDULER_RESOURCE_DIR}/resources.yaml ]; then
    >&2 echo "Error: file '${SCHEDULER_RESOURCE_DIR}/resources.yaml' already exists!"
    exit 1
fi

cat << EOF > ${SCHEDULER_RESOURCE_DIR}/resources.yaml
"resources":
  -
    'node_id': "Node-001"
    'Hostname': "$(hostname)"
    'Availability': "active"
    'State': "ready"
    'CPUs': ${NUM_CPUS}
    'MemoryBytes': ${MEM_AMOUNT}
    'Total CPUs': ${NUM_CPUS}
    'Total Memory': ${MEM_AMOUNT}
EOF
