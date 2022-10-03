#!/bin/sh

# A virtual environment path may be supplied using this environmental shell variable
if [ -n "${VENV_DIR:-}" ]; then
    # Initialize if virtual environment directory either doesn't exists, or exists but is empty ...
    if [ ! -d "${VENV_DIR}" ] || [ $(find "${VENV_DIR}" -maxdepth 0 -empty 2>/dev/null | wc -l) -eq 1 ]; then
        python -m venv "${VENV_DIR}"
    fi
    . "${VENV_DIR}/bin/activate"
    pip install --update -r /code/requirements.txt
fi

# Install for debugging when appropriate
if [ "$(echo "${PYCHARM_REMOTE_DEBUG_ACTIVE:-false}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')" = "true" ]; then
    _DEBUG_ARG="--pycharm-remote-debug"
fi

# Handle some things in any cases when there is debugging
if [ -n "${_DEBUG_ARG:-}" ]; then
    # Append these as well if appropriate, though defaults are coded (and they are somewhat agnostic to the debug setup)
    if [ -n "${PYCHARM_REMOTE_DEBUG_SERVER_HOST:-}" ]; then
        _DEBUG_ARG="${_DEBUG_ARG:-} --remote-debug-host ${PYCHARM_REMOTE_DEBUG_SERVER_HOST}"
    fi

    if [ -n "${PYCHARM_REMOTE_DEBUG_SERVER_PORT:-}" ]; then
        _DEBUG_ARG="${_DEBUG_ARG:-} --remote-debug-port ${PYCHARM_REMOTE_DEBUG_SERVER_PORT}"
    fi
fi

_OBJ_STORE_ARGS=""
if [ "${USE_OBJ_STORE:-true}" == "true" ]; then
    _OBJ_STORE_ARGS="--object-store-user-secret-name ${USER_SECRET_NAME:?} --object-store-passwd-secret-name ${PASSWD_SECRET_NAME:?}"
    _OBJ_STORE_ARGS="${_OBJ_STORE_ARGS} --object-store-host ${OBJECT_STORE_HOST:-minio-proxy}"
    _OBJ_STORE_ARGS="${_OBJ_STORE_ARGS} --object-store-port ${OBJECT_STORE_PORT:-9000}"
else
    _OBJ_STORE_ARGS="--no-object-store"
fi

_REDIS_ARGS=""
# Get the Redis host if provided
if [ -n "${REDIS_HOST:-}" ]; then
    _REDIS_ARGS="${_REDIS_ARGS} --redis-host ${REDIS_HOST}"
fi
# Get the Redis port if provided
if [ -n "${REDIS_PORT:-}" ]; then
    _REDIS_ARGS="${_REDIS_ARGS} --redis-port ${REDIS_PORT}"
fi
# Potentially get either the Docker secret for the Redis password or the Redis password itself, but not both
if [ -n "${DOCKER_SECRET_REDIS_PASS:-}" ]; then
    _REDIS_ARGS="${_REDIS_ARGS} --redis-pass-secret-name ${DOCKER_SECRET_REDIS_PASS}"
elif [ -n "${REDIS_PASS:-}" ]; then
    _REDIS_ARGS="${_REDIS_ARGS} --redis-pass ${REDIS_PASS}"
fi
# Also potentially get a directory for filesystem-backed dataset configs
if [ -n "${DMOD_FILESYSTEM_DATASET_CONFIG_DIR:-}" ]; then
    _FILESYSTEM_DATASET_ARGS="--file-dataset-config-dir ${DMOD_FILESYSTEM_DATASET_CONFIG_DIR}"
fi

# If we find this directory, and if there are wheels in it, then install those
if [ -d ${UPDATED_PACKAGES_DIR:=/updated_packages} ]; then
    if [ $(ls ${UPDATED_PACKAGES_DIR}/*.whl | wc -l) -gt 0 ]; then
        for srv in $(pip -qq freeze | grep dmod | awk -F= '{print $1}' | awk -F- '{print $2}'); do
            if [ $(ls ${UPDATED_PACKAGES_DIR} | grep dmod.${srv}- | wc -l) -eq 1 ]; then
                pip uninstall -y --no-input $(pip -qq freeze | grep dmod.${srv} | awk -F= '{print $1}')
                pip install --no-deps $(ls ${UPDATED_PACKAGES_DIR}/*.whl | grep dmod.${srv}-)
            fi
        done
        #pip install ${UPDATED_PACKAGES_DIR}/*.whl
    fi
fi

python -m ${SERVICE_PACKAGE_NAME:?} \
    --port ${LISTEN_PORT:?} \
    --ssl-dir ${SERVICE_SSL_DIR:?} \
    ${_DEBUG_ARG:-} \
    ${_OBJ_STORE_ARGS} \
    ${_FILESYSTEM_DATASET_ARGS:-} \
    ${_REDIS_ARGS}
