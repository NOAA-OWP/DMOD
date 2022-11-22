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
    label: "Configure Calibration",
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
    label: "Choose Forcing and Modeling Duration",
    schema: subsetSchema(NgenRealizationSchema as RJSFSchema, ["time"]),
  },
  {
    label: "Configure Realizations",
    schema: RealizationSchema as RJSFSchema,
    ui_schema: {
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
  },
  {
    label: "Configure Routing",
    schema: NgenRealizationSchema as RJSFSchema,
    ui_schema: {
      global: HIDE,
      time: HIDE,
      catchments: HIDE,
    },
  },
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
