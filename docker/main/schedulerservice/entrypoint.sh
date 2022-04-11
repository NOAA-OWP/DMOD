#!/bin/sh
SECRET_FILE="/run/secrets/${DOCKER_SECRET_REDIS_PASS:?}"
REDIS_PASS="$(cat ${SECRET_FILE})"
#set -e

# A virtual environment path may be supplied using this environmental shell variable
if [ -n "${VENV_DIR:-}" ]; then
    # Initialize if virtual environment directory either doesn't exists, or exists but is empty ...
    if [ ! -d "${VENV_DIR}" ] || [ $(find "${VENV_DIR}" -maxdepth 0 -empty 2>/dev/null | wc -l) -eq 1 ]; then
        python -m venv "${VENV_DIR}"
    fi
    . "${VENV_DIR}/bin/activate"
    pip install --update -r /code/requirements.txt
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

#set +e

python -u -m ${SERVICE_PACKAGE_NAME:?} \
    --port ${LISTEN_PORT:?} \
    --ssl-dir ${SERVICE_SSL_DIR:?} \
    --redis-pass ${REDIS_PASS}
