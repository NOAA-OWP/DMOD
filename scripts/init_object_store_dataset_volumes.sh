#!/usr/bin/env bash

INFO='Initialize associated named volume on current node for one or more object store datasets.'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

SHARED_FUNCS_DIR="${SCRIPT_PARENT_DIR}/shared"

# Import shared default script startup source
. ${SHARED_FUNCS_DIR}/default_script_setup.sh

# Import shared functions used for Docker-dev-related scripts
. ${SHARED_FUNCS_DIR}/docker_dev_func.sh

if [ -e "${PROJECT_ROOT}/.env" ]; then
    . "${PROJECT_ROOT}/.env"
fi

# TODO: eventually, these (and perhaps options for the keys explicitly) should be parameterized

S3FS_ACCESS_KEY_FILE="/run/secrets/model_exec_access_key"
if [ ! -e ${S3FS_ACCESS_KEY_FILE} ]; then
    S3FS_ACCESS_KEY_FILE="${PROJECT_ROOT}/docker/secrets/object_store/model_exec_access_key"
fi

S3FS_SECRET_KEY_FILE="/run/secrets/model_exec_secret_key"
if [ ! -e ${S3FS_SECRET_KEY_FILE} ]; then
    S3FS_SECRET_KEY_FILE="${PROJECT_ROOT}/docker/secrets/object_store/model_exec_secret_key"
fi

if [ -z "${S3FS_ACCESS_KEY:-}" ]; then
    if [ ! -e ${S3FS_ACCESS_KEY_FILE} ]; then
        echo "S3FS access key file '${S3FS_ACCESS_KEY_FILE}' not found"
        exit 1
    else
        echo "Reading S3FS access key file from secrets file '${S3FS_ACCESS_KEY_FILE}'"
        S3FS_ACCESS_KEY="$(cat ${S3FS_ACCESS_KEY_FILE})"
    fi
fi

if [ -z "${S3FS_SECRET_KEY:-}" ]; then
    if [ ! -e ${S3FS_SECRET_KEY_FILE:?Cannot read secret key from file: no secret key file set} ]; then
        echo "S3FS secret key file '${S3FS_SECRET_KEY_FILE}' not found"
        exit 1
    else
        echo "Reading S3FS secret key file from secrets file '${S3FS_SECRET_KEY_FILE}'"
        S3FS_SECRET_KEY="$(cat ${S3FS_SECRET_KEY_FILE})"
    fi
fi

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|--help
    ${NAME:?} [opts] [[<dataset>]*]

Options:
    --alias|-a <name>           Set alias name for storage driver plugin
                                (otherwise, use PLUGIN_ALIAS in environment)
    --no-create-volumes|-P      Do not create volumes; just perform the tasks
                                applicable to the storage driver plugin
    --remove|-r                 Remove volumes instead of adding them
    --remove-all|-R             Remove all previous volumes with this storage
                                driver
    --remove-plugin             Remove the storage driver plugin itself (implies
                                --remove-all)
    --re-init|-I                Re-initialize storage driver plugin if it exists
                                (implies --remove-plugin)
    --sentinel|-S <basename>    Create sentinel file under /tmp upon completion
    --service-mode              Run in service mode (keep process alive after;
                                completion; requires --sentinel)
    --url <obj_store_url>       Set the URL for the object store connection
                                (otherwise, use S3FS_URL in environment)
"
        echo "${_O}" 2>&1
}

remove_plugin()
{
    if docker_dev_check_for_s3fs_volume_plugin ${PLUGIN_ALIAS:?}; then
        docker plugin disable ${PLUGIN_ALIAS:?} && docker plugin rm ${PLUGIN_ALIAS}
    fi
}

add_plugin()
{
    if [ -n "${DO_RE_INIT_PLUGIN:-}" ]; then
        remove_plugin
    fi
    if ! docker_dev_check_for_s3fs_volume_plugin ${PLUGIN_ALIAS:?}; then
        echo "Initializing Docker plugin '${PLUGIN_ALIAS}' for s3fs access to ${S3FS_URL:?}"
        docker_dev_init_s3fs_volume_plugin ${S3FS_ACCESS_KEY:?} ${S3FS_SECRET_KEY:?} ${S3FS_URL:?} ${PLUGIN_ALIAS}
    fi
}

add_volumes()
{
    if [ ${#} -le 0 ]; then
        >&2 echo "Error: no dataset names provided"
        usage
        exit 1
    elif [ ${1} == '-h' ] || [ ${1} == '--help' ]; then
        usage
        exit
    fi

    add_plugin

    for i in ${@}; do
        if docker_dev_check_volume_exists ${i}; then
            echo "Not recreating existing volume '${i}'."
        else
            docker volume create -d ${PLUGIN_ALIAS} ${i}
            # TODO: modify to include options for permissions
        fi
    done
}

remove_volumes()
{
    docker volume rm ${@}
}

remove_all_volumes()
{
    docker volume rm $(docker volume ls -q --filter driver=${PLUGIN_ALIAS:?}:latest)
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        --alias|-a)
            PLUGIN_ALIAS="${2:?}"
            shift
            ;;
        --no-create-volumes|-P)
            NO_CREATE_VOLUMES='true'
            ;;
        --remove|-r)
            if [ -n "${DO_RE_INIT_PLUGIN:-}" ]; then
                >&2 echo "Error: cannot combine --remove and --re-init"
                usage
                exit 1
            fi
            DO_REMOVAL='true'
            ;;
        --remove-all|-R)
            DO_REMOVE_ALL='true'
            ;;
        --remove-plugin)
            DO_REMOVE_PLUGIN='true'
            DO_REMOVE_ALL='true'
            ;;
        --re-init|-I)
            if [ -n "${DO_REMOVAL:-}" ]; then
                >&2 echo "Error: cannot combine --remove and --re-init"
                usage
                exit 1
            fi
            DO_RE_INIT_PLUGIN='true'
            DO_REMOVE_PLUGIN='true'
            DO_REMOVE_ALL='true'
            ;;
        --sentinel|-S)
            SENTINEL="${2:?}"
            shift
            ;;
        --service-mode)
            SERVICE_MODE='true'
            ;;
        --url)
            S3FS_URL="${2:?}"
            shift
            ;;
        *)
            break
            ;;
    esac
    shift
done

# Use this as a default
if [ -z "${S3FS_URL:-}" ]; then
    S3FS_URL="http://$(hostname):9000/"
fi

# Sanity checks

# Shouldn't have trailing dataset name args if set to remove all (unless re-init)
if [ -n "${DO_REMOVE_ALL:-}" ] && [ -z "${DO_RE_INIT_PLUGIN:-}" ] && [ ${#} -gt 0 ]; then
    usage
    exit 1
fi

# While removing all
if [ -n "${DO_REMOVE_ALL:-}" ] && [ -n "${DO_REMOVE:-}" ]; then
    >&2 echo "Error: cannot combine --remove and --remove-all"
    usage
    exit 1
fi

# Service mode implies sentinel, so ensure this is set
if [ -n "${SERVICE_MODE:-}" ]; then
    if [ -z "${SENTINEL:-}" ]; then
        >&2 echo "Error: cannot run in service mode without also providing sentinel"
        usage
        exit 1
    fi
fi

if [ -n "${DO_REMOVE_ALL:-}" ]; then
    remove_all_volumes
fi

if [ -n "${DO_REMOVE_PLUGIN:-}" ]; then
    remove_plugin
fi

if [ -n "${DO_REMOVAL:-}" ]; then
    remove_volumes ${@}
elif [ -n "${NO_CREATE_VOLUMES:-}" ]; then
        add_plugin
elif [ ${#} -gt 0 ]; then
    # Note that add_volumes calls 'add_plugin' (but only if there are volume names to be added)
    add_volumes ${@}
fi

if [ -n "${SENTINEL:-}" ]; then
    echo "Volume init complete" > ${SENTINEL}
    if [ -n "${SERVICE_MODE:-}" ]; then
        while true; do
            sleep 300
        done
    fi
fi
