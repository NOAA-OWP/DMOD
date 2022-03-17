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
if [ "$(echo "${PYCHARM_REMOTE_DEBUG_ACTIVE:-false}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')" == "true" ]; then
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
    _OBJ_STORE_ARGS="$--object-store-user-secret-name ${USER_SECRET_NAME:?} --object-store-passwd-secret-name ${PASSWD_SECRET_NAME:?}"
else
    _OBJ_STORE_ARGS="--no-object-store"
fi

python -m ${SERVICE_PACKAGE_NAME:?} \
    --port ${LISTEN_PORT:?} \
    --ssl-dir ${SERVICE_SSL_DIR:?} \
    ${_DEBUG_ARG:-} \
    ${_OBJ_STORE_ARGS}
