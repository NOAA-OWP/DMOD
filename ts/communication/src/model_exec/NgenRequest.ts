import TimeRange from "../dataset/TimeRange";
import {
  AllocationParadigm,
  BmiConfigDataId,
  Catchments,
  CpuCount,
  ForcingsDataId,
  HydrofabricDataId,
  HydrofabricUid,
  PartitionConfigDataId,
  RealizationConfigDataId,
  SessionSecret,
} from "./value_objects";

export type NgenJobType = "ngen";

/**
 * An abstract extension of ::class:`DmodJobRequest` for requesting model execution jobs.
 *
 * Note that subtypes must ensure they define both the ::attribute:`model_name` class attribute and the
 * ::attribute:`job_type` instance attribute to the same value.  The latter will be a discriminator, so should be
 * defined as a fixed ::class:`Literal`. The ::method:`factory_init_correct_subtype_from_deserialized_json` class
 * function requires this to work correctly.
 */
export interface NgenRequest {
  job_type: NgenJobType;
  cpu_count?: CpuCount;
  /**
   * The allocation paradigm desired for use when allocating resources for this request.
   */
  allocation_paradigm?: AllocationParadigm;
  request_body: NgenRequestBody;
  session_secret: SessionSecret;
  [k: string]: unknown;
}
export default NgenRequest;

export interface NgenRequestBody {
  time_range: TimeRange;
  hydrofabric_uid: HydrofabricUid;
  hydrofabric_data_id: HydrofabricDataId;
  realization_config_data_id: RealizationConfigDataId;
  forcings_data_id?: ForcingsDataId;
  bmi_config_data_id: BmiConfigDataId;
  catchments?: Catchments;
  partition_config_data_id?: PartitionConfigDataId;
  [k: string]: unknown;
}
