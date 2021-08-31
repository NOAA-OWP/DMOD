#!/bin/sh

#set -e

_DEBUG_ARG=""

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
    pip install pydevd-pycharm${PYCHARM_REMOTE_DEBUG_VERSION}
    _DEBUG_ARG="--remote-debug --debug-host ${PYCHARM_REMOTE_DEBUG_SERVER_HOST:?} --debug-port ${PYCHARM_REMOTE_DEBUG_SERVER_PORT:?}"
fi

#set +e
#export PYTHONASYNCIODEBUG=1
python -m ${SERVICE_PACKAGE_NAME:?} \
    --port ${LISTEN_PORT:?} \
    --ssl-dir ${SERVICE_SSL_DIR:?} \
    --scheduler-host ${SCHEDULER_ENDPOINT_HOST:?} \
    --scheduler-port ${SCHEDULER_ENDPOINT_PORT:?} \
    --scheduler-ssl-dir ${SCHEDULER_CLIENT_SSL_DIR:?} \
    ${_DEBUG_ARG}
