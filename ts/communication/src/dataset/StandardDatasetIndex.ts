export type UnknownStandardDatasetIndex = "UNKNOWN";
export type TimeStandardDatasetIndex = "TIME";
export type CatchmentIdStandardDatasetIndex = "CATCHMENT_ID";
export type DataIdStandardDatasetIndex = "DATA_ID";
export type HydrofabricIdStandardDatasetIndex = "HYDROFABRIC_ID";
export type LengthStandardDatasetIndex = "LENGTH";
export type GlobalChecksumStandardDatasetIndex = "GLOBAL_CHECKSUM";
export type ElementIdStandardDatasetIndex = "ELEMENT_ID";
export type RealizationConfigDataIdStandardDatasetIndex =
  "REALIZATION_CONFIG_DATA_ID";
export type FileNameStandardDatasetIndex = "FILE_NAME";

export type StandardDatasetIndex =
  | UnknownStandardDatasetIndex
  | TimeStandardDatasetIndex
  | CatchmentIdStandardDatasetIndex
  | DataIdStandardDatasetIndex
  | HydrofabricIdStandardDatasetIndex
  | LengthStandardDatasetIndex
  | GlobalChecksumStandardDatasetIndex
  | ElementIdStandardDatasetIndex
  | RealizationConfigDataIdStandardDatasetIndex
  | FileNameStandardDatasetIndex;
export default StandardDatasetIndex;
