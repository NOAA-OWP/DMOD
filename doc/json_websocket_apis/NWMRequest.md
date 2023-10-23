# NWMRequest

**Title:** NWMRequest

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
<summary><strong> <a name="job_type"></a>1. [Optional] Property NWMRequest > job_type</strong>  

</summary>
<blockquote>

**Title:** Job Type

|              |                    |
| ------------ | ------------------ |
| **Type**     | `enum (of string)` |
| **Required** | No                 |
| **Default**  | `"nwm"`            |

Must be one of:
* "nwm"

</blockquote>
</details>

<details>
<summary><strong> <a name="cpu_count"></a>2. [Optional] Property NWMRequest > cpu_count</strong>  

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
<summary><strong> <a name="allocation_paradigm"></a>3. [Optional] Property NWMRequest > allocation_paradigm</strong>  

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
<summary><strong> <a name="session_secret"></a>4. [Required] Property NWMRequest > session_secret</strong>  

</summary>
<blockquote>

**Title:** Session Secret

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body"></a>5. [Required] Property NWMRequest > request_body</strong>  

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | Yes                                                                       |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/NWMRequestBody                                              |

**Description:** An interface class for an object that can be serialized to a dictionary-like format (i.e., potentially a JSON
object) and JSON string format based directly from dumping the aforementioned dictionary-like representation.

Subtypes of `Serializable` should specify their fields following
[`pydantic.BaseModel`](https://docs.pydantic.dev/usage/models/) semantics (see example below).
Notably, `to_dict` and `to_json` will exclude `None` fields and serialize fields using any
provided aliases (i.e.  `pydantic.Field(alias="some_alias")`). Also, enum subtypes are
serialized using their member `name` property.

Objects of this type will also used the JSON string format as their default string representation.

While not strictly enforced (because this probably isn't possible), it is HIGHLY recommended that instance
attribute members of implemented sub-types be of types that are either convertible to strings using the ``str()``
built-in, or are themselves also implementations of ::class:`Serializable`.  The convenience class method
::method:`serialize` will handle serializing any such member objects appropriately, providing a clean interface for
this.

An exception to the aforementioned recommendation is the ::class:`datetime.datetime` type.  Subtype attributes of
::class:`datetime.datetime` type should be parsed and serialized using the pattern returned by the
::method:`get_datetime_str_format` class method.  A reasonable default is provided in the base interface class, but
the pattern can be adjusted either by overriding the class method directly or by having a subtypes set/override
its ::attribute:`_SERIAL_DATETIME_STR_FORMAT` class attribute.  Note that the actual parsing/serialization logic is
left entirely to the subtypes, as many will not need it (and thus should not have to worry about implement another
method or have their superclass bloated by importing the ``datetime`` package).

Example:
```
# specify field as class variable, specify final type using type hint.
# pydantic will try to coerce a field into the specified type, if it can't, a
# `pydantic.ValidationError` is raised.

class User(Serializable):
    id: int
    username: str
    email: str # more appropriately, `pydantic.EmailStr`

>>> user = User(id=1, username="uncle_sam", email="uncle_sam@fake.gov")
>>> user.to_dict() # {"id": 1, "username": "uncle_sam", "email": "uncle_sam@fake.gov"}
>>> user.to_json() # '{"id": 1, "username": "uncle_sam", "email": "uncle_sam@fake.gov"}'
```

<details>
<summary><strong> <a name="request_body_nwm"></a>5.1. [Required] Property NWMRequest > request_body > nwm</strong>  

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | Yes                                                                       |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/NWMInnerRequestBody                                         |

**Description:** An interface class for an object that can be serialized to a dictionary-like format (i.e., potentially a JSON
object) and JSON string format based directly from dumping the aforementioned dictionary-like representation.

Subtypes of `Serializable` should specify their fields following
[`pydantic.BaseModel`](https://docs.pydantic.dev/usage/models/) semantics (see example below).
Notably, `to_dict` and `to_json` will exclude `None` fields and serialize fields using any
provided aliases (i.e.  `pydantic.Field(alias="some_alias")`). Also, enum subtypes are
serialized using their member `name` property.

Objects of this type will also used the JSON string format as their default string representation.

While not strictly enforced (because this probably isn't possible), it is HIGHLY recommended that instance
attribute members of implemented sub-types be of types that are either convertible to strings using the ``str()``
built-in, or are themselves also implementations of ::class:`Serializable`.  The convenience class method
::method:`serialize` will handle serializing any such member objects appropriately, providing a clean interface for
this.

An exception to the aforementioned recommendation is the ::class:`datetime.datetime` type.  Subtype attributes of
::class:`datetime.datetime` type should be parsed and serialized using the pattern returned by the
::method:`get_datetime_str_format` class method.  A reasonable default is provided in the base interface class, but
the pattern can be adjusted either by overriding the class method directly or by having a subtypes set/override
its ::attribute:`_SERIAL_DATETIME_STR_FORMAT` class attribute.  Note that the actual parsing/serialization logic is
left entirely to the subtypes, as many will not need it (and thus should not have to worry about implement another
method or have their superclass bloated by importing the ``datetime`` package).

Example:
```
# specify field as class variable, specify final type using type hint.
# pydantic will try to coerce a field into the specified type, if it can't, a
# `pydantic.ValidationError` is raised.

class User(Serializable):
    id: int
    username: str
    email: str # more appropriately, `pydantic.EmailStr`

>>> user = User(id=1, username="uncle_sam", email="uncle_sam@fake.gov")
>>> user.to_dict() # {"id": 1, "username": "uncle_sam", "email": "uncle_sam@fake.gov"}
>>> user.to_json() # '{"id": 1, "username": "uncle_sam", "email": "uncle_sam@fake.gov"}'
```

<details>
<summary><strong> <a name="request_body_nwm_name"></a>5.1.1. [Optional] Property NWMRequest > request_body > nwm > name</strong>  

</summary>
<blockquote>

**Title:** Name

|              |                    |
| ------------ | ------------------ |
| **Type**     | `enum (of string)` |
| **Required** | No                 |
| **Default**  | `"nwm"`            |

Must be one of:
* "nwm"

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_nwm_config_data_id"></a>5.1.2. [Required] Property NWMRequest > request_body > nwm > config_data_id</strong>  

</summary>
<blockquote>

**Title:** Config Data Id

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** Unique id of the config dataset for this request.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_nwm_data_requirements"></a>5.1.3. [Optional] Property NWMRequest > request_body > nwm > data_requirements</strong>  

</summary>
<blockquote>

**Title:** Data Requirements

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

| Each item of this array must be                              | Description                                                                 |
| ------------------------------------------------------------ | --------------------------------------------------------------------------- |
| [DataRequirement](#request_body_nwm_data_requirements_items) | A definition of a particular data requirement needed for an execution task. |

##### <a name="autogenerated_heading_2"></a>5.1.3.1. NWMRequest > request_body > nwm > data_requirements > DataRequirement

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/DataRequirement                                             |

**Description:** A definition of a particular data requirement needed for an execution task.

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_category"></a>5.1.3.1.1. [Required] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > category</strong>  

</summary>
<blockquote>

|                |                            |
| -------------- | -------------------------- |
| **Type**       | `enum (of string)`         |
| **Required**   | Yes                        |
| **Defined in** | #/definitions/DataCategory |

**Description:** The general category values for different data.

Must be one of:
* "CONFIG"
* "FORCING"
* "HYDROFABRIC"
* "OBSERVATION"
* "OUTPUT"

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain"></a>5.1.3.1.2. [Required] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain</strong>  

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | Yes                                                                       |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/DataDomain                                                  |

**Description:** A domain for a dataset, with domain-defining values contained by one or more discrete and/or continuous components.

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_data_format"></a>5.1.3.1.2.1. [Required] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > data_format</strong>  

</summary>
<blockquote>

|                |                    |
| -------------- | ------------------ |
| **Type**       | `enum (of string)` |
| **Required**   | Yes                |
| **Defined in** |                    |

**Description:** The format for the data in this domain, which contains details like the indices and other data fields.

Must be one of:
* "AORC_CSV"
* "NETCDF_FORCING_CANONICAL"
* "NETCDF_AORC_DEFAULT"
* "NGEN_OUTPUT"
* "NGEN_REALIZATION_CONFIG"
* "NGEN_GEOJSON_HYDROFABRIC"
* "NGEN_PARTITION_CONFIG"
* "BMI_CONFIG"
* "NWM_OUTPUT"
* "NWM_CONFIG"
* "NGEN_CAL_OUTPUT"
* "NGEN_CAL_CONFIG"
* "NGEN_JOB_COMPOSITE_CONFIG"
* "T_ROUTE_CONFIG"

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_continuous"></a>5.1.3.1.2.2. [Optional] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > continuous</strong>  

</summary>
<blockquote>

**Title:** Continuous

|                           |                                                                                                                                                                      |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                             |
| **Required**              | No                                                                                                                                                                   |
| **Additional properties** | [[Should-conform]](#request_body_nwm_data_requirements_items_domain_continuous_additionalProperties "Each additional property must conform to the following schema") |

**Description:** Map of the continuous restrictions defining this domain, keyed by variable name.

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_continuous_additionalProperties"></a>5.1.3.1.2.2.1. Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > continuous > ContinuousRestriction</strong>  

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/ContinuousRestriction                                       |

**Description:** A filtering component, typically applied as a restriction on a domain, by a continuous range of values of a variable.

If a subclass name is passed to the optional ``subclass`` parameter during initialization the subclass will be
initialized and returned. For example, `ContinuousRestriction(..., subclass="TimeRange")` would return a
``TimeRange`` instance. Invalid ``subclass`` parameter values will return an``ContinuousRestriction`` instance and
display a RuntimeWarning.

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_continuous_additionalProperties_variable"></a>5.1.3.1.2.2.1.1. [Required] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > continuous > ContinuousRestriction > variable</strong>  

</summary>
<blockquote>

|                |                                    |
| -------------- | ---------------------------------- |
| **Type**       | `enum (of string)`                 |
| **Required**   | Yes                                |
| **Defined in** | #/definitions/StandardDatasetIndex |

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
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_continuous_additionalProperties_begin"></a>5.1.3.1.2.2.1.2. [Required] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > continuous > ContinuousRestriction > begin</strong>  

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
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_continuous_additionalProperties_end"></a>5.1.3.1.2.2.1.3. [Required] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > continuous > ContinuousRestriction > end</strong>  

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
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_continuous_additionalProperties_datetime_pattern"></a>5.1.3.1.2.2.1.4. [Optional] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > continuous > ContinuousRestriction > datetime_pattern</strong>  

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
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_continuous_additionalProperties_subclass"></a>5.1.3.1.2.2.1.5. [Optional] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > continuous > ContinuousRestriction > subclass</strong>  

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

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_discrete"></a>5.1.3.1.2.3. [Optional] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > discrete</strong>  

</summary>
<blockquote>

**Title:** Discrete

|                           |                                                                                                                                                                    |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Type**                  | `object`                                                                                                                                                           |
| **Required**              | No                                                                                                                                                                 |
| **Additional properties** | [[Should-conform]](#request_body_nwm_data_requirements_items_domain_discrete_additionalProperties "Each additional property must conform to the following schema") |

**Description:** Map of the discrete restrictions defining this domain, keyed by variable name.

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_discrete_additionalProperties"></a>5.1.3.1.2.3.1. Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > discrete > DiscreteRestriction</strong>  

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/DiscreteRestriction                                         |

**Description:** A filtering component, typically applied as a restriction on a domain, by a discrete set of values of a variable.

Note that an empty list for the ::attribute:`values` property implies a restriction of all possible values being
required.  This is reflected by the :method:`is_all_possible_values` property.

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_discrete_additionalProperties_variable"></a>5.1.3.1.2.3.1.1. [Required] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > discrete > DiscreteRestriction > variable</strong>  

</summary>
<blockquote>

|                        |                                                                                                       |
| ---------------------- | ----------------------------------------------------------------------------------------------------- |
| **Type**               | `enum (of string)`                                                                                    |
| **Required**           | Yes                                                                                                   |
| **Same definition as** | [variable](#request_body_nwm_data_requirements_items_domain_continuous_additionalProperties_variable) |

**Description:** An enumeration.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_discrete_additionalProperties_values"></a>5.1.3.1.2.3.1.2. [Required] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > discrete > DiscreteRestriction > values</strong>  

</summary>
<blockquote>

**Title:** Values

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `combining`                                                               |
| **Required**              | Yes                                                                       |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

<blockquote>

| Any of(Option)                                                                                           |
| -------------------------------------------------------------------------------------------------------- |
| [item 0](#request_body_nwm_data_requirements_items_domain_discrete_additionalProperties_values_anyOf_i0) |
| [item 1](#request_body_nwm_data_requirements_items_domain_discrete_additionalProperties_values_anyOf_i1) |
| [item 2](#request_body_nwm_data_requirements_items_domain_discrete_additionalProperties_values_anyOf_i2) |

<blockquote>

##### <a name="request_body_nwm_data_requirements_items_domain_discrete_additionalProperties_values_anyOf_i0"></a>5.1.3.1.2.3.1.2.1. Property `NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > discrete > DiscreteRestriction > values > anyOf > item 0`

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

| Each item of this array must be                                                                                      | Description |
| -------------------------------------------------------------------------------------------------------------------- | ----------- |
| [item 0 items](#request_body_nwm_data_requirements_items_domain_discrete_additionalProperties_values_anyOf_i0_items) | -           |

##### <a name="autogenerated_heading_3"></a>5.1.3.1.2.3.1.2.1.1. NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > discrete > DiscreteRestriction > values > anyOf > item 0 > item 0 items

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
<blockquote>

##### <a name="request_body_nwm_data_requirements_items_domain_discrete_additionalProperties_values_anyOf_i1"></a>5.1.3.1.2.3.1.2.2. Property `NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > discrete > DiscreteRestriction > values > anyOf > item 1`

|              |                   |
| ------------ | ----------------- |
| **Type**     | `array of number` |
| **Required** | No                |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                      | Description |
| -------------------------------------------------------------------------------------------------------------------- | ----------- |
| [item 1 items](#request_body_nwm_data_requirements_items_domain_discrete_additionalProperties_values_anyOf_i1_items) | -           |

##### <a name="autogenerated_heading_4"></a>5.1.3.1.2.3.1.2.2.1. NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > discrete > DiscreteRestriction > values > anyOf > item 1 > item 1 items

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
<blockquote>

##### <a name="request_body_nwm_data_requirements_items_domain_discrete_additionalProperties_values_anyOf_i2"></a>5.1.3.1.2.3.1.2.3. Property `NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > discrete > DiscreteRestriction > values > anyOf > item 2`

|              |                    |
| ------------ | ------------------ |
| **Type**     | `array of integer` |
| **Required** | No                 |

|                      | Array restrictions |
| -------------------- | ------------------ |
| **Min items**        | N/A                |
| **Max items**        | N/A                |
| **Items unicity**    | False              |
| **Additional items** | False              |
| **Tuple validation** | See below          |

| Each item of this array must be                                                                                      | Description |
| -------------------------------------------------------------------------------------------------------------------- | ----------- |
| [item 2 items](#request_body_nwm_data_requirements_items_domain_discrete_additionalProperties_values_anyOf_i2_items) | -           |

##### <a name="autogenerated_heading_5"></a>5.1.3.1.2.3.1.2.3.1. NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > discrete > DiscreteRestriction > values > anyOf > item 2 > item 2 items

|              |           |
| ------------ | --------- |
| **Type**     | `integer` |
| **Required** | No        |

</blockquote>

</blockquote>

</blockquote>
</details>

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_data_fields"></a>5.1.3.1.2.4. [Optional] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > data_fields</strong>  

</summary>
<blockquote>

**Title:** Data Fields

|                           |                                                                                                                                                                       |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                              |
| **Required**              | No                                                                                                                                                                    |
| **Additional properties** | [[Should-conform]](#request_body_nwm_data_requirements_items_domain_data_fields_additionalProperties "Each additional property must conform to the following schema") |

**Description:** This will either be directly from the format, if its format specifies any fields, or from a custom fieldsattribute that may be set during initialization (but is ignored when the format specifies fields).

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_domain_data_fields_additionalProperties"></a>5.1.3.1.2.4.1. Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > data_fields > additionalProperties</strong>  

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `combining`                                                               |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

<blockquote>

| Any of(Option)                                                                                       |
| ---------------------------------------------------------------------------------------------------- |
| [item 0](#request_body_nwm_data_requirements_items_domain_data_fields_additionalProperties_anyOf_i0) |
| [item 1](#request_body_nwm_data_requirements_items_domain_data_fields_additionalProperties_anyOf_i1) |
| [item 2](#request_body_nwm_data_requirements_items_domain_data_fields_additionalProperties_anyOf_i2) |
| [item 3](#request_body_nwm_data_requirements_items_domain_data_fields_additionalProperties_anyOf_i3) |

<blockquote>

##### <a name="request_body_nwm_data_requirements_items_domain_data_fields_additionalProperties_anyOf_i0"></a>5.1.3.1.2.4.1.1. Property `NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > data_fields > additionalProperties > anyOf > item 0`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
<blockquote>

##### <a name="request_body_nwm_data_requirements_items_domain_data_fields_additionalProperties_anyOf_i1"></a>5.1.3.1.2.4.1.2. Property `NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > data_fields > additionalProperties > anyOf > item 1`

|              |           |
| ------------ | --------- |
| **Type**     | `integer` |
| **Required** | No        |

</blockquote>
<blockquote>

##### <a name="request_body_nwm_data_requirements_items_domain_data_fields_additionalProperties_anyOf_i2"></a>5.1.3.1.2.4.1.3. Property `NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > data_fields > additionalProperties > anyOf > item 2`

|              |          |
| ------------ | -------- |
| **Type**     | `number` |
| **Required** | No       |

</blockquote>
<blockquote>

##### <a name="request_body_nwm_data_requirements_items_domain_data_fields_additionalProperties_anyOf_i3"></a>5.1.3.1.2.4.1.4. Property `NWMRequest > request_body > nwm > data_requirements > DataRequirement > domain > data_fields > additionalProperties > anyOf > item 3`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

</blockquote>

</blockquote>

</blockquote>
</details>

</blockquote>
</details>

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_fulfilled_access_at"></a>5.1.3.1.3. [Optional] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > fulfilled_access_at</strong>  

</summary>
<blockquote>

**Title:** Fulfilled Access At

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** The location at which the fulfilling dataset for this requirement is accessible, if the dataset known.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_fulfilled_by"></a>5.1.3.1.4. [Optional] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > fulfilled_by</strong>  

</summary>
<blockquote>

**Title:** Fulfilled By

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** The name of the dataset that will fulfill this, if it is known.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_is_input"></a>5.1.3.1.5. [Required] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > is_input</strong>  

</summary>
<blockquote>

**Title:** Is Input

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | Yes       |

**Description:** Whether this represents required input data, as opposed to a requirement for storing output data.

</blockquote>
</details>

<details>
<summary><strong> <a name="request_body_nwm_data_requirements_items_size"></a>5.1.3.1.6. [Optional] Property NWMRequest > request_body > nwm > data_requirements > DataRequirement > size</strong>  

</summary>
<blockquote>

**Title:** Size

|              |           |
| ------------ | --------- |
| **Type**     | `integer` |
| **Required** | No        |

</blockquote>
</details>

</blockquote>
</details>

</blockquote>
</details>

</blockquote>
</details>

----------------------------------------------------------------------------------------------------------------------------
