# NgenCalibrationResponse

**Title:** NgenCalibrationResponse

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

**Description:** Class representing a response to some ::class:`Message`, typically a ::class:`AbstractInitRequest` sub-type.

Parameters
----------
success : bool
    Was the purpose encapsulated by the corresponding message fulfilled; e.g., to perform a task or transfer info
reason : str
    A summary of what the response conveys; e.g., request action trigger or disallowed
message : str
    A more detailed explanation of what the response conveys
data : Union[dict, Serializeable, None]
    Subtype-specific serialized data that should be conveyed as a result of the initial message

Attributes
----------
success : bool
    Was the purpose encapsulated by the corresponding message fulfilled; e.g., to perform a task or transfer info
reason : str
    A summary of what the response conveys; e.g., request action trigger or disallowed
message : str
    A more detailed explanation of what the response conveys
data : Union[dict, Serializeable, None]
    Subtype-specific serialized data that should be conveyed as a result of the initial message

<details>
<summary><strong> <a name="success"></a>1. [Required] Property NgenCalibrationResponse > success</strong>  

</summary>
<blockquote>

**Title:** Success

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | Yes       |

**Description:** Whether this indicates a successful result.

</blockquote>
</details>

<details>
<summary><strong> <a name="reason"></a>2. [Required] Property NgenCalibrationResponse > reason</strong>  

</summary>
<blockquote>

**Title:** Reason

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** A very short, high-level summary of the result.

</blockquote>
</details>

<details>
<summary><strong> <a name="message"></a>3. [Optional] Property NgenCalibrationResponse > message</strong>  

</summary>
<blockquote>

**Title:** Message

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |
| **Default**  | `""`     |

**Description:** An optional, more detailed explanation of the result, which by default is an empty string.

</blockquote>
</details>

<details>
<summary><strong> <a name="data"></a>4. [Optional] Property NgenCalibrationResponse > data</strong>  

</summary>
<blockquote>

**Title:** Data

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `combining`                                                               |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

<blockquote>

| Any of(Option)                                 |
| ---------------------------------------------- |
| [ModelExecRequestResponseBody](#data_anyOf_i0) |
| [item 1](#data_anyOf_i1)                       |

<blockquote>

### <a name="data_anyOf_i0"></a>4.1. Property `NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/ModelExecRequestResponseBody                                |

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
<summary><strong> <a name="data_anyOf_i0_job_id"></a>4.1.1. [Optional] Property NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody > job_id</strong>  

</summary>
<blockquote>

**Title:** Job Id

|              |           |
| ------------ | --------- |
| **Type**     | `integer` |
| **Required** | No        |
| **Default**  | `-1`      |

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i0_output_data_id"></a>4.1.2. [Optional] Property NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody > output_data_id</strong>  

</summary>
<blockquote>

**Title:** Output Data Id

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i0_scheduler_response"></a>4.1.3. [Required] Property NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody > scheduler_response</strong>  

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | Yes                                                                       |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/SchedulerRequestResponse                                    |

**Description:** Class representing a response to some ::class:`Message`, typically a ::class:`AbstractInitRequest` sub-type.

Parameters
----------
success : bool
    Was the purpose encapsulated by the corresponding message fulfilled; e.g., to perform a task or transfer info
reason : str
    A summary of what the response conveys; e.g., request action trigger or disallowed
message : str
    A more detailed explanation of what the response conveys
data : Union[dict, Serializeable, None]
    Subtype-specific serialized data that should be conveyed as a result of the initial message

Attributes
----------
success : bool
    Was the purpose encapsulated by the corresponding message fulfilled; e.g., to perform a task or transfer info
reason : str
    A summary of what the response conveys; e.g., request action trigger or disallowed
message : str
    A more detailed explanation of what the response conveys
data : Union[dict, Serializeable, None]
    Subtype-specific serialized data that should be conveyed as a result of the initial message

<details>
<summary><strong> <a name="data_anyOf_i0_scheduler_response_success"></a>4.1.3.1. [Required] Property NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody > scheduler_response > success</strong>  

</summary>
<blockquote>

**Title:** Success

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | Yes       |

**Description:** Whether this indicates a successful result.

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i0_scheduler_response_reason"></a>4.1.3.2. [Required] Property NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody > scheduler_response > reason</strong>  

</summary>
<blockquote>

**Title:** Reason

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** A very short, high-level summary of the result.

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i0_scheduler_response_message"></a>4.1.3.3. [Optional] Property NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody > scheduler_response > message</strong>  

</summary>
<blockquote>

**Title:** Message

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |
| **Default**  | `""`     |

**Description:** An optional, more detailed explanation of the result, which by default is an empty string.

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i0_scheduler_response_data"></a>4.1.3.4. [Optional] Property NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody > scheduler_response > data</strong>  

</summary>
<blockquote>

**Title:** Data

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `combining`                                                               |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

<blockquote>

| Any of(Option)                                                                  |
| ------------------------------------------------------------------------------- |
| [SchedulerRequestResponseBody](#data_anyOf_i0_scheduler_response_data_anyOf_i0) |
| [item 1](#data_anyOf_i0_scheduler_response_data_anyOf_i1)                       |

<blockquote>

##### <a name="data_anyOf_i0_scheduler_response_data_anyOf_i0"></a>4.1.3.4.1. Property `NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody > scheduler_response > data > anyOf > SchedulerRequestResponseBody`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/SchedulerRequestResponseBody                                |

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
<summary><strong> <a name="data_anyOf_i0_scheduler_response_data_anyOf_i0_job_id"></a>4.1.3.4.1.1. [Optional] Property NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody > scheduler_response > data > anyOf > SchedulerRequestResponseBody > job_id</strong>  

</summary>
<blockquote>

**Title:** Job Id

|              |           |
| ------------ | --------- |
| **Type**     | `integer` |
| **Required** | No        |
| **Default**  | `-1`      |

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i0_scheduler_response_data_anyOf_i0_output_data_id"></a>4.1.3.4.1.2. [Optional] Property NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody > scheduler_response > data > anyOf > SchedulerRequestResponseBody > output_data_id</strong>  

</summary>
<blockquote>

**Title:** Output Data Id

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>
<blockquote>

##### <a name="data_anyOf_i0_scheduler_response_data_anyOf_i1"></a>4.1.3.4.2. Property `NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody > scheduler_response > data > anyOf > item 1`

|                           |                                                                                                                                                          |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                                                                                 |
| **Required**              | No                                                                                                                                                       |
| **Additional properties** | [[Should-conform]](#data_anyOf_i0_scheduler_response_data_anyOf_i1_additionalProperties "Each additional property must conform to the following schema") |

<details>
<summary><strong> <a name="data_anyOf_i0_scheduler_response_data_anyOf_i1_additionalProperties"></a>4.1.3.4.2.1. Property NgenCalibrationResponse > data > anyOf > ModelExecRequestResponseBody > scheduler_response > data > anyOf > item 1 > additionalProperties</strong>  

</summary>
<blockquote>

|              |        |
| ------------ | ------ |
| **Type**     | `null` |
| **Required** | No     |

</blockquote>
</details>

</blockquote>

</blockquote>

</blockquote>
</details>

</blockquote>
</details>

</blockquote>
<blockquote>

### <a name="data_anyOf_i1"></a>4.2. Property `NgenCalibrationResponse > data > anyOf > item 1`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

</blockquote>

</blockquote>

</blockquote>
</details>

----------------------------------------------------------------------------------------------------------------------------
