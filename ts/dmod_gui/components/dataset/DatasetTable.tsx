import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import { DatasetFiles } from ".";
import DatasetTableRow from "./DatasetTableRow";

export interface DatasetTableProps {
  dataset_files: DatasetFiles;
}

export const DatasetTable = (props: DatasetTableProps) => {
  const { dataset_files } = props;

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
                <DatasetTableRow dataset_record={dataset_files[dataset_key]} />
              </React.Fragment>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default DatasetTable;
