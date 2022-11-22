import { UiSchema, RJSFSchema } from "@rjsf/utils";
import NgenConfigSchema from "../../schemas/ngen/NgenConfig.schema.json";
import subsetSchema from "../../utils/subsetSchema";
import FormWizard, { FormSteps } from "../lib/FormWizard";

const HIDE = { "ui:widget": "hidden" };

const uiSchema: UiSchema = {
  global: {
    calibration: HIDE,
    formulations: {
      params: {
        init_config: HIDE,
        allow_exceed_end_time: HIDE,
        fixed_time_step: HIDE,
        uses_forcing_file: HIDE,
        output_headers: HIDE,
        library_file: HIDE,
        registration_function: HIDE,
      },
    },
  },
};

const time = subsetSchema(NgenConfigSchema as RJSFSchema, ["time"]);
const realization = subsetSchema(NgenConfigSchema as RJSFSchema, ["global"]);
const routing = subsetSchema(NgenConfigSchema as RJSFSchema, ["routing"]);
const steps: FormSteps = [
  { label: "Choose Modeling Duration", schema: time },
  { label: "Configure Realization", schema: realization, ui_schema: uiSchema },
  { label: "Configure Routing", schema: routing },
];

export const Config = () => {
  return <FormWizard steps={steps} />;
};

export default Config;
