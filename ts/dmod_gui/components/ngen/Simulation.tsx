import { ChangeEvent, useState } from "react";
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  TextField,
  SxProps,
  Button,
} from "@mui/material";

enum Model {
  NWM = "nwm",
  NGEN = "ngen",
}

enum OutputVariable {
  streamflow = "streamflow",
}

interface SimulationState {
  model: Model;
  domain: string;
  version: string;
  output_variable: OutputVariable;
}

const initial_state: SimulationState = {
  model: Model.NGEN,
  domain: "example-domain-A",
  version: "1.0",
  output_variable: OutputVariable.streamflow,
};

const FAKE_DOMAINS = ["example-domain-A", "example-domain-B"];

export interface SimulationProps {
  sx?: SxProps;
}

export const Simulation = (props: SimulationProps) => {
  const { sx } = props;
  const [{ model, domain, version, output_variable }, setState] =
    useState<SimulationState>(initial_state);

  const handleModel = (event: ChangeEvent<HTMLInputElement>) => {
    setState((curr) => ({ ...curr, model: event.target.value as Model }));
  };
  const handleDomain = (event: ChangeEvent<HTMLInputElement>) => {
    setState((curr) => ({ ...curr, domain: event.target.value }));
  };
  const handleVersion = (event: ChangeEvent<HTMLInputElement>) => {
    setState((curr) => ({ ...curr, version: event.target.value }));
  };
  const handleOutputVariable = (event: ChangeEvent<HTMLInputElement>) => {
    setState((curr) => ({
      ...curr,
      output_variable: event.target.value as OutputVariable,
    }));
  };

  return (
    <FormControl fullWidth sx={sx}>
      <TextField
        select
        value={model}
        label="Model"
        onChange={handleModel}
        required
      >
        {Object.values(Model).map((value) => (
          <MenuItem key={value} value={value}>
            {value}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        select
        value={domain}
        label="Domain"
        onChange={handleDomain}
        required
      >
        {FAKE_DOMAINS.map((value, idx) => (
          <MenuItem key={idx} value={value}>
            {value}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        value={version}
        label="Version"
        type="number"
        inputProps={{ step: "0.1", min: "0.0" }}
        onChange={handleVersion}
        required
      />
      <TextField
        value={output_variable}
        label="Output Variable"
        onChange={handleOutputVariable}
        select
        required
      >
        {Object.values(OutputVariable).map((value) => (
          <MenuItem key={value} value={value}>
            {value}
          </MenuItem>
        ))}
      </TextField>
      <Button variant="contained" sx={{ width: "12em", alignSelf: "center" }}>
        Launch
      </Button>
    </FormControl>
  );
};

export default Simulation;
