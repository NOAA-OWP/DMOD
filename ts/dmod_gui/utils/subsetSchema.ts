import { RJSFSchema } from "@rjsf/utils";

export default function subsetSchema(
  s: RJSFSchema,
  fields: string[]
): RJSFSchema {
  const target_fields = new Set(fields);

  // filter
  const properties = s.properties ?? {};

  const subset_properties = Object.keys(properties)
    .filter((key) => target_fields.has(key))
    .reduce((cur, key) => {
      return Object.assign(cur, { [key]: properties[key] });
    }, {});

  const subset_required = (s.required ?? []).filter(
    (prop_name) => prop_name in target_fields
  );

  return {
    ...s,
    properties: subset_properties,
    required: subset_required,
  } as RJSFSchema;
}
