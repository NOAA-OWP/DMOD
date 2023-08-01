#!/bin/sh

while [ ${#} -gt 0 ]; do
    case "${1}" in
        --hydrofabric-dataset|-y)
            HY_DATASET_NAME="${2}"
            shift
            ;;
        --partition-dataset|-p)
            PART_DATASET_NAME="${2}"
            shift
            ;;
        --num-partitions|-n)
            NUM_PARTITIONS="${2}"
            shift
            ;;
        --catchment-data-file|-c)
            CATCHMENT_DATA_FILE_NAME="${2}"
            shift
            ;;
        --nexus-data-file|-x)
            NEXUS_DATA_FILE_NAME="${2}"
            shift
            ;;
        --nexus-subset)
            NEX_SUBSET="${2}"
            shift
            ;;
        --catchment-subset)
            CAT_SUBSET="${2}"
            shift
            ;;
    esac
    shift
done

# Set some defaults
if [ -z "${CATCHMENT_DATA_FILE_NAME}" ]; then
    CATCHMENT_DATA_FILE_NAME="catchment_data.geojson"
fi
if [ -z "${NEXUS_DATA_FILE_NAME}" ]; then
    NEXUS_DATA_FILE_NAME="nexus_data.geojson"
fi

HYDROFABRIC_DIR="/hydrofabric_dataset"
PARTITION_DIR="/partitioning_dataset"

ACCESS_KEY_SECRET="object_store_exec_user_name"
SECRET_KEY_SECRET="object_store_exec_user_passwd"
DOCKER_SECRETS_DIR="/run/secrets"
ACCESS_KEY_FILE="${DOCKER_SECRETS_DIR}/${ACCESS_KEY_SECRET}"
SECRET_KEY_FILE="${DOCKER_SECRETS_DIR}/${SECRET_KEY_SECRET}"

PARTITION_OUTPUT_BASENAME="partition_config.json"

S3FS_PASSWD_FILE="${HOME}/.passwd-s3fs"

# args to ngen partition executable are (see also below where actually used):
#       catchment_data_file, nexus_data_file, output_file, num_partitions, nexus_subset, catchment_subset
# Should actually be set by ENV
#NGEN_PART_EXECUTABLE="partitionGenerator"

# Mount an object store dataset of the given name and data category (which implies mount point directory)
mount_object_store_dataset()
{
    _MOUNTED_DATASET_NAME="${1:?}"
    _MOUNT_DIR="${2:?}"
    # TODO (later): this is a non-S3 implementation URL; add support for S3 directly also
    # This is based on the nginx proxy config (hopefully)
    _URL="http://minio-proxy:9000/"
    s3fs ${_MOUNTED_DATASET_NAME} ${_MOUNT_DIR} -o passwd_file=${HOME}/.passwd-s3fs -o url=${_URL} -o use_path_request_style
}

# Read Docker Secrets files for Object Store access, if they exist
if [ -e "${ACCESS_KEY_FILE}" ]; then
    ACCESS_KEY="$(cat "${ACCESS_KEY_FILE}")"
fi
if [ -e "${SECRET_KEY_FILE}" ]; then
    SECRET_KEY="$(cat "${SECRET_KEY_FILE}")"
fi

# Bail if we don't have these; otherwise, config the auth file for s3fs
if [ -z "${ACCESS_KEY:-}" ]; then
    echo "Error: no ACCESS_KEY provided for Minio object store access" 2>&1
    exit 1
elif [ -z "${SECRET_KEY:-}" ]; then
    echo "Error: ACCESS_KEY provided for Minio object store access, but no SECRET_KEY provided" 2>&1
    exit 1
fi

# Configure auth for s3fs
echo ${ACCESS_KEY}:${SECRET_KEY} > "${S3FS_PASSWD_FILE}"
chmod 600 "${S3FS_PASSWD_FILE}"

# Mount the hydrofabric dataset
mount_object_store_dataset ${HY_DATASET_NAME:?} ${HYDROFABRIC_DIR}

# Mount the partitioning config output dataset
mount_object_store_dataset ${PART_DATASET_NAME:?} ${PARTITION_DIR}

# Run the partitioner
# Again, args are: catchment_data_file, nexus_data_file, output_file, num_partitions, nexus_subset, catchment_subset
${NGEN_PART_EXECUTABLE:?} \
    ${HYDROFABRIC_DIR}/${CATCHMENT_DATA_FILE_NAME} \
    ${HYDROFABRIC_DIR}/${NEXUS_DATA_FILE_NAME} \
    ${PARTITION_DIR}/${PARTITION_OUTPUT_BASENAME} \
    ${NUM_PARTITIONS:?} \
    ${NEX_SUBSET:-} \
    ${CAT_SUBSET:-}