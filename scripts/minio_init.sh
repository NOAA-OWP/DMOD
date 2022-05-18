#!/bin/bash

INFO='Perform setup tasks for the DMOD MinIO Object Store'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

SHARED_FUNCS_DIR="${SCRIPT_PARENT_DIR}/shared"

# Import shared default script startup source
. ${SHARED_FUNCS_DIR}/default_script_setup.sh

if [ -e "${PROJECT_ROOT}/.env" ]; then
    . "${PROJECT_ROOT}/.env"
fi

MC_COMMAND="mc"
DEFAULT_ALIAS="dmod"
DEFAULT_GROUP="dataset_users"
DEFAULT_URL="http://localhost:${DMOD_OBJECT_STORE_1_HOST_PORT:-9000}"

USER_NAME_SECRET_FILE="${PROJECT_ROOT}/docker/secrets/object_store/model_exec_access_key"
USER_PASS_SECRET_FILE="${PROJECT_ROOT}/docker/secrets/object_store/model_exec_secret_key"
MINIO_ROOT_PASSWORD_FILE="${PROJECT_ROOT}/docker/secrets/object_store/secret_key"
MINIO_ROOT_USER_FILE="${PROJECT_ROOT}/docker/secrets/object_store/access_key"

check_alias_exists()
{
    ${MC_COMMAND} alias ls ${ALIAS:?No alias set when verifying alias exists} > /dev/null 2>&1;
}

create_alias()
{
    # Check whether flag was set to indicate the alias has already been created (and doesn't need to be reset)
    if [ -n "${ALIAS_EXISTS:-}" ] && [ -z "${RESET_CONN:-}" ]; then
        # Make sure it is there
        if check_alias_exists; then
            echo "Using existing alias ${ALIAS}"
        else
            echo "Error: option set to expect existing alias ${ALIAS}, but it was not found; exiting." 1>&2
            exit 1
        fi
    else
        # If appropriate, remove an existing connection alias
        if [ -n "${RESET_CONN:-}" ]; then
            if check_alias_exists; then
                echo "Removing existing alias ${ALIAS}"
                ${MC_COMMAND} alias rm ${ALIAS:?No alias set when creating alias}
            else
                echo "Warning: option set to reset alias ${ALIAS}, but it did not already exist"
            fi
        fi

        ${MC_COMMAND} alias set \
            ${ALIAS:?No alias set when creating alias} \
            ${CONNECTION_URL:?No connection url set when creating alias} \
            ${MINIO_ROOT_USER:?No admin user name set when creating alias} \
            ${MINIO_ROOT_PASSWORD:?No admin user passwd set when creating alias}
    fi
}

create_user()
{
    ${MC_COMMAND} admin user add \
        ${ALIAS:?No alias set when adding USER} \
        ${USER_NAME:?No user name given when adding USER} \
        ${USER_SECRET:?No user secret given when adding USER}
}

create_group()
{
    # Create group and add user to it assumes group doesn't exist
    ${MC_COMMAND} admin group add ${ALIAS:?} ${GROUP_NAME:?} ${USER_NAME:?}

    # Add the necessary policy for the group
    ${MC_COMMAND} admin policy set ${ALIAS} ${READ_WRITE_POLICY:-readwrite} group=${GROUP_NAME}
}

initial_setup()
{
    # TODO: add logic/options for conditional processing if things exist already
    create_alias
    create_user
    create_group

}

print_info()
{
    echo "Alias:        ${ALIAS}"
    echo "Admin User:   ${MINIO_ROOT_USER}"
    echo "URL:          ${CONNECTION_URL:?}"
    echo "User:         ${USER_NAME}"
    echo "Group:        ${GROUP_NAME}"
}

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} [--alias|-a <name>] [--url|-u <url>]

Options:
    --alias|-a <name>   Specify the connection alias name for the mc CLI (default: ${DEFAULT_ALIAS}).
    --alias-exists|-x   Specify that the alias should already exist and does not need to be created.
    --reset-connection  Remove existing connection before performing typical setup.
    --url|-u <name>     Specify connection URL (default: ${DEFAULT_URL})
"
    echo "${_O}" 2>&1
}

# TODO: function to change/remove+readd existing alias to account for new root user or password

while [ ${#} -gt 0 ]; do
    case "${1}" in
        -h|--help|-help)
            usage
            exit
            ;;
        --alias|-a)
            ALIAS="${2}"
            shift
            ;;
        --alias-exists|-x)
            ALIAS_EXISTS='true'
            ;;
        --url|-u)
            CONNECTION_URL="${2}"
            shift
            ;;
        --info)
            PRINT_INFO="true"
            ;;
        --reset-connection)
            RESET_CONN="true"
            ;;
        *)
            usage
            exit 1
            ;;
    esac
    shift
done

# Sanity check util is install
which ${MC_COMMAND} > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: minio command line tool not installed." 1>&2
    exit 1
fi
# Sanity check that these required files exist 
if [ ! -e "${USER_NAME_SECRET_FILE}" ]; then
    echo "Error: user name file ${USER_NAME_SECRET_FILE} does not exist." 1>&2
    exit 1
fi
if [ ! -e "${USER_PASS_SECRET_FILE}" ]; then
    echo "Error: user secret file ${USER_PASS_SECRET_FILE} does not exist." 1>&2
    exit 1
fi
if [ ! -e "${MINIO_ROOT_PASSWORD_FILE}" ]; then
    echo "Error: admin user secret file ${MINIO_ROOT_PASSWORD_FILE} does not exist." 1>&2
    exit 1
fi
if [ ! -e "${MINIO_ROOT_USER_FILE}" ]; then
    echo "Error: admin user name file ${MINIO_ROOT_USER_FILE} does not exist." 1>&2
    exit 1
fi

# Source (or effectively do so) various needed things
MINIO_ROOT_USER="$(cat ${MINIO_ROOT_USER_FILE})"
MINIO_ROOT_PASSWORD="$(cat ${MINIO_ROOT_PASSWORD_FILE})"
USER_NAME="$(cat ${USER_NAME_SECRET_FILE})"
USER_SECRET="$(cat ${USER_PASS_SECRET_FILE})"

# Also, set up these default if needed
if [ -z "${ALIAS:-}" ]; then
    ALIAS="${DEFAULT_ALIAS}"
fi
# Set the default for URL, but only if the alias is not expected to exist
# (Better to have a failure happen otherwise, as we shouldn't expect to NEED it except to create the alias)
if [ -z "${CONNECTION_URL:-}" ] && [ -z "${ALIAS_EXISTS:-}" ]; then
    CONNECTION_URL="${DEFAULT_URL}"
fi
if [ -z "${GROUP_NAME:-}" ]; then
    GROUP_NAME="${DEFAULT_GROUP}"
fi

if [ -n "${PRINT_INFO:-}" ]; then
    print_info
else
    initial_setup
fi
