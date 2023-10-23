# UnsupportedMessageTypeResponse

**Title:** UnsupportedMessageTypeResponse

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
<summary><strong> <a name="success"></a>1. [Optional] Property UnsupportedMessageTypeResponse > success</strong>  

</summary>
<blockquote>

**Title:** Success

|              |           |
| ------------ | --------- |
| **Type**     | `boolean` |
| **Required** | No        |
| **Default**  | `false`   |

</blockquote>
</details>

<details>
<summary><strong> <a name="reason"></a>2. [Optional] Property UnsupportedMessageTypeResponse > reason</strong>  

</summary>
<blockquote>

**Title:** Reason

|              |                                    |
| ------------ | ---------------------------------- |
| **Type**     | `string`                           |
| **Required** | No                                 |
| **Default**  | `"Message Event Type Unsupported"` |

</blockquote>
</details>

<details>
<summary><strong> <a name="message"></a>3. [Required] Property UnsupportedMessageTypeResponse > message</strong>  

</summary>
<blockquote>

**Title:** Message

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

</blockquote>
</details>

<details>
<summary><strong> <a name="data"></a>4. [Optional] Property UnsupportedMessageTypeResponse > data</strong>  

</summary>
<blockquote>

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/Serializable                                                |

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

</blockquote>
</details>

<details>
<summary><strong> <a name="actual_event_type"></a>5. [Required] Property UnsupportedMessageTypeResponse > actual_event_type</strong>  

</summary>
<blockquote>

|                |                                |
| -------------- | ------------------------------ |
| **Type**       | `enum (of string)`             |
| **Required**   | Yes                            |
| **Defined in** | #/definitions/MessageEventType |

**Description:** An enumeration.

Must be one of:
* "SESSION_INIT"
* "MODEL_EXEC_REQUEST"
* "SCHEDULER_REQUEST"
* "INFORMATION_UPDATE"
* "METADATA"
* "PARTITION_REQUEST"
* "EVALUATION_REQUEST"
* "CALIBRATION_REQUEST"
* "DATASET_MANAGEMENT"
* "DATA_TRANSMISSION"
* "INVALID"

</blockquote>
</details>

<details>
<summary><strong> <a name="listener_type"></a>6. [Required] Property UnsupportedMessageTypeResponse > listener_type</strong>  

</summary>
<blockquote>

**Title:** Listener Type

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | Yes                                                                       |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

</blockquote>
</details>

----------------------------------------------------------------------------------------------------------------------------
