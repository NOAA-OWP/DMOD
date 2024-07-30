# NGENRequest

**Title:** NGENRequest

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

**Description:** An abstract extension of ::class:`DmodJobRequest` for requesting model execution jobs.

Note that subtypes must ensure they define both the ::attribute:`model_name` class attribute and the
::attribute:`job_type` instance attribute to the same value.  The latter will be a discriminator, so should be
defined as a fixed ::class:`Literal`. The ::method:`factory_init_correct_subtype_from_deserialized_json` class
function requires this to work correctly.

<details>
<summary><strong> <a name="job_type"></a>1. [Optional] Property NGENRequest > job_type</strong>

</summary>
<blockquote>

**Title:** Job Type

|              |                    |
| ------------ | ------------------ |
| **Type**     | `enum (of string)` |
| **Required** | No                 |
| **Default**  | `"ngen"`           |

Must be one of:
* "ngen"

</blockquote>
</details>

<details>
<summary><strong> <a name="cpu_count"></a>2. [Optional] Property NGENRequest > cpu_count</strong>

</summary>
<blockquote>

**Title:** Cpu Count

|              |           |
| ------------ | --------- |
| **Type**     | `integer` |
| **Required** | No        |
| **Default**  | `1`       |

**Description:** The number of processors requested for this job.

| Restrictions |        |
| ------------ | ------ |
| **Minimum**  | &gt; 0 |

</blockquote>
</details>

<details>
<summary><strong> <a name="allocation_paradigm"></a>3. [Optional] Property NGENRequest > allocation_paradigm</strong>

</summary>
<blockquote>

|                |                    |
| -------------- | ------------------ |
| **Type**       | `enum (of string)` |
| **Required**   | No                 |
| **Defined in** |                    |

**Description:** The allocation paradigm desired for use when allocating resources for this request.

Must be one of:
* "FILL_NODES"
* "ROUND_ROBIN"
* "SINGLE_NODE"

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body"></a>4. [Required] Property NGENRequest > request_body</strong>

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | Yes                                                                       |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/NGENRequestBody                                             |

**Description:** Request body encapsulating data within outer request.

Encapsulated data to define a requested ngen job.  It includes details on the time range, hydrofabric, and
configurations need for executing ngen.  It may also include a reference to what forcing data to use.

An instance contains a reference to the ::class:`DataFormat.NGEN_JOB_COMPOSITE_CONFIG` dataset containing
configurations for the requested job.  In cases when this dataset doesn't yet exist, an instance also contains the
necessary details for generating such a dataset.  In particular, this includes:

    - a realization config dataset id **OR** a ::class:`PartialRealizationConfig`
    - (optionally) a BMI init config dataset id
    - (optionally) a t-route configuration dataset id

When dataset ids are given, these are treated as sources for the new ::class:`DataFormat.NGEN_JOB_COMPOSITE_CONFIG`,
with the contents of the former copied into the latter as appropriate.

<details>
<summary><strong> <a name="request_body_time_range"></a>4.1. [Required] Property NGENRequest > request_body > time_range</strong>

</summary>
<blockquote>

**Title:** Time Range

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | Yes                                                                       |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            |                                                                           |

**Description:** The time range over which to run ngen simulation(s).

<details>
<summary><strong> <a name="request_body_time_range_variable"></a>4.1.1. [Optional] Property NGENRequest > request_body > time_range > variable</strong>

</summary>
<blockquote>

|                |                    |
| -------------- | ------------------ |
| **Type**       | `enum (of string)` |
| **Required**   | No                 |
| **Default**    | `"TIME"`           |
| **Defined in** |                    |

**Description:** An enumeration.

Must be one of:
* "UNKNOWN"
* "TIME"
* "CATCHMENT_ID"
* "DATA_ID"
* "HYDROFABRIC_ID"
* "LENGTH"
* "GLOBAL_CHECKSUM"
* "ELEMENT_ID"
* "REALIZATION_CONFIG_DATA_ID"
* "FILE_NAME"
* "COMPOSITE_SOURCE_ID"

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_time_range_begin"></a>4.1.2. [Required] Property NGENRequest > request_body > time_range > begin</strong>

</summary>
<blockquote>

**Title:** Begin

|              |             |
| ------------ | ----------- |
| **Type**     | `string`    |
| **Required** | Yes         |
| **Format**   | `date-time` |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_time_range_end"></a>4.1.3. [Required] Property NGENRequest > request_body > time_range > end</strong>

</summary>
<blockquote>

**Title:** End

|              |             |
| ------------ | ----------- |
| **Type**     | `string`    |
| **Required** | Yes         |
| **Format**   | `date-time` |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_time_range_datetime_pattern"></a>4.1.4. [Optional] Property NGENRequest > request_body > time_range > datetime_pattern</strong>

</summary>
<blockquote>

**Title:** Datetime Pattern

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_time_range_subclass"></a>4.1.5. [Optional] Property NGENRequest > request_body > time_range > subclass</strong>

</summary>
<blockquote>

**Title:** Subclass

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_hydrofabric_uid"></a>4.2. [Required] Property NGENRequest > request_body > hydrofabric_uid</strong>

</summary>
<blockquote>

**Title:** Hydrofabric Uid

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** The (DMOD-generated) unique id of the hydrofabric to use.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_hydrofabric_data_id"></a>4.3. [Required] Property NGENRequest > request_body > hydrofabric_data_id</strong>

</summary>
<blockquote>

**Title:** Hydrofabric Data Id

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** The dataset id of the hydrofabric dataset to use.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_composite_config_data_id"></a>4.4. [Optional] Property NGENRequest > request_body > composite_config_data_id</strong>

</summary>
<blockquote>

**Title:** Composite Config Data Id

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** Id of required ngen composite config dataset.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_realization_config_data_id"></a>4.5. [Optional] Property NGENRequest > request_body > realization_config_data_id</strong>

</summary>
<blockquote>

**Title:** Realization Config Data Id

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** Id of composite source of realization config.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_forcings_data_id"></a>4.6. [Optional] Property NGENRequest > request_body > forcings_data_id</strong>

</summary>
<blockquote>

**Title:** Forcings Data Id

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** Id of requested forcings dataset.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_bmi_config_data_id"></a>4.7. [Optional] Property NGENRequest > request_body > bmi_config_data_id</strong>

</summary>
<blockquote>

**Title:** Bmi Config Data Id

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** Id of composite source of BMI init configs.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_catchments"></a>4.8. [Optional] Property NGENRequest > request_body > catchments</strong>

</summary>
<blockquote>

**Title:** Catchments

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

**Description:** Subset of ids of catchments to include in job.

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                    | Description |
| -------------------------------------------------- | ----------- |
| [catchments items](#request_body_catchments_items) | -           |

#### <a name="autogenerated_heading_2"></a>4.8.1. NGENRequest > request_body > catchments > catchments items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config"></a>4.9. [Optional] Property NGENRequest > request_body > partial_realization_config</strong>

</summary>
<blockquote>

**Title:** Partial Realization Config

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            |                                                                           |

**Description:** Partial realization config, when supplied by user.

<details>
<summary><strong> <a name="request_body_partial_realization_config_hydrofabric_uid"></a>4.9.1. [Required] Property NGENRequest > request_body > partial_realization_config > hydrofabric_uid</strong>

</summary>
<blockquote>

**Title:** Hydrofabric Uid

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations"></a>4.9.2. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations</strong>

</summary>
<blockquote>

**Title:** Global Formulations

|              |         |
| ------------ | ------- |
| **Type**     | `array` |
| **Required** | No      |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                   | Description                       |
| --------------------------------------------------------------------------------- | --------------------------------- |
| [Formulation](#request_body_partial_realization_config_global_formulations_items) | Model of an ngen formulation. ... |

##### <a name="autogenerated_heading_3"></a>4.9.2.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/Formulation                                                 |

**Description:** Model of an ngen formulation.

Note, during object creation if the `params` field is deserialized (e.g. `params`'s value is a
dictionary), the `name` field is required. If `name` *is not* 'bmi_multi', the `model_type_name`
field is also required. Neither are required if a concrete known formulation instance is
provided.

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_name"></a>4.9.2.1.1. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > name</strong>

</summary>
<blockquote>

**Title:** Name

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params"></a>4.9.2.1.2. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params</strong>

</summary>
<blockquote>

**Title:** Params

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `combining`                                                               |
| **Required**              | Yes                                                                       |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

<blockquote>

| Any of(Option)                                                                                 |
| ---------------------------------------------------------------------------------------------- |
| [Topmod](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i0)   |
| [CFE](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i1)      |
| [PET](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i2)      |
| [NoahOWP](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i3)  |
| [LSTM](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i4)     |
| [SLOTH](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i5)    |
| [MultiBMI](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i6) |

<blockquote>

##### <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0"></a>4.9.2.1.2.1. Property `NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/Topmod                                                      |

**Description:** A BMIC implementation for the Topmod ngen module

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_name"></a>4.9.2.1.2.1.1. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > name</strong>

</summary>
<blockquote>

**Title:** Name

|              |           |
| ------------ | --------- |
| **Type**     | `const`   |
| **Required** | No        |
| **Default**  | `"bmi_c"` |

Specific value: `"bmi_c"`

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_model_type_name"></a>4.9.2.1.2.1.2. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > model_type_name</strong>

</summary>
<blockquote>

**Title:** Model Type Name

|              |              |
| ------------ | ------------ |
| **Type**     | `const`      |
| **Required** | No           |
| **Default**  | `"TOPMODEL"` |

Must be one of:
* "TOPMODEL"
Specific value: `"TOPMODEL"`

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_main_output_variable"></a>4.9.2.1.2.1.3. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > main_output_variable</strong>

</summary>
<blockquote>

**Title:** Main Output Variable

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |
| **Default**  | `"Qout"` |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_init_config"></a>4.9.2.1.2.1.4. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > init_config</strong>

</summary>
<blockquote>

**Title:** Init Config

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `path`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_allow_exceed_end_time"></a>4.9.2.1.2.1.5. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > allow_exceed_end_time</strong>

</summary>
<blockquote>

**Title:** Allow Exceed End Time

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_fixed_time_step"></a>4.9.2.1.2.1.6. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > fixed_time_step</strong>

</summary>
<blockquote>

**Title:** Fixed Time Step

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `true`    |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_uses_forcing_file"></a>4.9.2.1.2.1.7. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > uses_forcing_file</strong>

</summary>
<blockquote>

**Title:** Uses Forcing File

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_variables_names_map"></a>4.9.2.1.2.1.8. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > variables_names_map</strong>

</summary>
<blockquote>

**Title:** Variables Names Map

|                           |                                                                                                                                                                                                                 |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                                                                        |
| **Required**              | No                                                                                                                                                                                                              |
| **Additional properties** | [[Should-conform]](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_variables_names_map_additionalProperties "Each additional property must conform to the following schema") |

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_variables_names_map_additionalProperties"></a>4.9.2.1.2.1.8.1. Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > variables_names_map > additionalProperties</strong>

</summary>
<blockquote>

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_output_variables"></a>4.9.2.1.2.1.9. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > output_variables</strong>

</summary>
<blockquote>

**Title:** Output Variables

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                     | Description |
| ----------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_variables items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_output_variables_items) | -           |

##### <a name="autogenerated_heading_4"></a>4.9.2.1.2.1.9.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > output_variables > output_variables items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_output_headers"></a>4.9.2.1.2.1.10. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > output_headers</strong>

</summary>
<blockquote>

**Title:** Output Headers

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                 | Description |
| ------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_headers items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_output_headers_items) | -           |

##### <a name="autogenerated_heading_5"></a>4.9.2.1.2.1.10.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > output_headers > output_headers items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_model_params"></a>4.9.2.1.2.1.11. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > model_params</strong>

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/TopmodParams                                                |

**Description:** Class for validating Topmod Parameters

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_model_params_sr0"></a>4.9.2.1.2.1.11.1. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > model_params > sr0</strong>

</summary>
<blockquote>

**Title:** Sr0

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_model_params_srmax"></a>4.9.2.1.2.1.11.2. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > model_params > srmax</strong>

</summary>
<blockquote>

**Title:** Srmax

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_model_params_szm"></a>4.9.2.1.2.1.11.3. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > model_params > szm</strong>

</summary>
<blockquote>

**Title:** Szm

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_model_params_t0"></a>4.9.2.1.2.1.11.4. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > model_params > t0</strong>

</summary>
<blockquote>

**Title:** T0

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_model_params_td"></a>4.9.2.1.2.1.11.5. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > model_params > td</strong>

</summary>
<blockquote>

**Title:** Td

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_library_file"></a>4.9.2.1.2.1.12. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > library_file</strong>

</summary>
<blockquote>

**Title:** Library File

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `path`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i0_registration_function"></a>4.9.2.1.2.1.13. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > Topmod > registration_function</strong>

</summary>
<blockquote>

**Title:** Registration Function

|              |                           |
| ------------ | ------------------------- |
| **Type**     | `string`                  |
| **Required** | No                        |
| **Default**  | `"register_bmi_topmodel"` |

</blockquote>
</details>

</blockquote>
<blockquote>

##### <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1"></a>4.9.2.1.2.2. Property `NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/CFE                                                         |

**Description:** A BMIC implementation for the CFE ngen module

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_name"></a>4.9.2.1.2.2.1. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > name</strong>

</summary>
<blockquote>

**Title:** Name

|              |           |
| ------------ | --------- |
| **Type**     | `const`   |
| **Required** | No        |
| **Default**  | `"bmi_c"` |

Specific value: `"bmi_c"`

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_model_type_name"></a>4.9.2.1.2.2.2. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > model_type_name</strong>

</summary>
<blockquote>

**Title:** Model Type Name

|              |         |
| ------------ | ------- |
| **Type**     | `const` |
| **Required** | No      |
| **Default**  | `"CFE"` |

Must be one of:
* "CFE"
Specific value: `"CFE"`

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_main_output_variable"></a>4.9.2.1.2.2.3. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > main_output_variable</strong>

</summary>
<blockquote>

**Title:** Main Output Variable

|              |           |
| ------------ | --------- |
| **Type**     | `string`  |
| **Required** | No        |
| **Default**  | `"Q_OUT"` |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_init_config"></a>4.9.2.1.2.2.4. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > init_config</strong>

</summary>
<blockquote>

**Title:** Init Config

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `path`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_allow_exceed_end_time"></a>4.9.2.1.2.2.5. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > allow_exceed_end_time</strong>

</summary>
<blockquote>

**Title:** Allow Exceed End Time

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_fixed_time_step"></a>4.9.2.1.2.2.6. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > fixed_time_step</strong>

</summary>
<blockquote>

**Title:** Fixed Time Step

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `true`    |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_uses_forcing_file"></a>4.9.2.1.2.2.7. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > uses_forcing_file</strong>

</summary>
<blockquote>

**Title:** Uses Forcing File

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_variables_names_map"></a>4.9.2.1.2.2.8. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > variables_names_map</strong>

</summary>
<blockquote>

**Title:** Variables Names Map

|                           |                                                                                                                                                                                                                 |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                                                                        |
| **Required**              | No                                                                                                                                                                                                              |
| **Additional properties** | [[Should-conform]](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_variables_names_map_additionalProperties "Each additional property must conform to the following schema") |

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_variables_names_map_additionalProperties"></a>4.9.2.1.2.2.8.1. Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > variables_names_map > additionalProperties</strong>

</summary>
<blockquote>

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_output_variables"></a>4.9.2.1.2.2.9. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > output_variables</strong>

</summary>
<blockquote>

**Title:** Output Variables

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                     | Description |
| ----------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_variables items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_output_variables_items) | -           |

##### <a name="autogenerated_heading_6"></a>4.9.2.1.2.2.9.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > output_variables > output_variables items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_output_headers"></a>4.9.2.1.2.2.10. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > output_headers</strong>

</summary>
<blockquote>

**Title:** Output Headers

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                 | Description |
| ------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_headers items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_output_headers_items) | -           |

##### <a name="autogenerated_heading_7"></a>4.9.2.1.2.2.10.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > output_headers > output_headers items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_model_params"></a>4.9.2.1.2.2.11. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > model_params</strong>

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/CFEParams                                                   |

**Description:** Class for validating CFE Parameters

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_model_params_maxsmc"></a>4.9.2.1.2.2.11.1. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > model_params > maxsmc</strong>

</summary>
<blockquote>

**Title:** Maxsmc

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_model_params_satdk"></a>4.9.2.1.2.2.11.2. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > model_params > satdk</strong>

</summary>
<blockquote>

**Title:** Satdk

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_model_params_slope"></a>4.9.2.1.2.2.11.3. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > model_params > slope</strong>

</summary>
<blockquote>

**Title:** Slope

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_model_params_bb"></a>4.9.2.1.2.2.11.4. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > model_params > bb</strong>

</summary>
<blockquote>

**Title:** Bb

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_model_params_multiplier"></a>4.9.2.1.2.2.11.5. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > model_params > multiplier</strong>

</summary>
<blockquote>

**Title:** Multiplier

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_model_params_expon"></a>4.9.2.1.2.2.11.6. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > model_params > expon</strong>

</summary>
<blockquote>

**Title:** Expon

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_library_file"></a>4.9.2.1.2.2.12. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > library_file</strong>

</summary>
<blockquote>

**Title:** Library File

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `path`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i1_registration_function"></a>4.9.2.1.2.2.13. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > CFE > registration_function</strong>

</summary>
<blockquote>

**Title:** Registration Function

|              |                      |
| ------------ | -------------------- |
| **Type**     | `string`             |
| **Required** | No                   |
| **Default**  | `"register_bmi_cfe"` |

</blockquote>
</details>

</blockquote>
<blockquote>

##### <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2"></a>4.9.2.1.2.3. Property `NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/PET                                                         |

**Description:** A C implementation of several ET calculation algorithms

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_name"></a>4.9.2.1.2.3.1. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > name</strong>

</summary>
<blockquote>

**Title:** Name

|              |           |
| ------------ | --------- |
| **Type**     | `const`   |
| **Required** | No        |
| **Default**  | `"bmi_c"` |

Specific value: `"bmi_c"`

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_model_type_name"></a>4.9.2.1.2.3.2. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > model_type_name</strong>

</summary>
<blockquote>

**Title:** Model Type Name

|              |                    |
| ------------ | ------------------ |
| **Type**     | `enum (of string)` |
| **Required** | No                 |
| **Default**  | `"PET"`            |

Must be one of:
* "PET"

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_main_output_variable"></a>4.9.2.1.2.3.3. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > main_output_variable</strong>

</summary>
<blockquote>

**Title:** Main Output Variable

|              |                                      |
| ------------ | ------------------------------------ |
| **Type**     | `enum (of string)`                   |
| **Required** | No                                   |
| **Default**  | `"water_potential_evaporation_flux"` |

Must be one of:
* "water_potential_evaporation_flux"

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_init_config"></a>4.9.2.1.2.3.4. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > init_config</strong>

</summary>
<blockquote>

**Title:** Init Config

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `path`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_allow_exceed_end_time"></a>4.9.2.1.2.3.5. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > allow_exceed_end_time</strong>

</summary>
<blockquote>

**Title:** Allow Exceed End Time

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_fixed_time_step"></a>4.9.2.1.2.3.6. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > fixed_time_step</strong>

</summary>
<blockquote>

**Title:** Fixed Time Step

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `true`    |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_uses_forcing_file"></a>4.9.2.1.2.3.7. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > uses_forcing_file</strong>

</summary>
<blockquote>

**Title:** Uses Forcing File

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_variables_names_map"></a>4.9.2.1.2.3.8. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > variables_names_map</strong>

</summary>
<blockquote>

**Title:** Variables Names Map

|                           |                                                                                                                                                                                                                 |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                                                                        |
| **Required**              | No                                                                                                                                                                                                              |
| **Additional properties** | [[Should-conform]](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_variables_names_map_additionalProperties "Each additional property must conform to the following schema") |

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_variables_names_map_additionalProperties"></a>4.9.2.1.2.3.8.1. Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > variables_names_map > additionalProperties</strong>

</summary>
<blockquote>

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_output_variables"></a>4.9.2.1.2.3.9. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > output_variables</strong>

</summary>
<blockquote>

**Title:** Output Variables

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                     | Description |
| ----------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_variables items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_output_variables_items) | -           |

##### <a name="autogenerated_heading_8"></a>4.9.2.1.2.3.9.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > output_variables > output_variables items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_output_headers"></a>4.9.2.1.2.3.10. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > output_headers</strong>

</summary>
<blockquote>

**Title:** Output Headers

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                 | Description |
| ------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_headers items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_output_headers_items) | -           |

##### <a name="autogenerated_heading_9"></a>4.9.2.1.2.3.10.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > output_headers > output_headers items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_model_params"></a>4.9.2.1.2.3.11. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > model_params</strong>

</summary>
<blockquote>

**Title:** Model Params

|                           |                                                                                                                                                                                                          |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                                                                 |
| **Required**              | No                                                                                                                                                                                                       |
| **Additional properties** | [[Should-conform]](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_model_params_additionalProperties "Each additional property must conform to the following schema") |

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_model_params_additionalProperties"></a>4.9.2.1.2.3.11.1. Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > model_params > additionalProperties</strong>

</summary>
<blockquote>

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_library_file"></a>4.9.2.1.2.3.12. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > library_file</strong>

</summary>
<blockquote>

**Title:** Library File

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `path`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i2_registration_function"></a>4.9.2.1.2.3.13. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > PET > registration_function</strong>

</summary>
<blockquote>

**Title:** Registration Function

|              |                      |
| ------------ | -------------------- |
| **Type**     | `string`             |
| **Required** | No                   |
| **Default**  | `"register_bmi_pet"` |

</blockquote>
</details>

</blockquote>
<blockquote>

##### <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3"></a>4.9.2.1.2.4. Property `NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/NoahOWP                                                     |

**Description:** A BMIFortran implementation for a noahowp module

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_name"></a>4.9.2.1.2.4.1. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > name</strong>

</summary>
<blockquote>

**Title:** Name

|              |                 |
| ------------ | --------------- |
| **Type**     | `const`         |
| **Required** | No              |
| **Default**  | `"bmi_fortran"` |

Specific value: `"bmi_fortran"`

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_model_type_name"></a>4.9.2.1.2.4.2. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > model_type_name</strong>

</summary>
<blockquote>

**Title:** Model Type Name

|              |             |
| ------------ | ----------- |
| **Type**     | `const`     |
| **Required** | No          |
| **Default**  | `"NoahOWP"` |

Must be one of:
* "NoahOWP"
Specific value: `"NoahOWP"`

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_main_output_variable"></a>4.9.2.1.2.4.3. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > main_output_variable</strong>

</summary>
<blockquote>

**Title:** Main Output Variable

|              |            |
| ------------ | ---------- |
| **Type**     | `string`   |
| **Required** | No         |
| **Default**  | `"QINSUR"` |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_init_config"></a>4.9.2.1.2.4.4. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > init_config</strong>

</summary>
<blockquote>

**Title:** Init Config

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `path`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_allow_exceed_end_time"></a>4.9.2.1.2.4.5. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > allow_exceed_end_time</strong>

</summary>
<blockquote>

**Title:** Allow Exceed End Time

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_fixed_time_step"></a>4.9.2.1.2.4.6. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > fixed_time_step</strong>

</summary>
<blockquote>

**Title:** Fixed Time Step

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `true`    |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_uses_forcing_file"></a>4.9.2.1.2.4.7. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > uses_forcing_file</strong>

</summary>
<blockquote>

**Title:** Uses Forcing File

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_variables_names_map"></a>4.9.2.1.2.4.8. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > variables_names_map</strong>

</summary>
<blockquote>

**Title:** Variables Names Map

|                           |                                                                                                                                                                                                                 |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                                                                        |
| **Required**              | No                                                                                                                                                                                                              |
| **Additional properties** | [[Should-conform]](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_variables_names_map_additionalProperties "Each additional property must conform to the following schema") |

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_variables_names_map_additionalProperties"></a>4.9.2.1.2.4.8.1. Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > variables_names_map > additionalProperties</strong>

</summary>
<blockquote>

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_output_variables"></a>4.9.2.1.2.4.9. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > output_variables</strong>

</summary>
<blockquote>

**Title:** Output Variables

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                     | Description |
| ----------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_variables items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_output_variables_items) | -           |

##### <a name="autogenerated_heading_10"></a>4.9.2.1.2.4.9.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > output_variables > output_variables items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_output_headers"></a>4.9.2.1.2.4.10. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > output_headers</strong>

</summary>
<blockquote>

**Title:** Output Headers

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                 | Description |
| ------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_headers items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_output_headers_items) | -           |

##### <a name="autogenerated_heading_11"></a>4.9.2.1.2.4.10.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > output_headers > output_headers items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_model_params"></a>4.9.2.1.2.4.11. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > model_params</strong>

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/NoahOWPParams                                               |

**Description:** Class for validating NoahOWP Parameters

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i3_library_file"></a>4.9.2.1.2.4.12. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > NoahOWP > library_file</strong>

</summary>
<blockquote>

**Title:** Library File

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `path`   |

</blockquote>
</details>

</blockquote>
<blockquote>

##### <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4"></a>4.9.2.1.2.5. Property `NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/LSTM                                                        |

**Description:** A BMIPython implementation for an ngen LSTM module

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_name"></a>4.9.2.1.2.5.1. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > name</strong>

</summary>
<blockquote>

**Title:** Name

|              |                |
| ------------ | -------------- |
| **Type**     | `const`        |
| **Required** | No             |
| **Default**  | `"bmi_python"` |

Specific value: `"bmi_python"`

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_model_type_name"></a>4.9.2.1.2.5.2. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > model_type_name</strong>

</summary>
<blockquote>

**Title:** Model Type Name

|              |                    |
| ------------ | ------------------ |
| **Type**     | `enum (of string)` |
| **Required** | No                 |
| **Default**  | `"LSTM"`           |

Must be one of:
* "LSTM"

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_main_output_variable"></a>4.9.2.1.2.5.3. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > main_output_variable</strong>

</summary>
<blockquote>

**Title:** Main Output Variable

|              |                                      |
| ------------ | ------------------------------------ |
| **Type**     | `enum (of string)`                   |
| **Required** | No                                   |
| **Default**  | `"land_surface_water__runoff_depth"` |

Must be one of:
* "land_surface_water__runoff_depth"

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_init_config"></a>4.9.2.1.2.5.4. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > init_config</strong>

</summary>
<blockquote>

**Title:** Init Config

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `path`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_allow_exceed_end_time"></a>4.9.2.1.2.5.5. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > allow_exceed_end_time</strong>

</summary>
<blockquote>

**Title:** Allow Exceed End Time

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_fixed_time_step"></a>4.9.2.1.2.5.6. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > fixed_time_step</strong>

</summary>
<blockquote>

**Title:** Fixed Time Step

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `true`    |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_uses_forcing_file"></a>4.9.2.1.2.5.7. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > uses_forcing_file</strong>

</summary>
<blockquote>

**Title:** Uses Forcing File

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_variables_names_map"></a>4.9.2.1.2.5.8. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > variables_names_map</strong>

</summary>
<blockquote>

**Title:** Variables Names Map

|                           |                                                                                                                                                                                                                 |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                                                                        |
| **Required**              | No                                                                                                                                                                                                              |
| **Additional properties** | [[Should-conform]](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_variables_names_map_additionalProperties "Each additional property must conform to the following schema") |

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_variables_names_map_additionalProperties"></a>4.9.2.1.2.5.8.1. Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > variables_names_map > additionalProperties</strong>

</summary>
<blockquote>

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_output_variables"></a>4.9.2.1.2.5.9. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > output_variables</strong>

</summary>
<blockquote>

**Title:** Output Variables

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                     | Description |
| ----------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_variables items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_output_variables_items) | -           |

##### <a name="autogenerated_heading_12"></a>4.9.2.1.2.5.9.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > output_variables > output_variables items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_output_headers"></a>4.9.2.1.2.5.10. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > output_headers</strong>

</summary>
<blockquote>

**Title:** Output Headers

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                 | Description |
| ------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_headers items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_output_headers_items) | -           |

##### <a name="autogenerated_heading_13"></a>4.9.2.1.2.5.10.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > output_headers > output_headers items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_model_params"></a>4.9.2.1.2.5.11. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > model_params</strong>

</summary>
<blockquote>

**Title:** Model Params

|                           |                                                                                                                                                                                                          |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                                                                 |
| **Required**              | No                                                                                                                                                                                                       |
| **Additional properties** | [[Should-conform]](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_model_params_additionalProperties "Each additional property must conform to the following schema") |

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_model_params_additionalProperties"></a>4.9.2.1.2.5.11.1. Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > model_params > additionalProperties</strong>

</summary>
<blockquote>

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_python_type"></a>4.9.2.1.2.5.12. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > python_type</strong>

</summary>
<blockquote>

**Title:** Python Type

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `combining`                                                               |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Default**               | `"bmi_lstm.bmi_LSTM"`                                                     |

<blockquote>

| Any of(Option)                                                                                                    |
| ----------------------------------------------------------------------------------------------------------------- |
| [item 0](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_python_type_anyOf_i0) |
| [item 1](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_python_type_anyOf_i1) |

<blockquote>

##### <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_python_type_anyOf_i0"></a>4.9.2.1.2.5.12.1. Property `NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > python_type > anyOf > item 0`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
<blockquote>

##### <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i4_python_type_anyOf_i1"></a>4.9.2.1.2.5.12.2. Property `NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > LSTM > python_type > anyOf > item 1`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>

</blockquote>

</blockquote>
</details>

</blockquote>
<blockquote>

##### <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5"></a>4.9.2.1.2.6. Property `NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/SLOTH                                                       |

**Description:** A BMICXX implementation for the SLOTH ngen module

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_name"></a>4.9.2.1.2.6.1. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > name</strong>

</summary>
<blockquote>

**Title:** Name

|              |             |
| ------------ | ----------- |
| **Type**     | `const`     |
| **Required** | No          |
| **Default**  | `"bmi_c++"` |

Specific value: `"bmi_c++"`

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_model_type_name"></a>4.9.2.1.2.6.2. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > model_type_name</strong>

</summary>
<blockquote>

**Title:** Model Type Name

|              |           |
| ------------ | --------- |
| **Type**     | `const`   |
| **Required** | No        |
| **Default**  | `"SLOTH"` |

Must be one of:
* "SLOTH"
Specific value: `"SLOTH"`

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_main_output_variable"></a>4.9.2.1.2.6.3. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > main_output_variable</strong>

</summary>
<blockquote>

**Title:** Main Output Variable

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_init_config"></a>4.9.2.1.2.6.4. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > init_config</strong>

</summary>
<blockquote>

**Title:** Init Config

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `path`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_allow_exceed_end_time"></a>4.9.2.1.2.6.5. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > allow_exceed_end_time</strong>

</summary>
<blockquote>

**Title:** Allow Exceed End Time

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_fixed_time_step"></a>4.9.2.1.2.6.6. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > fixed_time_step</strong>

</summary>
<blockquote>

**Title:** Fixed Time Step

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `true`    |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_uses_forcing_file"></a>4.9.2.1.2.6.7. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > uses_forcing_file</strong>

</summary>
<blockquote>

**Title:** Uses Forcing File

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_variables_names_map"></a>4.9.2.1.2.6.8. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > variables_names_map</strong>

</summary>
<blockquote>

**Title:** Variables Names Map

|                           |                                                                                                                                                                                                                 |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                                                                        |
| **Required**              | No                                                                                                                                                                                                              |
| **Additional properties** | [[Should-conform]](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_variables_names_map_additionalProperties "Each additional property must conform to the following schema") |

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_variables_names_map_additionalProperties"></a>4.9.2.1.2.6.8.1. Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > variables_names_map > additionalProperties</strong>

</summary>
<blockquote>

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_output_variables"></a>4.9.2.1.2.6.9. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > output_variables</strong>

</summary>
<blockquote>

**Title:** Output Variables

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                     | Description |
| ----------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_variables items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_output_variables_items) | -           |

##### <a name="autogenerated_heading_14"></a>4.9.2.1.2.6.9.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > output_variables > output_variables items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_output_headers"></a>4.9.2.1.2.6.10. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > output_headers</strong>

</summary>
<blockquote>

**Title:** Output Headers

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                 | Description |
| ------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_headers items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_output_headers_items) | -           |

##### <a name="autogenerated_heading_15"></a>4.9.2.1.2.6.10.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > output_headers > output_headers items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_model_params"></a>4.9.2.1.2.6.11. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > model_params</strong>

</summary>
<blockquote>

**Title:** Model Params

|                           |                                                                                                                                                                                                          |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                                                                 |
| **Required**              | No                                                                                                                                                                                                       |
| **Additional properties** | [[Should-conform]](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_model_params_additionalProperties "Each additional property must conform to the following schema") |

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_model_params_additionalProperties"></a>4.9.2.1.2.6.11.1. Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > model_params > additionalProperties</strong>

</summary>
<blockquote>

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_library_file"></a>4.9.2.1.2.6.12. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > library_file</strong>

</summary>
<blockquote>

**Title:** Library File

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `path`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i5_registration_function"></a>4.9.2.1.2.6.13. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > SLOTH > registration_function</strong>

</summary>
<blockquote>

**Title:** Registration Function

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |
| **Default**  | `"none"` |

</blockquote>
</details>

</blockquote>
<blockquote>

##### <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6"></a>4.9.2.1.2.7. Property `NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/MultiBMI                                                    |

**Description:** A MultiBMI model definition
Implements and overrids several BMIParams attributes,
and includes a recursive Formulation list `modules`

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_name"></a>4.9.2.1.2.7.1. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > name</strong>

</summary>
<blockquote>

**Title:** Name

|              |               |
| ------------ | ------------- |
| **Type**     | `const`       |
| **Required** | No            |
| **Default**  | `"bmi_multi"` |

Specific value: `"bmi_multi"`

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_model_type_name"></a>4.9.2.1.2.7.2. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > model_type_name</strong>

</summary>
<blockquote>

**Title:** Model Type Name

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_main_output_variable"></a>4.9.2.1.2.7.3. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > main_output_variable</strong>

</summary>
<blockquote>

**Title:** Main Output Variable

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_init_config"></a>4.9.2.1.2.7.4. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > init_config</strong>

</summary>
<blockquote>

**Title:** Init Config

|              |         |
| ------------ | ------- |
| **Type**     | `const` |
| **Required** | No      |
| **Default**  | `""`    |

Specific value: `""`

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_allow_exceed_end_time"></a>4.9.2.1.2.7.5. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > allow_exceed_end_time</strong>

</summary>
<blockquote>

**Title:** Allow Exceed End Time

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_fixed_time_step"></a>4.9.2.1.2.7.6. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > fixed_time_step</strong>

</summary>
<blockquote>

**Title:** Fixed Time Step

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `true`    |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_uses_forcing_file"></a>4.9.2.1.2.7.7. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > uses_forcing_file</strong>

</summary>
<blockquote>

**Title:** Uses Forcing File

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_name_map"></a>4.9.2.1.2.7.8. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > name_map</strong>

</summary>
<blockquote>

**Title:** Name Map

|              |         |
| ------------ | ------- |
| **Type**     | `const` |
| **Required** | No      |

Specific value: `{
    "description": "😅 ERROR in schema generation, a referenced schema could not be loaded, no documentation here unfortunately 🏜️"
}`

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_name_map_additionalProperties"></a>4.9.2.1.2.7.8.1. Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > name_map > additionalProperties</strong>

</summary>
<blockquote>

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_output_variables"></a>4.9.2.1.2.7.9. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > output_variables</strong>

</summary>
<blockquote>

**Title:** Output Variables

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                     | Description |
| ----------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_variables items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_output_variables_items) | -           |

##### <a name="autogenerated_heading_16"></a>4.9.2.1.2.7.9.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > output_variables > output_variables items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_output_headers"></a>4.9.2.1.2.7.10. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > output_headers</strong>

</summary>
<blockquote>

**Title:** Output Headers

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of string` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                 | Description |
| ------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [output_headers items](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_output_headers_items) | -           |

##### <a name="autogenerated_heading_17"></a>4.9.2.1.2.7.10.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > output_headers > output_headers items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_model_params"></a>4.9.2.1.2.7.11. [Optional] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > model_params</strong>

</summary>
<blockquote>

**Title:** Model Params

|              |         |
| ------------ | ------- |
| **Type**     | `const` |
| **Required** | No      |

Specific value: `{
    "description": "😅 ERROR in schema generation, a referenced schema could not be loaded, no documentation here unfortunately 🏜️"
}`

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_model_params_additionalProperties"></a>4.9.2.1.2.7.11.1. Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > model_params > additionalProperties</strong>

</summary>
<blockquote>

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_modules"></a>4.9.2.1.2.7.12. [Required] Property NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > modules</strong>

</summary>
<blockquote>

**Title:** Modules

|              |         |
| ------------ | ------- |
| **Type**     | `array` |
| **Required** | Yes     |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                 | Description                       |
| --------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| [Formulation](#request_body_partial_realization_config_global_formulations_items_params_anyOf_i6_modules_items) | Model of an ngen formulation. ... |

##### <a name="autogenerated_heading_18"></a>4.9.2.1.2.7.12.1. NGENRequest > request_body > partial_realization_config > global_formulations > Formulation > params > anyOf > MultiBMI > modules > Formulation

|                           |                                                                                   |
| ------------------------- | --------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                          |
| **Required**              | No                                                                                |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.")         |
| **Same definition as**    | [Formulation](#request_body_partial_realization_config_global_formulations_items) |

**Description:** Model of an ngen formulation.

Note, during object creation if the `params` field is deserialized (e.g. `params`'s value is a
dictionary), the `name` field is required. If `name` *is not* 'bmi_multi', the `model_type_name`
field is also required. Neither are required if a concrete known formulation instance is
provided.

</blockquote>
</details>

</blockquote>

</blockquote>

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_catchment_formulations"></a>4.9.3. [Optional] Property NGENRequest > request_body > partial_realization_config > catchment_formulations</strong>

</summary>
<blockquote>

**Title:** Catchment Formulations

|                           |                                                                                                                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Type**                  | `object`                                                                                                                                                                 |
| **Required**              | No                                                                                                                                                                       |
| **Additional properties** | [[Should-conform]](#request_body_partial_realization_config_catchment_formulations_additionalProperties "Each additional property must conform to the following schema") |

<details>
<summary><strong> <a name="request_body_partial_realization_config_catchment_formulations_additionalProperties"></a>4.9.3.1. Property NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization</strong>

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/CatchmentRealization                                        |

**Description:** Simple model of a Realization, containing formulations and forcing

<details>
<summary><strong> <a name="request_body_partial_realization_config_catchment_formulations_additionalProperties_formulations"></a>4.9.3.1.1. [Required] Property NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > formulations</strong>

</summary>
<blockquote>

**Title:** Formulations

|              |         |
| ------------ | ------- |
| **Type**     | `array` |
| **Required** | Yes     |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                        | Description                       |
| ---------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| [Formulation](#request_body_partial_realization_config_catchment_formulations_additionalProperties_formulations_items) | Model of an ngen formulation. ... |

##### <a name="autogenerated_heading_19"></a>4.9.3.1.1.1. NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > formulations > Formulation

|                           |                                                                                   |
| ------------------------- | --------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                          |
| **Required**              | No                                                                                |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.")         |
| **Same definition as**    | [Formulation](#request_body_partial_realization_config_global_formulations_items) |

**Description:** Model of an ngen formulation.

Note, during object creation if the `params` field is deserialized (e.g. `params`'s value is a
dictionary), the `name` field is required. If `name` *is not* 'bmi_multi', the `model_type_name`
field is also required. Neither are required if a concrete known formulation instance is
provided.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_catchment_formulations_additionalProperties_forcing"></a>4.9.3.1.2. [Optional] Property NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > forcing</strong>

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/Forcing                                                     |

**Description:** Model for ngen forcing component inputs

<details>
<summary><strong> <a name="request_body_partial_realization_config_catchment_formulations_additionalProperties_forcing_file_pattern"></a>4.9.3.1.2.1. [Optional] Property NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > forcing > file_pattern</strong>

</summary>
<blockquote>

**Title:** File Pattern

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `combining`                                                               |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

<blockquote>

| Any of(Option)                                                                                                               |
| ---------------------------------------------------------------------------------------------------------------------------- |
| [item 0](#request_body_partial_realization_config_catchment_formulations_additionalProperties_forcing_file_pattern_anyOf_i0) |
| [item 1](#request_body_partial_realization_config_catchment_formulations_additionalProperties_forcing_file_pattern_anyOf_i1) |

<blockquote>

##### <a name="request_body_partial_realization_config_catchment_formulations_additionalProperties_forcing_file_pattern_anyOf_i0"></a>4.9.3.1.2.1.1. Property `NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > forcing > file_pattern > anyOf > item 0`

|              |             |
| ------------ | ----------- |
| **Type**     | `string`    |
| **Required** | No          |
| **Format**   | `file-path` |

</blockquote>
<blockquote>

##### <a name="request_body_partial_realization_config_catchment_formulations_additionalProperties_forcing_file_pattern_anyOf_i1"></a>4.9.3.1.2.1.2. Property `NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > forcing > file_pattern > anyOf > item 1`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>

</blockquote>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_catchment_formulations_additionalProperties_forcing_path"></a>4.9.3.1.2.2. [Required] Property NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > forcing > path</strong>

</summary>
<blockquote>

**Title:** Path

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `combining`                                                               |
| **Required**              | Yes                                                                       |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

<blockquote>

| Any of(Option)                                                                                                       |
| -------------------------------------------------------------------------------------------------------------------- |
| [item 0](#request_body_partial_realization_config_catchment_formulations_additionalProperties_forcing_path_anyOf_i0) |
| [item 1](#request_body_partial_realization_config_catchment_formulations_additionalProperties_forcing_path_anyOf_i1) |

<blockquote>

##### <a name="request_body_partial_realization_config_catchment_formulations_additionalProperties_forcing_path_anyOf_i0"></a>4.9.3.1.2.2.1. Property `NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > forcing > path > anyOf > item 0`

|              |                  |
| ------------ | ---------------- |
| **Type**     | `string`         |
| **Required** | No               |
| **Format**   | `directory-path` |

</blockquote>
<blockquote>

##### <a name="request_body_partial_realization_config_catchment_formulations_additionalProperties_forcing_path_anyOf_i1"></a>4.9.3.1.2.2.2. Property `NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > forcing > path > anyOf > item 1`

|              |             |
| ------------ | ----------- |
| **Type**     | `string`    |
| **Required** | No          |
| **Format**   | `file-path` |

</blockquote>

</blockquote>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_catchment_formulations_additionalProperties_forcing_provider"></a>4.9.3.1.2.3. [Optional] Property NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > forcing > provider</strong>

</summary>
<blockquote>

|                |                    |
| -------------- | ------------------ |
| **Type**       | `enum (of string)` |
| **Required**   | No                 |
| **Default**    | `"CsvPerFeature"`  |
| **Defined in** |                    |

**Description:** Enumeration of the supported NGEN forcing provider strings

Must be one of:
* "CsvPerFeature"
* "NetCDF"

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_catchment_formulations_additionalProperties_calibration"></a>4.9.3.1.3. [Optional] Property NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > calibration</strong>

</summary>
<blockquote>

**Title:** Calibration

|                           |                                                                                                                                                                                                           |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                                                                  |
| **Required**              | No                                                                                                                                                                                                        |
| **Additional properties** | [[Should-conform]](#request_body_partial_realization_config_catchment_formulations_additionalProperties_calibration_additionalProperties "Each additional property must conform to the following schema") |

<details>
<summary><strong> <a name="request_body_partial_realization_config_catchment_formulations_additionalProperties_calibration_additionalProperties"></a>4.9.3.1.3.1. Property NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > calibration > additionalProperties</strong>

</summary>
<blockquote>

|              |         |
| ------------ | ------- |
| **Type**     | `array` |
| **Required** | No      |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                                                           | Description |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| [additionalProperties items](#request_body_partial_realization_config_catchment_formulations_additionalProperties_calibration_additionalProperties_items) | -           |

##### <a name="autogenerated_heading_20"></a>4.9.3.1.3.1.1. NGENRequest > request_body > partial_realization_config > catchment_formulations > CatchmentRealization > calibration > additionalProperties > additionalProperties items

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

</blockquote>
</details>

</blockquote>
</details>

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_forcing_file_pattern"></a>4.9.4. [Optional] Property NGENRequest > request_body > partial_realization_config > forcing_file_pattern</strong>

</summary>
<blockquote>

**Title:** Forcing File Pattern

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_forcing_file_name"></a>4.9.5. [Optional] Property NGENRequest > request_body > partial_realization_config > forcing_file_name</strong>

</summary>
<blockquote>

**Title:** Forcing File Name

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_routing_config"></a>4.9.6. [Optional] Property NGENRequest > request_body > partial_realization_config > routing_config</strong>

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/Routing                                                     |

**Description:** Model for ngen routing configuration information

<details>
<summary><strong> <a name="request_body_partial_realization_config_routing_config_t_route_config_file_with_path"></a>4.9.6.1. [Required] Property NGENRequest > request_body > partial_realization_config > routing_config > t_route_config_file_with_path</strong>

</summary>
<blockquote>

**Title:** T Route Config File With Path

|              |             |
| ------------ | ----------- |
| **Type**     | `string`    |
| **Required** | Yes         |
| **Format**   | `file-path` |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_routing_config_t_route_connection_path"></a>4.9.6.2. [Optional] Property NGENRequest > request_body > partial_realization_config > routing_config > t_route_connection_path</strong>

</summary>
<blockquote>

**Title:** T Route Connection Path

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |
| **Default**  | `""`     |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partial_realization_config_is_env_workaround"></a>4.9.7. [Optional] Property NGENRequest > request_body > partial_realization_config > is_env_workaround</strong>

</summary>
<blockquote>

**Title:** Is Env Workaround

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_partition_config_data_id"></a>4.10. [Optional] Property NGENRequest > request_body > partition_config_data_id</strong>

</summary>
<blockquote>

**Title:** Partition Config Data Id

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** Partition config dataset, when multi-process job.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_t_route_config_data_id"></a>4.11. [Optional] Property NGENRequest > request_body > t_route_config_data_id</strong>

</summary>
<blockquote>

**Title:** T Route Config Data Id

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** Id of composite source of t-route config.

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="session_secret"></a>5. [Required] Property NGENRequest > session_secret</strong>

</summary>
<blockquote>

**Title:** Session Secret

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

</blockquote>
</details>

----------------------------------------------------------------------------------------------------------------------------
