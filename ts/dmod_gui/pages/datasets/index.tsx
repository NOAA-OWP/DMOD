import { Box, Drawer, Fab, IconButton, SxProps } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { DatasetFiles } from "../../components/dataset";
import { DatasetTable } from "../../components/dataset/DatasetTable";
import CreateDataset from "../../components/dataset/forms/CreateDataset";
import ExitIcon from "@mui/icons-material/HighlightOff";
import useToggle from "../../hooks/useToggle";

const MOCK_DATASET_FILES: DatasetFiles = {
  "42": {
    action: "foo",
    data_id: "42",
    dataset_name: "my_cool_dataset",
    item_name: "my_cool_item",
    query_results: {},
    is_awaiting: false,
    files: [
      { id: "1", name: "some_cool_file", size: 1024, url: "https://fake.gov" },
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
  return (
    <Box>
      <DatasetTable dataset_files={MOCK_DATASET_FILES} />
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
