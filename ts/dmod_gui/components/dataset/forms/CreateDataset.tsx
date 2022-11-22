import Form from "@rjsf/mui";
import { UiSchema, WidgetProps } from "@rjsf/utils";
import { useRef, useState } from "react";
import schema from "../../../schemas/DatasetManager.schema.json";

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

const CatchmentIdField = (props: WidgetProps) => {
  const textRef = useRef<HTMLInputElement>();

  const handleAdd = () => {
    const currentId = textRef?.current?.value;
    currentId && props.onChange([...props.value, currentId]);
  };

  return (
    <>
      <Box
        sx={{ display: "flex", gap: "1.5em", justifyContent: "space-around" }}
      >
        <IconButton
          aria-label="add"
          disabled={props.disabled}
          onClick={handleAdd}
        >
          <AddCircleIcon />
        </IconButton>
        <TextField
          sx={{ flexGrow: 1 }}
          required={props.required}
          disabled={props.disabled}
          variant="outlined"
          label="Enter Catchment Id"
          inputRef={textRef}
        />
      </Box>
      <List>
        {props.value.map((value: string, idx: string) => {
          return (
            <ListItem key={idx}>
              {value}
              <IconButton
                onClick={() =>
                  props.onChange([
                    ...props.value.slice(0, idx),
                    ...props.value.slice(idx + 1),
                  ])
                }
              >
                <DeleteIcon />
              </IconButton>
            </ListItem>
          );
        })}
      </List>
    </>
  );
};

const UploadDatasetField = (props: WidgetProps) => (
  <Button variant="contained" component="label">
    Upload Dataset
    <input hidden type="file" />
  </Button>
);

function title_case(s: string): string {
  return s.replace(
    /\w\S*/g,
    (txt: string) => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase()
  );
}

function FormatEnumField(fn: (s: string) => string) {
  function FormattedEnumField(props: EnumWidgetProps) {
    return <EnumField {...props} handleValue={fn} />;
  }
  return FormattedEnumField;
}

interface EnumWidgetProps extends WidgetProps {
  handleValue?: (value: string) => string;
}

const EnumField = (props: EnumWidgetProps) => (
  <Select
    onChange={(e) => props.onChange(e.target.value)}
    value={props.value ?? ""}
  >
    {props.options.enumOptions?.map(({ value, label }) => (
      <MenuItem key={value} value={value}>
        {props.handleValue ? props.handleValue(label) : label}
      </MenuItem>
    ))}
  </Select>
);

const uiSchema: UiSchema = {
  "ui:options": {
    title: "Create Dataset",
    classNames: "formRoot",
  },
  category: {
    "ui:options": {
      widget: FormatEnumField((s: string) =>
        title_case(s.replaceAll("_", " "))
      ),
      label: "",
    },
  },
  data_format: {
    "ui:options": {
      classNames: "dataFormat",
      widget: FormatEnumField((s: string) =>
        title_case(s.replaceAll("_", " "))
      ),
    },
    catchment_id: {
      "ui:options": {
        widget: CatchmentIdField,
      },
    },
    file: {
      "ui:options": {
        widget: UploadDatasetField,
      },
    },
  },
};

export const CreateDataset = () => {
  const [data, setData] = useState({});

  return (
    <Form
      validator={validator}
      schema={schema}
      uiSchema={uiSchema}
      formData={data}
    />
  );
};

export default CreateDataset;
