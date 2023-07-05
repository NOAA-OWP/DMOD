import { JobId, Message, OutputDataId, Reason, Success } from "./value_objects";

export interface NgenRequestResponse {
  success: Success;
  reason: Reason;
  message?: Message;
  data?: ModelExecRequestResponseBodyData;
  [k: string]: unknown;
}
export default NgenRequestResponse;

export type ModelExecRequestResponseBodyData =
  | ModelExecRequestResponseBody
  | {
      [k: string]: unknown;
    };

export interface ModelExecRequestResponseBody {
  job_id?: JobId;
  output_data_id?: OutputDataId;
  scheduler_response: SchedulerRequestResponse;
  [k: string]: unknown;
}

export type SchedulerRequestResponseBodyData =
  | SchedulerRequestResponseBody
  | {
      [k: string]: null;
    };

export interface SchedulerRequestResponseBody {
  job_id?: JobId;
  output_data_id?: OutputDataId;
  [k: string]: unknown;
}

export interface SchedulerRequestResponse {
  success: Success;
  reason: Reason;
  message?: Message;
  data?: SchedulerRequestResponseBodyData;
  [k: string]: unknown;
}
