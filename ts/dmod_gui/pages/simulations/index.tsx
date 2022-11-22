import Simulation from "../../components/ngen/Simulation";
import { Box } from "@mui/system";
import { Typography } from "@mui/material";

export const Simulations = () => {
  return (
    <Box
      sx={{
        margin: "2em 30em",
      }}
    >
      <Typography variant="h6">Configure a Simulation</Typography>
      <br />
      <Simulation
        sx={{
          display: "flex",
          flexDirection: "column",
          gap: "1em",
        }}
      />
    </Box>
  );
};

export default Simulations;
