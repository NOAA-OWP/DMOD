import Button from "@mui/material/Button";
import Step from "@mui/material/Step";
import StepButton from "@mui/material/StepButton";
import Stepper from "@mui/material/Stepper";
import { Form } from "@rjsf/mui";
import { RJSFSchema, UiSchema } from "@rjsf/utils";
import validator from "@rjsf/validator-ajv8";
import { useState } from "react";

// TODO: move interfaces and types to own file.
export interface FormStep {
  label: string;
  schema: RJSFSchema;
  ui_schema?: UiSchema;
}

export type FormSteps = FormStep[];

// toggle on and off specific ui schemas
export interface FormWizardProps {
  steps: FormSteps;
}

interface FormWizardState {
  validSteps: boolean[];
  currentStep: number;
  data: object;
}

export const FormWizard = (props: FormWizardProps) => {
  const { steps } = props;

  const [state, setState] = useState<FormWizardState>(() => ({
    validSteps: Array(steps.length).fill(false),
    currentStep: 0,
    data: {},
  }));

  const handleJumpToStep = (idx: number) => {
    setState((curr) => ({ ...curr, currentStep: idx }));
  };
  const handlePrevStep = () => {
    setState((curr) => ({ ...curr, currentStep: curr.currentStep - 1 }));
  };

  const handleUpdateForm = (data: object) => {
    setState((curr) => {
      curr.validSteps[curr.currentStep] = true;
      if (curr.currentStep < curr.validSteps.length - 1) {
        curr.currentStep++;
      }
      return { ...curr, data: { ...curr.data, ...data } };
    });
  };

  // "submit" button is "Next" if more stages, otherwise, "Finish"
  const submit_button_ui = {
    "ui:submitButtonOptions": {
      submitText: state.currentStep !== steps.length - 1 ? "Next" : "Finish",
    },
  };

  return (
    <>
      <Stepper activeStep={state.currentStep}>
        {steps.map((step, idx) => {
          return (
            <Step key={idx} completed={state.validSteps[idx]}>
              <StepButton onClick={() => handleJumpToStep(idx)}>
                {step.label}
              </StepButton>
            </Step>
          );
        })}
      </Stepper>

      <Form
        validator={validator}
        schema={steps[state.currentStep].schema}
        // combine ui schemas
        uiSchema={{
          ...submit_button_ui,
          ...steps[state.currentStep].ui_schema,
        }}
        formData={state.data}
        onSubmit={({ formData }) => handleUpdateForm(formData)}
      />
      {state.currentStep > 0 && <Button onClick={handlePrevStep}>Back</Button>}
    </>
  );
};

export default FormWizard;
