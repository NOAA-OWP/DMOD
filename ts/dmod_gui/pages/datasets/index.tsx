import { Box, Drawer, Fab, IconButton, SxProps } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import {DatasetRecord} from "../../components/dataset";
import { makeDatasetRow } from "../../components/dataset/DatasetTable";
import CreateDataset from "../../components/dataset/forms/CreateDataset";
import ExitIcon from "@mui/icons-material/HighlightOff";
import useToggle from "../../hooks/useToggle";
import {GenericTable} from "../../components/GenericTable";

const MOCK_DATASET_FILES: Record<string, DatasetRecord> = {
  "42": {
    action: "foo",
    data_id: "42",
    dataset_name: "my_cool_dataset",
    item_name: "my_cool_item",
    query_results: {},
    is_awaiting: false,
    category: "Forcing",
    files: [
      { id: "1", name: "some_cool_file", size: 1024, url: "https://fake.gov" },
    ],
  },
  "43": {
    action: "bar",
    data_id: "43",
    dataset_name: "my_dumb_dataset",
    item_name: "my_dumb_item",
    query_results: {},
    is_awaiting: false,
    category: "Forcing",
    files: [
      { id: "2", name: "some_stupid_file", size: 102408598, url: "https://fake.gov/dumb" },
    ],
  },
  "44": {
    action: "baz",
    data_id: "44",
    dataset_name: "my_awesome_dataset",
    item_name: "my_awesome_item",
    query_results: {},
    is_awaiting: true,
    category: "Forcing",
    files: [
      { id: "3", name: "some_awesome_file", size: 10240853, url: "https://fake.gov/awesome" },
      { id: "4", name: "some_other_awesome_file", size: 1024085, url: "https://fake.gov/awesome/other" },
    ],
  },
};

const style: SxProps = {
  bgcolor: "background.paper",
  opacity: 1,
  p: "0.5em 2em",
  maxWidth: 500,
};

export const Index = () => {
  const [open, toggleOpen] = useToggle(false);
  const columnNames = [{columnName:'', styles: {width: "2em"}}, 'Dataset Name', 'Category', 'Actions'];
  
  return (
    <Box>
        <GenericTable
            id="DatasetTable"
            columnNames={columnNames}
            data={MOCK_DATASET_FILES}
            rowFunction={makeDatasetRow}
        />
      <Fab
        color="primary"
        aria-label="add"
        onClick={toggleOpen}
        sx={{ position: "absolute", top: "4.6em", right: 16 }}
      >
        <AddIcon />
      </Fab>
      <Drawer anchor="right" open={open}>
        <IconButton
          sx={{
            position: "absolute",
            left: "87%",
            top: "0.5em",
            zIndex: 1000,
          }}
          onClick={toggleOpen}
        >
          <ExitIcon />
        </IconButton>
        <Box sx={style}>
          <CreateDataset />
        </Box>
      </Drawer>
    </Box>
  );
};

export default Index;
