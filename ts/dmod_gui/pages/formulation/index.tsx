import { Box, Typography } from "@mui/material";
import Config from "../../components/ngen/Config";

// uniform fields:
// set:
// - binary
// - init_config
// keep:
// -
// drop:
// - partitions
// - parallel
//
// already-selected:
// - catchments
// - nexus
// - crosswalk

const ui_schema = {
  /*
  hidden fields
  */
  // type: { "ui:widget": "hidden" }, // defaults to "ngen"
  // realization: {
  //   "ui:widget": "file",
  //   "ui:title": "Realization",
  //   "ui:description": "NGen Realization file to initialize calibration from.",
  //   "ui:options": {
  //     accept: ".json",
  //     title: "Title",
  //     description: "Description",
  //   },
  // },
  // hydrofabric: { "ui:widget": "hidden" },
  // ngen_realization: { "ui:widget": "hidden" },
  // strategy: { "ui:widget": "hidden" },
  // args: { "ui:widget": "hidden" }, // I think we can ignore this for now
  // binary: { "ui:widget": "hidden" }, // defaults to "ngen"
  // ngen_realization: {
  //   global: {
  //     formulations: {
  //       init_config: { "ui:widget": "text" },
  //     },
  //   },
  //   calibration: {
  //     "ui:widget": "hidden",
  //   },
  // },
  // params: {
  //   "ui:description": "Define parameters to calibrate",
  //   "ui:title": "Calibration Parameters",
  // },
};

const default_parameters = {
  // required
  type: "ngen", // will need to be re-evaluated in the future, but for now is only

  // optional
  workdir: "/home/user",
  restart: false,
  start_iteration: 0,
  parallel: 1,
  binary: "ngen",
  // args: "", // do we need defaults for this?
};

export const Formulation = () => {
  // const [data, setData] = useState(initial_data);

  // const f = (data, event) => {
  //   console.log("data: ", data, "\n", "event: ", event);
  // };

  return (
    <Box sx={{ margin: "2em 25em" }}>
      <Typography variant="h5">Configure NGEN Realization</Typography>
      <br />
      <Config />
    </Box>
  );
};

export default Formulation;
