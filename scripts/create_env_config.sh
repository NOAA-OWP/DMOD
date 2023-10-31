#!/bin/bash

# TODO: provide args to optionally parameterize REPO_ROOT_DIR and OUTPUT_BASENAME
if [ ! -d ""${REPO_ROOT_DIR:=$(pwd)}"" ]; then
    >&2 echo "Expected DMOD repo root '${REPO_ROOT_DIR}' is not an existing directory!"
    exit 1
fi
OUTPUT_ENV="${REPO_ROOT_DIR}/${OUTPUT_BASENAME:-.env}"

# Sanity check that a config doesn't already exist
if [ -e "${OUTPUT_ENV}" ]; then
    >&2 echo "Error: environment config ${OUTPUT_ENV} already exists!"
    exit 1
fi

# TODO: provide args to optionally parameterize JOBS_CPU_COUNT (while still sanity checking against nproc)
if [ -z "${JOBS_CPU_COUNT:-}" ]; then
    _TOTAL_CPU=$(nproc)
    if [ ${_TOTAL_CPU} -lt 2 ]; then
        JOBS_CPU_COUNT=1
    elif [ ${_TOTAL_CPU} -lt 8 ]; then
        JOBS_CPU_COUNT=2
    else
        JOBS_CPU_COUNT=4
    fi
fi

cat example.env | \
    sed "s|##* *DMOD_SSL_DIR=.*|DMOD_SSL_DIR=${REPO_ROOT_DIR}/ssl/|" | \
    sed "s|##* *DMOD_OBJECT_STORE_MINIO_1_SSL_KEY=.*|DMOD_OBJECT_STORE_MINIO_1_SSL_KEY=${REPO_ROOT_DIR}/ssl/object_store/minio1/private.key|" | \
    sed "s|##* *DMOD_OBJECT_STORE_MINIO_1_SSL_CERT=.*|DMOD_OBJECT_STORE_MINIO_1_SSL_CERT=${REPO_ROOT_DIR}/ssl/object_store/minio1/public.crt|" | \
    sed "s|##* *DMOD_OBJECT_STORE_MINIO_2_SSL_KEY=.*|DMOD_OBJECT_STORE_MINIO_2_SSL_KEY=${REPO_ROOT_DIR}/ssl/object_store/minio2/private.key|" | \
    sed "s|##* *DMOD_OBJECT_STORE_MINIO_2_SSL_CERT=.*|DMOD_OBJECT_STORE_MINIO_2_SSL_CERT=${REPO_ROOT_DIR}/ssl/object_store/minio2/public.crt|" | \
    sed "s|##* *DMOD_OBJECT_STORE_MINIO_PROXY_SSL_KEY=.*|DMOD_OBJECT_STORE_MINIO_PROXY_SSL_KEY=${REPO_ROOT_DIR}/ssl/object_store/minio_proxy/private.key|" | \
    sed "s|##* *DMOD_OBJECT_STORE_MINIO_PROXY_SSL_CERT=.*|DMOD_OBJECT_STORE_MINIO_PROXY_SSL_CERT=${REPO_ROOT_DIR}/ssl/object_store/minio_proxy/public.crt|" | \
    sed "s|##* *DOCKER_HOST_IMAGE_STORE=.*|DOCKER_HOST_IMAGE_STORE=${REPO_ROOT_DIR}/docker_host_volumes/images|" | \
    sed "s|##* *DOCKER_VOL_DOMAINS=.*|DOCKER_VOL_DOMAINS=${REPO_ROOT_DIR}/docker_host_volumes/domains|" | \
    sed "s|##* *DOCKER_GUI_HOST_VENV_DIR=.*|DOCKER_GUI_HOST_VENV_DIR=${REPO_ROOT_DIR}/docker_host_volumes/virtual_envs/gui_venv|" | \
    sed "s|##* *DOCKER_INTERNAL_REGISTRY_STACK_CONFIG=.*|DOCKER_INTERNAL_REGISTRY_STACK_CONFIG=${REPO_ROOT_DIR}/docker/dev_registry_stack/docker-registry.yml|" | \
    sed "s|##* *DOCKER_GUI_WEB_SERVER_CONFIG_FILE=.*|DOCKER_GUI_WEB_SERVER_CONFIG_FILE=${REPO_ROOT_DIR}/docker/nwm_gui/web_server/nginx/default.conf|" | \
    sed "s|##* *REDIS_CONF_DIR=.*|REDIS_CONF_DIR=${REPO_ROOT_DIR}/docker/main/myredis|" | \
    sed "s|##* *DOCKER_REDIS_SECRET_FILE=.*|DOCKER_REDIS_SECRET_FILE=${REPO_ROOT_DIR}/docker/secrets/myredis_password.txt|" | \
    sed "s|##* *DMOD_OBJECT_STORE_ADMIN_USER_NAME_SECRET_FILE=.*|DMOD_OBJECT_STORE_ADMIN_USER_NAME_SECRET_FILE=${REPO_ROOT_DIR}/docker/secrets/object_store/access_key|" | \
    sed "s|##* *DMOD_OBJECT_STORE_ADMIN_USER_PASSWD_SECRET_FILE=.*|DMOD_OBJECT_STORE_ADMIN_USER_PASSWD_SECRET_FILE=${REPO_ROOT_DIR}/docker/secrets/object_store/secret_key|" | \
    sed "s|##* *DMOD_OBJECT_STORE_EXEC_USER_NAME_SECRET_FILE=.*|DMOD_OBJECT_STORE_EXEC_USER_NAME_SECRET_FILE=${REPO_ROOT_DIR}/docker/secrets/object_store/model_exec_access_key|" | \
    sed "s|##* *DMOD_OBJECT_STORE_EXEC_USER_PASSWD_SECRET_FILE=.*|DMOD_OBJECT_STORE_EXEC_USER_PASSWD_SECRET_FILE=${REPO_ROOT_DIR}/docker/secrets/object_store/model_exec_secret_key|" | \
    sed "s|##* *DOCKER_REDIS_SECRET_FILE=.*|DOCKER_REDIS_SECRET_FILE=${REPO_ROOT_DIR}/docker/secrets/myredis_password.txt|" | \
    sed "s|##* *DMOD_OBJECT_STORE_PROXY_TEMPLATES_DIR=.*|DMOD_OBJECT_STORE_PROXY_TEMPLATES_DIR=${REPO_ROOT_DIR}/docker/object_store/nginx_config_templates|" | \
    sed "s|##* *DMOD_OBJECT_STORE_PROXY_CONFIG=.*|DMOD_OBJECT_STORE_PROXY_CONFIG=${REPO_ROOT_DIR}/docker/object_store/nginx-docker-desktop.conf|" | \
    sed "s|##* *DMOD_APP_STATIC=.*|DMOD_APP_STATIC=${REPO_ROOT_DIR}/python/gui/static|" | \
    sed "s|##* *NGEN_BUILD_PARALLEL_JOBS=.*|NGEN_BUILD_PARALLEL_JOBS=${JOBS_CPU_COUNT?Missing jobs CPU count}|" | \
    sed "s|##* *SCHEDULER_RESOURCE_DIR=.*|SCHEDULER_RESOURCE_DIR=${REPO_ROOT_DIR}/data/scheduler_service|" | \
    sed "s|##* *DMOD_OBJECT_STORE_SINGLE_NODE_HOST_DIR=.*|DMOD_OBJECT_STORE_SINGLE_NODE_HOST_DIR=${REPO_ROOT_DIR}/docker_host_volumes/dmod_object_store|" > ${OUTPUT_ENV}


source ${OUTPUT_ENV}

if [ -z "${DOCKER_INTERNAL_REGISTRY_STACK_CONFIG:-}" ] || [ ! -f "${DOCKER_INTERNAL_REGISTRY_STACK_CONFIG}" ]; then
    >&2 echo "File ${OUTPUT_ENV} was not created correctly; removing"
    rm ${OUTPUT_ENV}
    exit 1
else
    echo "Created environment config at '${OUTPUT_ENV}'"
fi