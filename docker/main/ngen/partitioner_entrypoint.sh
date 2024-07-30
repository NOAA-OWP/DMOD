#!/bin/bash

while [ ${#} -gt 0 ]; do
    case "${1}" in
        --hydrofabric-dataset|-y)
            HYDROFABRIC_DATASET_NAME="${2}"
            shift
            ;;
        --partition-dataset|-p)
            PARTITION_DATASET_NAME="${2}"
            shift
            ;;
        --num-partitions|-n)
            NUM_PARTITIONS="${2}"
            shift
            ;;
        --output-file|-o)
            PARTITION_OUTPUT_BASENAME="${2:?}"
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

# Get some universally applicable functions and constants
source ./funcs.sh

# Make sure the directories are available
PARTITION_DATASET_DIR="${ALL_DATASET_DIR:?}/config/${PARTITION_DATASET_NAME:?No partition config dataset given}"
HYDROFABRIC_DATASET_DIR="${ALL_DATASET_DIR}/hydrofabric/${HYDROFABRIC_DATASET_NAME:?No hydrofabric dataset given}"
check_for_dataset_dir "${PARTITION_DATASET_DIR}"
check_for_dataset_dir "${HYDROFABRIC_DATASET_DIR}"

# Set some defaults
if [ -z "${CATCHMENT_DATA_FILE_NAME}" ]; then
    CATCHMENT_DATA_FILE_NAME="catchment_data.geojson"
fi
if [ -z "${NEXUS_DATA_FILE_NAME}" ]; then
    NEXUS_DATA_FILE_NAME="nexus_data.geojson"
fi

# args to ngen partition executable are (see also below where actually used):
#       catchment_data_file, nexus_data_file, output_file, num_partitions, nexus_subset, catchment_subset
# Should actually be set by ENV
#NGEN_PART_EXECUTABLE="partitionGenerator"

# Run the partitioner
# Again, args are: catchment_data_file, nexus_data_file, output_file, num_partitions, nexus_subset, catchment_subset
${NGEN_PART_EXECUTABLE:?Partitioning executable name not provided} \
    ${HYDROFABRIC_DATASET_DIR}/${CATCHMENT_DATA_FILE_NAME} \
    ${HYDROFABRIC_DATASET_DIR}/${NEXUS_DATA_FILE_NAME} \
    ${PARTITION_DATASET_DIR}/${PARTITION_OUTPUT_BASENAME:-partition_config.json} \
    ${NUM_PARTITIONS:?} \
    ${NEX_SUBSET:-} \
    ${CAT_SUBSET:-}
