#!/bin/sh

#set -e

# A virtual environment path may be supplied using this environmental shell variable
if [ -n "${VENV_DIR:-}" ]; then
    # Initialize if virtual environment directory either doesn't exists, or exists but is empty ...
    if [ ! -d "${VENV_DIR}" ] || [ $(find "${VENV_DIR}" -maxdepth 0 -empty 2>/dev/null | wc -l) -eq 1 ]; then
        python3 -m venv "${VENV_DIR}"
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

# If we find this directory, and if there are wheels in it, then install those
if [ -d ${UPDATED_PACKAGES_DIR:=/updated_packages} ]; then
    if [ $(ls ${UPDATED_PACKAGES_DIR}/*.whl | wc -l) -gt 0 ]; then
        for srv in $(pip -qq freeze | grep dmod | awk -F= '{print $1}' | awk -F- '{print $2}'); do
            if [ $(ls ${UPDATED_PACKAGES_DIR} | grep dmod.${srv}- | wc -l) -eq 1 ]; then
                pip uninstall -y --no-input $(pip -qq freeze | grep dmod.${srv} | awk -F= '{print $1}')
                pip install $(ls ${UPDATED_PACKAGES_DIR}/*.whl | grep dmod.${srv}-)
            fi
        done
        #pip install ${UPDATED_PACKAGES_DIR}/*.whl
    fi
fi

args=""
if [ -n "${LISTEN_PORT:-}" ]; then
  args="${args} --port ${LISTEN_PORT}"
fi
if [ -n "${CATCHMENT_DATA_FILE:-}" ]; then
  args="${args} --catchment-data-file ${CATCHMENT_DATA_FILE}"
fi
if [ -n "${NEXUS_DATA_FILE:-}" ]; then
  args="${args} --nexus-data-file ${NEXUS_DATA_FILE}"
fi
if [ -n "${CROSSWALK_FILE:-}" ]; then
  args="${args} --crosswalk-file ${CROSSWALK_FILE}"
fi
if [ -n "${FILES_DIRECTORY:-}" ]; then
  args="${args} --files-directory ${FILES_DIRECTORY}"
fi

#set +e
#export PYTHONASYNCIODEBUG=1
python3 -m ${SERVICE_PACKAGE_NAME:?} ${_DEBUG_ARG:-} ${args}
