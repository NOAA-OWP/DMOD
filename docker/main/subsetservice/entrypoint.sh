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
python3 -m ${SERVICE_PACKAGE_NAME:?} ${args}