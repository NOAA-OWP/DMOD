import { TimeStandardDatasetIndex } from "./StandardDatasetIndex";

/**
 * Encapsulated representation of a time range.
 */
export interface TimeRange {
  variable?: TimeStandardDatasetIndex;
  begin: string;
  end: string;
  datetime_pattern: DatetimePattern;
  // NOTE: at this time, it does not make sense to consider the `subclass` field
  // subclass?: Subclass;
  [k: string]: unknown;
}
export default TimeRange;

export type DefaultDatetimePattern = "%Y-%m-%d %H:%M:%S";
export type DatetimePattern = DefaultDatetimePattern | string;
