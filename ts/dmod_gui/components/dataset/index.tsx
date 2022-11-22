interface Files {
  files: File[];
}

export interface File {
  id: string;
  name: string;
  size: number;
  url: string;
}

export interface DatasetResponse {
  action: string;
  data_id: string;
  dataset_name: string;
  item_name: string;
  query_results: any; // dont know what this should be
  is_awaiting: boolean;
  //   [k: string]: keyof DatasetResponse;
}

export type DatasetResponses = DatasetResponse[];

export type DatasetRecord = DatasetResponse & Files;

export interface DatasetFiles {
  [dataset_id: string]: DatasetRecord;
}
