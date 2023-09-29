import Form from "@rjsf/mui";
import {RJSFSchema, UiSchema, WidgetProps} from "@rjsf/utils";
import { useRef, useState } from "react";
import schema from "../../schemas/EvaluationSpecification.schema.json";

import AddCircleIcon from "@mui/icons-material/AddCircle";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  Box,
  Button,
  IconButton,
  List,
  ListItem,
  MenuItem,
  Select,
  TextField,
} from "@mui/material";
import validator from "@rjsf/validator-ajv8";
import subsetSchema from "../../utils/subsetSchema";
import {FormSteps, FormWizard} from "../../components/lib/FormWizard";

const EvaluationSchema = schema as RJSFSchema;

const uiSchema: UiSchema = {
    "ui:options": {
        title: "Create Evaluation",
        classNames: "formRoot"
    }
}

const observations = subsetSchema(EvaluationSchema, ['observations'])
const predictions = subsetSchema(EvaluationSchema, ['predictions'])
const crosswalks = subsetSchema(EvaluationSchema, ['crosswalks'])

const configurationSteps: FormSteps = [
    { label: "Select Observations", schema: observations },
    { label: "Select Predictions", schema: predictions },
    { label: "Setup Crosswalk", schema: crosswalks }
]

export function Index() {
  return <FormWizard steps={configurationSteps}/>
}

export default Index;