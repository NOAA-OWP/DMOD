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
import { DatasetRecord } from ".";
import { useToggle } from "../../hooks/useToggle";
import FilesTable from "./FilesTable";

export interface DatasetTableRowProps {
  dataset_record: DatasetRecord;
}

export const DatasetTableRow = (props: DatasetTableRowProps) => {
  const { dataset_record } = props;
  const { files, dataset_name: name } = dataset_record;

  const [open, toggleOpen] = useToggle(false);

  // TODO: hook up category and actions when better understood
  const category = "FORCING";
  const actions = ["something"];

  return (
    <>
      <TableRow>
        <TableCell>
          <IconButton aria-label="expand row" size="small" onClick={toggleOpen}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell>{name}</TableCell>
        <TableCell>{category}</TableCell>
        <TableCell>{actions}</TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={4}>
          {/* Collapsible Table*/}
          <Collapse in={open} unmountOnExit>
            <Box sx={{ maxWidth: "600px", marginLeft: "2em" }}>
              <Typography variant="subtitle1" gutterBottom>
                Dataset Files
              </Typography>
              <FilesTable files={files} />
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
};

export default DatasetTableRow;
