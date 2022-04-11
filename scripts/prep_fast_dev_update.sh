#!/usr/bin/env bash

INFO='Facilitate development by preparing updated packages in a dev Docker volume.'
SCRIPT_PARENT_DIR="$(cd "$(dirname "${0}")"; pwd)"

SHARED_FUNCS_DIR="${SCRIPT_PARENT_DIR}/shared"

# Import shared default script startup source
. ${SHARED_FUNCS_DIR}/default_script_setup.sh

if [ -e "${PROJECT_ROOT}/.env" ]; then
    . "${PROJECT_ROOT}/.env"
fi

# The name for the updated packages Docker volume
UPDATED_PACKAGES_VOLUME_NAME="updated_packages"
# Our stack control script, which also runs the image build process
CONTROL_SCRIPT="${PROJECT_ROOT}/scripts/control_stack.sh"
# The name of the Python packages management stack
PY_PACKAGES_STACK_NAME="py-sources"
# Main services stack name
PRIMARY_STACK_NAME="main"
# The name and tag of the last image/service, if just rebuilding that and not the prior deps image layers
LAST_SERVICE_NAME="py-sources"
HELPER_IMAGE="${DOCKER_INTERNAL_REGISTRY}/dmod-py-sources:latest"

usage()
{
    local _O="${NAME:?}:
${INFO:?}

Usage:
    ${NAME:?} -h|-help|--help
    ${NAME:?} [options]

Options:
    --force-removal|-R
        When removing a previously existing Docker volume, add the flags to
        the Docker command to force removal.

    --full-build|-B
        Do a full build of the ${LAST_SERVICE_NAME} service image with
        the Python DMOD packages, instead of an optimized build.

    --remove-volume-only|-O
        Just remove the Docker volume, if it exists.

    --create-empty|-E
        Create a new volume, but don't build updated DMOD Python packages and
        copy them into this volume.

    --safe|-S
        Exit in error if the primary '${PRIMARY_STACK_NAME}' stack is running,
        to make sure we don't try to delete an previously existing volume
        while its in use (conflicts with --deploy).

    --deploy|-D
        Go ahead and deploy the code to services, stopping and starting as
        needed (conflicts with --safe).
"

    echo "${_O}" 2>&1
}

clean_existing_volume()
{
    if docker volume inspect ${UPDATED_PACKAGES_VOLUME_NAME} > /dev/null 2>&1; then
        docker volume rm ${REMOVAL_ARG:-} ${UPDATED_PACKAGES_VOLUME_NAME} > /dev/null 2>&1 \
            && echo "INFO: removed previously existing volume '${UPDATED_PACKAGES_VOLUME_NAME}' successfully."
    else
        echo "INFO: no existing volume '${UPDATED_PACKAGES_VOLUME_NAME}' to remove."
    fi
}

while [ ${#} -gt 0 ]; do
    case "${1}" in
        -h|-help|--help)
            usage
            exit
            ;;
        --force-removal|-R)
            [ -n "${REMOVAL_ARG:-}" ] && usage && exit 1
            REMOVAL_ARG="--force"
            ;;
        --create-empty|-E)
            [ -n "${DO_CREATE_EMPTY:-}" ] && usage && exit 1
            DO_CREATE_EMPTY="true"
            ;;
        --full-build|-B)
            [ -n "${DO_FULL_BUILD:-}" ] && usage && exit 1
            DO_FULL_BUILD="true"
            ;;
        --remove-volume-only|-O)
            [ -n "${JUST_REMOVE_VOLUME:-}" ] && usage && exit 1
            JUST_REMOVE_VOLUME="true"
            ;;
        --deploy|-D)
            [ -n "${DO_DEPLOY:-}" ] && usage && exit 1
            [ -n "${RUN_SAFE:-}" ] && usage && exit 1
            DO_DEPLOY="true"
            ;;
        --safe|-S)
            [ -n "${DO_DEPLOY:-}" ] && usage && exit 1
            [ -n "${RUN_SAFE:-}" ] && usage && exit 1
            RUN_SAFE="true"
            ;;
        *)
            usage
            exit 1
            ;;
    esac
    shift
done

# Make sure nothing is running if it doesn't need to be, bailing or stopping it as appropriate
if [ -n "${RUN_SAFE:-}"]; then
    if ${CONTROL_SCRIPT} ${PRIMARY_STACK_NAME} check > /dev/null; then
        >&2 echo "Error: option for safe mode active and found primary '${PRIMARY_STACK_NAME}' stack running; exiting."
        exit 1
    fi
elif [ -n "${DO_DEPLOY:-}"]; then
    if ${CONTROL_SCRIPT} ${PRIMARY_STACK_NAME} check > /dev/null; then
        ${CONTROL_SCRIPT} ${PRIMARY_STACK_NAME} stop
    fi
fi

# Prepare a Docker volume for the dmod Python packages, removing any existing
if ! clean_existing_volume; then
     >&2 echo "Error: removal of existing Docker volume '${UPDATED_PACKAGES_VOLUME_NAME}' failed; exiting."
     exit 1
fi

if [ -n "${JUST_REMOVE_VOLUME:-}" ]; then
    exit
fi

if ! docker volume create ${UPDATED_PACKAGES_VOLUME_NAME} > /dev/null 2>&1; then
    >&2 echo "Error: Docker volume creation for '${UPDATED_PACKAGES_VOLUME_NAME}' failed; exiting."
    exit 1
fi

# Build updated py-sources image; if requested, build everything, but by default, just build the last image
if [ -n "${DO_FULL_BUILD:-}" ]; then
    ${CONTROL_SCRIPT} ${PY_PACKAGES_STACK_NAME} build
else
    ${CONTROL_SCRIPT} --build-args "${LAST_SERVICE_NAME}" ${PY_PACKAGES_STACK_NAME} build
fi

# Run a (cleaned-up) container from py-sources, with the volume mounted, and copy the dmod Python packages there
echo "INFO: copying updated Python DMOD packages to '${UPDATED_PACKAGES_VOLUME_NAME}' volume"
docker run --rm \
    --name fast_dev_updater \
    --entrypoint /bin/sh \
    --mount source=${UPDATED_PACKAGES_VOLUME_NAME},target=/updated_packages \
  ${HELPER_IMAGE} \
  -c "cp -a /DIST/dmod*.whl /updated_packages/."

if [ -n "${DO_DEPLOY:-}" ]; then
    ${CONTROL_SCRIPT} ${PRIMARY_STACK_NAME} start
fi
