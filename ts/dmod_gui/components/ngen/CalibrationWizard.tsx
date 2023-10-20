import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Step from "@mui/material/Step";
import StepButton from "@mui/material/StepButton";
import Stepper from "@mui/material/Stepper";
import { Form } from "@rjsf/mui";
import { RJSFSchema, UiSchema } from "@rjsf/utils";
import validator from "@rjsf/validator-ajv8";
import dynamic from "next/dynamic";
import { useState } from "react";
import NgenRealizationSchema from "../../schemas/NgenRealization.schema.json";
import RealizationSchema from "../../schemas/Realization.schema.json";
import NgenCalSchema from "../../schemas/General.schema.json";
import NgenUniformSchema from "../../schemas/NgenUniformSingle.schema.json";
import NgenRealizationSingleSchema from "../../schemas/NgenRealizationSingle.schema.json";
import subsetSchema from "../../utils/subsetSchema";

const Map = dynamic(() => import("../HydrofabricMap"), {
  ssr: false,
});

interface FormStep {
  label: string;
  schema: RJSFSchema;
  ui_schema?: UiSchema;
}

const HIDE = { "ui:widget": "hidden" };

// global.formulations.params.modules[0].params.variables_names_map;
// based on model type name, set `variables_names_map`

const default_variable_names_map = {
  CFE: { atmosphere_water__liquid_equivalent_precipitation_rate: "QINSUR" },
  NoahOWP: {
    PRCPNONC: "atmosphere_water__liquid_equivalent_precipitation_rate",
    Q2: "atmosphere_air_water~vapor__relative_saturation",
    SFCTMP: "land_surface_air__temperature",
    UU: "land_surface_wind__x_component_of_velocity",
    VV: "land_surface_wind__y_component_of_velocity",
    LWDN: "land_surface_radiation~incoming~longwave__energy_flux",
    SOLDN: "land_surface_radiation~incoming~shortwave__energy_flux",
    SFCPRS: "land_surface_air__pressure",
  },
  LSTM: {
    atmosphere_water__time_integral_of_precipitation_mass_flux: "RAINRATE",
  },
  TOPMODEL: {
    atmosphere_water__liquid_equivalent_precipitation_rate: "QINSUR",
  },
  PET: {
    water_potential_evaporation_flux: "water_potential_evaporation_flux",
  },
};

function handleDefaultVariableNameMapping(formData: object) {
  formData?.global?.formulations?.params?.modules?.forEach((m) => {
    const model_name = m?.params?.model_type_name;

    if (m?.params?.variables_names_map) {
      m.params.variables_names_map = default_variable_names_map[model_name];
    }
  });
  return formData;
}

const steps: FormStep[] = [
  {
    label: "Select Hydrofabric",
    schema: {
      properties: {
        hydrofabric_element: {
          type: "string",
          enum: ["Catchment", "Flowpath", "Nexus"],
        },
      },
    },
    ui_schema: {
      hydrofabric_element: HIDE,
    },
  },
  {
    label: "Configure Formulations",
    schema: subsetSchema(NgenRealizationSingleSchema as RJSFSchema, ["global"]),
    ui_schema: {
      time: HIDE,
      routing: HIDE,
      global: {
        forcing: HIDE,
      },
      catchments: HIDE,
    },
  },
  {
    label: "Select Calibration Type",
    schema: {
      properties: {
        strategy: {
          title: "Strategy",
          enum: [
            // This will be added in the future.
            //   "explicit",
            "uniform",
            "independent",
          ],
          type: "string",
        },
      },
      required: ["strategy"],
    },
  },
  {
    label: "Configure Calibration",
    schema: NgenCalSchema as RJSFSchema,
    ui_schema: {
      start_iteration: HIDE,
      evaluation_start: HIDE,
      evaluation_stop: HIDE,
      log_file: HIDE,
      workdir: HIDE,
      restart: HIDE,
      parameter_log_file: HIDE,
      objective_log_file: HIDE,
    },
  },
  {
    label: "Configure Calibration Parameters",
    schema: NgenUniformSchema as RJSFSchema,
    // ui_schema: {
    //   hydrofabric_element: HIDE,
    // },
  },
  {
    label: "Choose Forcing and Modeling Duration",
    schema: subsetSchema(NgenRealizationSchema as RJSFSchema, ["time"]),
  },
  // {
  //   label: "Configure Realizations",
  //   schema: RealizationSchema as RJSFSchema,
  //   ui_schema: {
  //     formulations: {
  //       params: {
  //         init_config: HIDE,
  //         allow_exceed_end_time: HIDE,
  //         fixed_time_step: HIDE,
  //         uses_forcing_file: HIDE,
  //         output_headers: HIDE,
  //         library_file: HIDE,
  //         registration_function: HIDE,
  //       },
  //     },
  //   },
  // },
  // {
  //   label: "Configure Routing",
  //   schema: NgenRealizationSchema as RJSFSchema,
  //   ui_schema: {
  //     global: HIDE,
  //     time: HIDE,
  //     catchments: HIDE,
  //   },
  // },
];

// refactor to use FormWizard component
export const CalibrationWizard = () => {
  // TODO: refactor state management to useReducer hook.
  // array of markers indicating if a form step is valid
  const [valid, setValid] = useState<boolean[]>(
    Array(steps.length).fill(false)
  );
  // indicates the current form step
  const [currentStep, setCurrentStep] = useState<number>(0);
  // state for all form steps
  const [data, setData] = useState<object>({});

  const base_ui_schema = {
    "ui:submitButtonOptions": {
      submitText: currentStep !== steps.length - 1 ? "Next" : "Finish",
    },
  };

  return (
    <Box sx={{ margin: "3em" }}>
      <Stepper activeStep={currentStep}>
        {steps.map((step, idx) => {
          return (
            <Step key={idx} completed={valid[idx]}>
              <StepButton onClick={() => setCurrentStep(idx)}>
                {step.label}
              </StepButton>
            </Step>
          );
        })}
      </Stepper>

      {currentStep === 0 && <Map />}

      <Form
        validator={validator}
        schema={steps[currentStep].schema}
        uiSchema={{ ...base_ui_schema, ...steps[currentStep].ui_schema }}
        formData={data}
        onChange={({ formData }) => {
          setData(handleDefaultVariableNameMapping(formData));
        }}
        onSubmit={({ formData }) => {
          setData((curr) => ({ ...formData, ...curr }));

          setValid((curr) => {
            curr[currentStep] = true;
            return curr;
          });

          if (currentStep < steps.length - 1) {
            setCurrentStep((curr) => curr + 1);
          }
        }}
      />
      {currentStep > 0 && (
        <Button
          sx={{ marginTop: "0.5em" }}
          variant="contained"
          onClick={() => {
            setCurrentStep((curr) => {
              return curr - 1;
            });
          }}
        >
          Back
        </Button>
      )}
    </Box>
  );
};

export default CalibrationWizard;
