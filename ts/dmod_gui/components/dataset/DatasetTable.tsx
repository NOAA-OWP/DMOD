import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import {DatasetFiles, DatasetRecord} from ".";
import DatasetTableRow from "./DatasetTableRow";
import {GDataTableType} from "../GenericTable";

export interface DatasetTableProps {
  dataset_files: DatasetFiles;
}

export function makeDatasetRow(
    id: string,
    dataRecord: DatasetRecord,
    index: string | number,
    data: GDataTableType<DatasetRecord>
): JSX.Element {
  return (
      <>
        <DatasetTableRow id={id} dataset_record={dataRecord}/>
      </>
  );
}

export const DatasetTable = (props: DatasetTableProps) => {
  const { dataset_files } = props;
  const id = "DatasetTable";

  return (
    <TableContainer>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell width={"2rem"} />
            <TableCell>Dataset Name</TableCell>
            <TableCell>Category</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>

        <TableBody>
          {Object.keys(dataset_files).map((dataset_key) => {
            return (
              <React.Fragment key={dataset_key}>
                <DatasetTableRow id={id} dataset_record={dataset_files[dataset_key]} />
              </React.Fragment>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default DatasetTable;
