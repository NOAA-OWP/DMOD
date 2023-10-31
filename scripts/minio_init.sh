#!/bin/bash

INFO='Perform setup tasks for the DMOD MinIO Object Store'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

SHARED_FUNCS_DIR="${SCRIPT_PARENT_DIR}/shared"

# Import shared default script startup source
. ${SHARED_FUNCS_DIR}/default_script_setup.sh

if [ -e "${PROJECT_ROOT}/.env" ]; then
    . "${PROJECT_ROOT}/.env"
fi

DEFAULT_MC_COMMAND_1="minio-client"
DEFAULT_MC_COMMAND_2="mc"
DEFAULT_ALIAS="dmod"
DEFAULT_ADMIN_ALIAS="dmodadmin"
DEFAULT_GROUP="dataset_users"
DEFAULT_URL="http://127.0.0.1:${DMOD_OBJECT_STORE_1_HOST_PORT:-9000}"

USER_NAME_SECRET_FILE="${PROJECT_ROOT}/docker/secrets/object_store/model_exec_access_key"
USER_PASS_SECRET_FILE="${PROJECT_ROOT}/docker/secrets/object_store/model_exec_secret_key"
MINIO_ROOT_PASSWORD_FILE="${PROJECT_ROOT}/docker/secrets/object_store/secret_key"
MINIO_ROOT_USER_FILE="${PROJECT_ROOT}/docker/secrets/object_store/access_key"

check_alias_exists()
{
    # $1 - alias name
    ${MC_COMMAND:?} alias ls ${1:?No alias set when verifying alias exists} > /dev/null 2>&1;
}

create_alias()
{
    # $1 - alias name
    # $2 - connection URL
    # $3 - connection user
    # $4 - connection password

    ${MC_COMMAND:?} --insecure alias set \
        ${1:?No alias name set when creating alias} \
        ${2:?No connection url set when creating alias} \
        ${3:?No user name set when creating alias ${1}} \
        ${4:?No user passwd set when creating alias ${1}}
}

prep_connection_alias()
{
    # Check whether flag was set to indicate the alias has already been created (and doesn't need to be reset)
    if [ -n "${ALIAS_EXISTS:-}" ] && [ -z "${RESET_CONN:-}" ]; then
        # In such cases, make sure the connection alias does actually exist
        if check_alias_exists ${ALIAS:?No connection alias name set when checking for existence}; then
            echo "INFO: Using existing connection alias ${ALIAS}"
        else
            echo "ERROR: option set to expect existing connection alias ${ALIAS}, but it was not found; exiting." 1>&2
            exit 1
        fi
    else
        # If appropriate, remove an existing connection alias
        if [ -n "${RESET_CONN:-}" ]; then
            if check_alias_exists ${ALIAS:?No alias name set when trying to reset}; then
                echo "Removing existing alias ${ALIAS}"
                ${MC_COMMAND:?} alias rm ${ALIAS}
            else
                echo "WARN: option set to reset connection alias ${ALIAS}, but it did not already exist"
            fi
        fi
        create_alias ${ALIAS} ${CONNECTION_URL} ${USER_NAME} ${USER_SECRET}
    fi
}

prep_admin_alias()
{
    # If not set to create the admin alias, then just verify it exists
    if [ -z "${CREATE_ADMIN_ALIAS:-}" ]; then
        if check_alias_exists ${ADMIN_ALIAS:?No admin alias name set when checking for existence}; then
            echo "INFO: Using existing admin alias ${ADMIN_ALIAS} for setup"
        else
            echo "ERROR: expected client admin alias ${ADMIN_ALIAS} does not exist." 1>&2
            exit 1
        fi
    # If set to create (or re-create) the admin alias, then do so
    else
        # The option to create the admin alias implies an existing one should first be removed
        if check_alias_exists ${ADMIN_ALIAS:?No admin alias name set when trying to create}; then
            echo "INFO: Removing existing admin alias ${ADMIN_ALIAS}"
            ${MC_COMMAND:?} alias rm ${ADMIN_ALIAS:?}
        fi
        # Once we are sure there is no previously existing (still), create the admin alias
        echo "INFO: Creating admin alias ${ADMIN_ALIAS} over connection ${CONNECTION_URL}"
        create_alias ${ADMIN_ALIAS} ${CONNECTION_URL} ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}
        echo "INFO: Admin alias ${ADMIN_ALIAS} created"
    fi
}

create_user()
{
    ${MC_COMMAND:?} admin user add \
        ${ADMIN_ALIAS:?No admin alias set when adding USER} \
        ${USER_NAME:?No user name given when adding USER} \
        ${USER_SECRET:?No user secret given when adding USER}
}

create_group()
{
    # Create group and add user to it assumes group doesn't exist
    ${MC_COMMAND:?} admin group add ${ADMIN_ALIAS:?} ${GROUP_NAME:?} ${USER_NAME:?}

    # Add the necessary policy for the group
    ${MC_COMMAND} admin policy set ${ADMIN_ALIAS} ${READ_WRITE_POLICY:-readwrite} group=${GROUP_NAME}
}

initial_setup()
{
    prep_admin_alias
    prep_connection_alias

    # TODO: add logic/options for conditional processing if things exist already
    create_user
    create_group

}

print_info()
{
    echo "URL:          ${CONNECTION_URL:?}"
    echo "Admin Alias:  ${ADMIN_ALIAS}"
    echo "Admin User:   ${MINIO_ROOT_USER}"
    echo "Access Alias: ${ALIAS}"
    echo "Access User:  ${USER_NAME}"
    echo "Group:        ${GROUP_NAME}"
}

usage()
{
    # For usage, try to use the right default, but fall back to the last guess for the message
    if which ${DEFAULT_MC_COMMAND_1:?} > /dev/null 2>&1; then
        MC_COMMAND=${DEFAULT_MC_COMMAND_1:?}
    else
        MC_COMMAND=${DEFAULT_MC_COMMAND_2:?}
    fi

    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} [options]

Options:
    --admin-alias|-A <name> Specify the admin connection alias for the 'mc' CLI
                            (default: ${DEFAULT_ADMIN_ALIAS}).

    --alias|-a <name>       Specify the connection alias name for the 'mc' CLI
                            (default: ${DEFAULT_ALIAS}).

    --mc-command|-c <path>  Specify path to minio client
                            (default ${MC_COMMAND:?Not attempting to guess default mc command for usage message}).

    --create-admin-alias    Set that the 'mc' CLI admin alias must be created,
                            or removed and recreated if it already exists.

    --alias-exists|-x       Specify that the 'mc' CLI alias already exists (not
                            expected by default) and doesn't need to be created.

    --info                  Do no setup actions; only print the settings that
                            would be used for setup.

    --reset-alias           Remove existing 'mc' CLI alias before performing
                            typical setup.

    --url|-u <name>         Specify connection URL (default: ${DEFAULT_URL})
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
        --admin-alias|-A)
            ADMIN_ALIAS="${2}"
            shift
            ;;
        --alias|-a)
            ALIAS="${2}"
            shift
            ;;
        --alias-exists|-x)
            ALIAS_EXISTS='true'
            ;;
        --mc-command|-c)
            MC_COMMAND=${2:?}
            shift
            ;;
        --create-admin-alias)
            CREATE_ADMIN_ALIAS='true'
            ;;
        --url|-u)
            CONNECTION_URL="${2}"
            shift
            ;;
        --info)
            PRINT_INFO="true"
            ;;
        --reset-alias)
            RESET_CONN="true"
            ;;
        *)
            usage
            exit 1
            ;;
    esac
    shift
done

# Sanity check util is set/install
if [ -z "${MC_COMMAND:-}" ]; then
    # Try our defaults
    if which ${DEFAULT_MC_COMMAND_1:?} > /dev/null 2>&1; then
        MC_COMMAND=${DEFAULT_MC_COMMAND_1:?}
    elif which ${DEFAULT_MC_COMMAND_2:?} > /dev/null 2>&1; then
        MC_COMMAND=${DEFAULT_MC_COMMAND_2:?}
    else
        echo "Error: default options for minio client command (${DEFAULT_MC_COMMAND_1}, ${DEFAULT_MC_COMMAND_2}) do not appear to be valid." 1>&2
    fi
fi
which ${MC_COMMAND:?} > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: given minio command line tool ${MC_COMMAND} not valid." 1>&2
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
if [ -z "${ADMIN_ALIAS:-}" ]; then
    ADMIN_ALIAS="${DEFAULT_ADMIN_ALIAS}"
fi
# Set the default for URL, but only if it isn't set AND at least one of the aliases is not expected to exist
# (Better to have a failure happen otherwise, as we shouldn't expect to NEED it EXCEPT to create an alias)
if [ -z "${CONNECTION_URL:-}" ]; then
    if [ -z "${ALIAS_EXISTS:-}" ] || [ -n "${CREATE_ADMIN_ALIAS:-}" ]; then
        CONNECTION_URL="${DEFAULT_URL}"
    fi
fi
if [ -z "${GROUP_NAME:-}" ]; then
    GROUP_NAME="${DEFAULT_GROUP}"
fi

if [ -n "${PRINT_INFO:-}" ]; then
    print_info
else
    initial_setup
fi
