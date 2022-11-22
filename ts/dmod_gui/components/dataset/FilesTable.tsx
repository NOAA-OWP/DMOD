import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Button from "@mui/material/Button";
import { File } from "./index";
import humanReadableFileSize from "../../utils/humanReadableFileSize";

export interface FilesTableProps {
  files: File[];
}

export const FilesTables = (props: FilesTableProps) => {
  const { files } = props;

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Filename</TableCell>
          <TableCell>Size</TableCell>
          <TableCell align="right">
            {/* placeholder row for download links*/}
          </TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {files.map((file) => (
          <TableRow key={file.id}>
            <TableCell>{file.name}</TableCell>
            <TableCell>{humanReadableFileSize(file.size)}</TableCell>
            <TableCell align="right">
              {/* TODO: download when this is clicked */}
              <Button variant="contained">Download</Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

export default FilesTables;
