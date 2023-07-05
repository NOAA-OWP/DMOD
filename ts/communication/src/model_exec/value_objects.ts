/**
 * Representation of the ways compute assets may be combined to fulfill a total required asset amount for a task.
 *
 * The values are as follows:
 *     FILL_NODES  - obtain allocations of assets by proceeding through resources in some order, getting either the max
 *                   possible allocation from the current resource or a allocation that fulfills the outstanding need,
 *                   until the sum of assets among all received allocations is sufficient; also, have allocations be
 *                   single cpu/process
 *     ROUND_ROBIN - obtain allocations of assets from available resource nodes in a round-robin manner; also, have
 *                   allocations be single cpu/process
 *     SINGLE_NODE - require all allocation of assets to be from a single resource/host; also, require allocations to
 *                   be single cpu/process
 */
export type AllocationParadigm = "FILL_NODES" | "ROUND_ROBIN" | "SINGLE_NODE";

/**
 * The number of processors requested for this job.
 */
export type CpuCount = number;

export type SessionSecret = string;

export type BmiConfigDataId = string;
export type CatchmentId = string;
export type Catchments = CatchmentId[];
export type ForcingsDataId = string;
export type HydrofabricDataId = string;
export type HydrofabricUid = string;
export type JobId = number;
export type OutputDataId = string;
export type PartitionConfigDataId = string;
export type RealizationConfigDataId = string;

/**
 * Whether this indicates a successful result.
 */
export type Success = boolean;
/**
 * A very short, high-level summary of the result.
 */
export type Reason = string;
/**
 * An optional, more detailed explanation of the result, which by default is an empty string.
 */
export type Message = string;
