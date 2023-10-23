# SessionInitResponse

**Title:** SessionInitResponse

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

**Description:** The :class:`~.message.Response` subtype used to response to a :class:`.SessionInitMessage`, either
conveying the new session's details or information about why session init failed.

In particular, the :attr:`data` attribute will be of one two types.  For responses
indicating success, :attr:`data` will contain a :class:`Session` object (likely a :class:`FullAuthSession`) created
as a result of the request.  This will have its :attr:`Session.session_secret` attribute, which will be needed by
the requesting client to send further messages via the authenticated session.

Alternatively, for responses indicating failure, :attr:`data` will contain a :class:`FailedSessionInitInfo` with
details about the failure.

In the init constructor, if the ``data`` param is not some of either of the expected types, or a dict that can be
deserialized to one, then :attr:`data` will be set as an :class:`FailedSessionInitInfo`.  This is due to the
de facto failure the response instance represents to a request for a session, if there is no valid :class:`Session`
in the response.  This will also override the ``success`` parameter, and force :attr:`success` to be false.

Parameters
----------
success : bool
    Was the requested new session initialized successfully for the client
reason : str
    A summary of the results of the session request
message : str
    More details on the results of the session request, if any, typically only used when a request is unsuccessful
data : dict, `Session`, or `FailedSessionInitInfo`, optional
    For successful requests, the session object (possibly serialized as a ``dict``); for failures, the failure info
    object (again, possibly serialized as a ``dict``), or None

Attributes
----------
success : bool
    Was the requested new session initialized successfully for the client
reason : str
    A summary of the results of the session request
message : str
    More details on the results of the session request, if any, typically only used when a request is unsuccessful
data : `.Session` or `.FailedSessionInitInfo`
    For successful requests, the session object; for failures, the failure info object

<details>
<summary><strong> <a name="success"></a>1. [Required] Property SessionInitResponse > success</strong>  

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
<summary><strong> <a name="reason"></a>2. [Required] Property SessionInitResponse > reason</strong>  

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
<summary><strong> <a name="message"></a>3. [Optional] Property SessionInitResponse > message</strong>  

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
<summary><strong> <a name="data"></a>4. [Required] Property SessionInitResponse > data</strong>  

</summary>
<blockquote>

**Title:** Data

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `combining`                                                               |
| **Required**              | Yes                                                                       |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

<blockquote>

| Any of(Option)                          |
| --------------------------------------- |
| [FullAuthSession](#data_anyOf_i0)       |
| [Session](#data_anyOf_i1)               |
| [FailedSessionInitInfo](#data_anyOf_i2) |

<blockquote>

### <a name="data_anyOf_i0"></a>4.1. Property `SessionInitResponse > data > anyOf > FullAuthSession`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/FullAuthSession                                             |

**Description:** A bare-bones representation of a session between some compatible server and client, over which various requests may
be made, and potentially other communication may take place.

<details>
<summary><strong> <a name="data_anyOf_i0_session_id"></a>4.1.1. [Required] Property SessionInitResponse > data > anyOf > FullAuthSession > session_id</strong>  

</summary>
<blockquote>

**Title:** Session Id

|              |           |
| ------------ | --------- |
| **Type**     | `integer` |
| **Required** | Yes       |

**Description:** The unique identifier for this session.

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i0_session_secret"></a>4.1.2. [Optional] Property SessionInitResponse > data > anyOf > FullAuthSession > session_secret</strong>  

</summary>
<blockquote>

**Title:** Session Secret

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** The unique random secret for this session.

| Restrictions   |    |
| -------------- | -- |
| **Min length** | 64 |
| **Max length** | 64 |

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i0_created"></a>4.1.3. [Optional] Property SessionInitResponse > data > anyOf > FullAuthSession > created</strong>  

</summary>
<blockquote>

**Title:** Created

|              |             |
| ------------ | ----------- |
| **Type**     | `string`    |
| **Required** | No          |
| **Format**   | `date-time` |

**Description:** The date and time this session was created.

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i0_last_accessed"></a>4.1.4. [Optional] Property SessionInitResponse > data > anyOf > FullAuthSession > last_accessed</strong>  

</summary>
<blockquote>

**Title:** Last Accessed

|              |             |
| ------------ | ----------- |
| **Type**     | `string`    |
| **Required** | No          |
| **Format**   | `date-time` |

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i0_ip_address"></a>4.1.5. [Required] Property SessionInitResponse > data > anyOf > FullAuthSession > ip_address</strong>  

</summary>
<blockquote>

**Title:** Ip Address

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i0_user"></a>4.1.6. [Optional] Property SessionInitResponse > data > anyOf > FullAuthSession > user</strong>  

</summary>
<blockquote>

**Title:** User

|              |             |
| ------------ | ----------- |
| **Type**     | `string`    |
| **Required** | No          |
| **Default**  | `"default"` |

</blockquote>
</details>

</blockquote>
<blockquote>

### <a name="data_anyOf_i1"></a>4.2. Property `SessionInitResponse > data > anyOf > Session`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/Session                                                     |

**Description:** A bare-bones representation of a session between some compatible server and client, over which various requests may
be made, and potentially other communication may take place.

<details>
<summary><strong> <a name="data_anyOf_i1_session_id"></a>4.2.1. [Required] Property SessionInitResponse > data > anyOf > Session > session_id</strong>  

</summary>
<blockquote>

**Title:** Session Id

|              |           |
| ------------ | --------- |
| **Type**     | `integer` |
| **Required** | Yes       |

**Description:** The unique identifier for this session.

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i1_session_secret"></a>4.2.2. [Optional] Property SessionInitResponse > data > anyOf > Session > session_secret</strong>  

</summary>
<blockquote>

**Title:** Session Secret

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** The unique random secret for this session.

| Restrictions   |    |
| -------------- | -- |
| **Min length** | 64 |
| **Max length** | 64 |

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i1_created"></a>4.2.3. [Optional] Property SessionInitResponse > data > anyOf > Session > created</strong>  

</summary>
<blockquote>

**Title:** Created

|              |             |
| ------------ | ----------- |
| **Type**     | `string`    |
| **Required** | No          |
| **Format**   | `date-time` |

**Description:** The date and time this session was created.

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i1_last_accessed"></a>4.2.4. [Optional] Property SessionInitResponse > data > anyOf > Session > last_accessed</strong>  

</summary>
<blockquote>

**Title:** Last Accessed

|              |             |
| ------------ | ----------- |
| **Type**     | `string`    |
| **Required** | No          |
| **Format**   | `date-time` |

</blockquote>
</details>

</blockquote>
<blockquote>

### <a name="data_anyOf_i2"></a>4.3. Property `SessionInitResponse > data > anyOf > FailedSessionInitInfo`

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |
| **Defined in**            | #/definitions/FailedSessionInitInfo                                       |

**Description:** A :class:`~.serializeable.Serializable` type for representing details on why a :class:`SessionInitMessage` didn't
successfully init a session.

<details>
<summary><strong> <a name="data_anyOf_i2_user"></a>4.3.1. [Required] Property SessionInitResponse > data > anyOf > FailedSessionInitInfo > user</strong>  

</summary>
<blockquote>

**Title:** User

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i2_reason"></a>4.3.2. [Optional] Property SessionInitResponse > data > anyOf > FailedSessionInitInfo > reason</strong>  

</summary>
<blockquote>

|                |                    |
| -------------- | ------------------ |
| **Type**       | `enum (of string)` |
| **Required**   | No                 |
| **Default**    | `-1`               |
| **Defined in** |                    |

**Description:** An enumeration.

Must be one of:
* "AUTHENTICATION_SYS_FAIL"
* "AUTHENTICATION_DENIED"
* "USER_NOT_AUTHORIZED"
* "AUTH_ATTEMPT_TIMEOUT"
* "REQUEST_TIMED_OUT"
* "SESSION_DETAILS_MISSING"
* "SESSION_MANAGER_FAIL"
* "OTHER"
* "UNKNOWN"

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i2_fail_time"></a>4.3.3. [Optional] Property SessionInitResponse > data > anyOf > FailedSessionInitInfo > fail_time</strong>  

</summary>
<blockquote>

**Title:** Fail Time

|              |             |
| ------------ | ----------- |
| **Type**     | `string`    |
| **Required** | No          |
| **Format**   | `date-time` |

</blockquote>
</details>

<details>
<summary><strong> <a name="data_anyOf_i2_details"></a>4.3.4. [Optional] Property SessionInitResponse > data > anyOf > FailedSessionInitInfo > details</strong>  

</summary>
<blockquote>

**Title:** Details

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

</blockquote>
</details>

</blockquote>

</blockquote>

</blockquote>
</details>

----------------------------------------------------------------------------------------------------------------------------
