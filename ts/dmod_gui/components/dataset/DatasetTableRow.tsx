import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import {
  Box,
  Collapse,
  IconButton,
  TableCell,
  TableRow,
  Typography,
} from "@mui/material";
import {DatasetRecord, File} from ".";
import { useToggle } from "../../hooks/useToggle";
import {GenericArrayTable, GenericTable} from "../GenericTable";
import humanReadableFileSize from "../../utils/humanReadableFileSize";
import Button from "@mui/material/Button";

export interface DatasetTableRowProps {
  id: string
  dataset_record: DatasetRecord;
}

export function makeFileRow(
    id: string,
    entry: File
): JSX.Element {
    return (
        <TableRow id={`${id}-file-${entry.id}`}>
            <TableCell>{entry.name}</TableCell>
            <TableCell>{humanReadableFileSize(entry.size)}</TableCell>
            <TableCell align="right">
                {/* TODO: download when this is clicked */}
                <Button variant="contained">Download</Button>
            </TableCell>
        </TableRow>
    );
}

export function DatasetTableRow(props: DatasetTableRowProps): JSX.Element {
  const { id, dataset_record } = props;
  const { files, category, action, dataset_name: name } = dataset_record;

  const [open, toggleOpen] = useToggle(false);
  const cleanName = name.replace(" ", "-")
  const fileColumns = ["Filename", "Size", {columnName: "", styles: {"align": "right"}}]
  
  const rowID = `${id}-${cleanName}`;

  return (
    <>
      <TableRow id={rowID} className={`dataset ${cleanName}`} data-name={name}>
        <TableCell>
          <IconButton aria-label="expand row" size="small" onClick={toggleOpen}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell className="dataset-name">{name}</TableCell>
        <TableCell className="dataset-category">{category}</TableCell>
        <TableCell className="dataset-action">{action}</TableCell>
      </TableRow>
      <TableRow id={`${rowID}-files`} className="dataset-files">
        <TableCell colSpan={4}>
          {/* Collapsible Table*/}
          <Collapse in={open} unmountOnExit>
            <Box sx={{ maxWidth: "600px", marginLeft: "2em" }}>
              <Typography variant="subtitle1" gutterBottom>
                Dataset Files
              </Typography>
              <GenericArrayTable id={rowID} columnNames={fileColumns} data={files} rowFunction={makeFileRow}/>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

export default DatasetTableRow;
