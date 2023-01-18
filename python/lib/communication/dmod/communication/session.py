import datetime
import hashlib
import random
from .message import AbstractInitRequest, MessageEventType, Response
from dmod.core.serializable import Serializable
from dmod.core.enum import PydanticEnum
from abc import ABC, abstractmethod
from numbers import Number
from typing import ClassVar, Dict, Optional, List, Type, Union
from pydantic import Field, IPvAnyAddress, validator, root_validator


def _generate_secret() -> str:
    """Generate random sha256 session secret.

    Returns
    -------
    str
        sha256 digest
    """
    random.seed()
    return hashlib.sha256(str(random.random()).encode('utf-8')).hexdigest()


class SessionInitFailureReason(PydanticEnum):
    AUTHENTICATION_SYS_FAIL = 1, # some error other than bad credentials prevented successful user authentication
    AUTHENTICATION_DENIED = 2,  # the user's asserted identity was not authenticated due to the provided credentials
    USER_NOT_AUTHORIZED = 3,  # the user was authenticated, but does not have authorized permission for a session
    AUTH_ATTEMPT_TIMEOUT = 4,  # the authentication backend did not respond to the session initializer before a timeout
    REQUEST_TIMED_OUT = 5,  # the session initializer did not respond to the session requestor before a timeout
    SESSION_DETAILS_MISSING = 6,  # otherwise appearing successful, but the serialized session details were not sent
    SESSION_MANAGER_FAIL = 7,  # after authentication and authorization were successful, there was an error in the session manager
    OTHER = 8,  # an understood error occurred that is not currently covered by the available enum values
    UNKNOWN = -1


class Session(Serializable):
    """
    A bare-bones representation of a session between some compatible server and client, over which various requests may
    be made, and potentially other communication may take place.
    """

    _DATETIME_FORMAT: ClassVar[str] = '%Y-%m-%d %H:%M:%S.%f'

    session_id: int = Field(description="The unique identifier for this session.")
    # QUESTION: we are using UUID4's elsewhere, do we want to use that instead here? Or perhaps a ULID?
    session_secret: str = Field(default_factory=_generate_secret, min_length=64, max_length=64, description="The unique random secret for this session.")
    created: datetime.datetime = Field(default_factory=datetime.datetime.now, description="The date and time this session was created.")
    last_accessed: datetime.datetime = Field(default_factory=datetime.datetime.now)

    _full_equality_attributes: ClassVar[List[str]]= ['session_id', 'session_secret', 'created', 'last_accessed']
    """ list of str: the names of attributes/properties to include when testing instances for complete equality """

    _serialized_attributes: ClassVar[List[str]]= ['session_id', 'session_secret', 'created', 'last_accessed']
    """ list of str: the names of attributes/properties to include when serializing an instance """

    _session_timeout_delta: ClassVar[datetime.timedelta] = datetime.timedelta(minutes=30.0)

    @validator("created", "last_accessed", pre=True)
    def validate_date(cls, value):
        if isinstance(value, datetime.datetime):
            return value

        try:
            return datetime.datetime.strptime(value, cls.get_datetime_str_format())
        # TODO: improve error handling, or throw something know for downstream users.
        except: 
            return datetime.datetime.now()

    @classmethod
    def get_datetime_str_format(cls):
        return cls._DATETIME_FORMAT

    @classmethod
    def get_full_equality_attributes(cls) -> tuple:
        """
        Get a tuple-ized (and therefore immutable) collection of attribute names for those attributes used for
        determining more complete or "full" equality between instances than is provided by the standard "equals"
        operation, as is used in :meth:`full_equals`.

        Returns
        -------
        tuple of str:
            a tuple-ized (and therefore immutable) collection of attribute names for those attributes used for
            determining full/complete equality between instances.
        """
        return tuple(cls.__fields__)

    @classmethod
    def get_serialized_attributes(cls) -> tuple:
        """
        Get a tuple-ized (and therefore immutable) collection of attribute names for those attributes included in
        serialized representations of the instance.

        A common case for usage is for getting expected/required names for serializing a class to JSON.

        Returns
        -------
        tuple of str:
            a tuple-ized (and therefore immutable) collection of attribute names for attributes used in serialization
        """
        return tuple(cls.__fields__)

    @classmethod
    def get_session_timeout_delta(cls) -> datetime.timedelta:
        return cls._session_timeout_delta

    def __eq__(self, other):
        return isinstance(other, Session) and self.session_id == other.session_id

    def __hash__(self):
        return self.session_id

    def full_equals(self, other: object) -> bool:
        """
        Test if this object and another are both of the exact same type and are more "fully" equal than can be
        determined from the standard equality implementation, by comparing all the attributes from
        :meth:`get_serialized_attributes`.

        In general, the standard :meth:`__eq__` implementation will only determine if two instances represent the same
        modeled session.

        Parameters
        ----------
        other

        Returns
        -------
        fully_equal : bool
            whether the objects are of the same type and with equal values for all serialized attributes
        """
        return super().__eq__(other)

    def get_as_dict(self) -> dict:
        """
        Get a serialized representation of this instance as a :obj:`dict` instance.

        Returns
        -------
        dict
            a serialized representation of this instance
        """
        return self.dict()

    def get_as_json(self) -> str:
        """
        Get a serialized JSON representation of this instance.

        Returns
        -------
        object
            a serialized JSON representation of this instance
        """
        return self.to_json()

    def get_created_serialized(self):
        return self.created.strftime(Session._DATETIME_FORMAT)

    def get_last_accessed_serialized(self):
        return self.last_accessed.strftime(Session._DATETIME_FORMAT)

    def is_expired(self):
        return self.last_accessed + self.get_session_timeout_delta() < datetime.datetime.now()

    def is_serialized_attribute(self, attribute: str) -> bool:
        """
        Test whether an attribute of the given name is included in the serialized version of the instance returned by
        :method:`get_as_dict` and/or :method:`get_as_json` (at the top level).

        Parameters
        ----------
        attribute

        Returns
        -------
        bool
            True if there is an attribute with the given name in the :attr:`_serialized_attributes` list, or False
            otherwise
        """
        if not isinstance(attribute, str):
            return False
        return attribute in self.__fields__

    def dict(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = True, # Note this follows Serializable convention
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False
    ) -> Dict[str, Union[str, int]]:
        _exclude = {"created", "last_accessed"}
        if exclude is not None:
            _exclude = {*_exclude, *exclude}

        serial = super().dict(
            include=include,
            exclude=_exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

        if exclude is None or "created" not in exclude:
            serial["created"] = self.created.strftime(self.get_datetime_str_format())

        if exclude is None or "last_accessed" not in exclude:
            serial["last_accessed"] = self.last_accessed.strftime(self.get_datetime_str_format())

        return serial


# TODO: work more on this later, when authentication becomes more important
class FullAuthSession(Session):

    ip_address: str
    user: str = 'default'

    @validator("ip_address", pre=True)
    def cast_ip_address_to_str(cls, value: str) -> str:
        # this will raise if cannot be coerced into IPv(4|6)Address
        return str(IPvAnyAddress.validate(value))

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Parameters
        ----------
        json_obj

        Returns
        -------
        A new object of this type instantiated from the deserialize JSON object dictionary
        """

        try:
            return cls(**json_obj)
        except:
            return Session.factory_init_from_deserialized_json(json_obj)


class SessionInitMessage(AbstractInitRequest):
    """
    The :class:`Message` subtype used by a client to request and authenticate a new :class:`Session` instance.

    Parameters
    ----------
    username : str
        The asserted username for the client entity requesting a session
    user_secret : str
        The secret through which the client entity establishes the authenticity of its username assertion

    Attributes
    ----------
    username : str
        The asserted username for the client entity requesting a session
    user_secret : str
        The secret through which the client entity establishes the authenticity of its username assertion
    """

    username: str
    user_secret: str

    event_type: ClassVar[MessageEventType] = MessageEventType.SESSION_INIT
    """ :class:`MessageEventType`: the event type for this message implementation """


class FailedSessionInitInfo(Serializable):
    """
    A :class:`~.serializeable.Serializable` type for representing details on why a :class:`SessionInitMessage` didn't
    successfully init a session.
    """

    user: str
    reason: SessionInitFailureReason = SessionInitFailureReason.UNKNOWN
    fail_time: datetime.datetime = Field(default_factory=datetime.datetime.now)
    details: Optional[str]

    @classmethod
    def get_datetime_str_format(cls):
        return Session.get_datetime_str_format()


# Define this custom type here for hinting
SessionInitDataType = Union[Session, FailedSessionInitInfo]

class SessionInitResponse(Response):
    """
    The :class:`~.message.Response` subtype used to response to a :class:`.SessionInitMessage`, either
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

    """

    response_to_type: ClassVar[Type[AbstractInitRequest]] = SessionInitMessage
    """ Type[`SessionInitMessage`]: the type or subtype of :class:`Message` for which this type is the response"""

    # NOTE: this field _is_ optional, however `data` will be FailedSessionInitInfo if it is not
    # provided or set to None.
    # NOTE: order of this Union matters. types will be coerced from left to right. meaning, more
    # specific types (i.e. subtypes) should be listed before more general types. see `SmartUnion`
    # for more detail: https://docs.pydantic.dev/usage/model_config/#smart-union
    data: Union[FailedSessionInitInfo, FullAuthSession, Session] = Field(
        default_factory=lambda: FailedSessionInitInfo(
            user="",
            reason=SessionInitFailureReason.SESSION_DETAILS_MISSING,
            details="Instantiated SessionInitResponse object without session data; defaulting to failure",
        )
    )

    @root_validator(pre=True)
    def _coerce_data_field(cls, values):
        data = values.get("data")

        if data is None:
            details = "Instantiated SessionInitResponse object without session data; defaulting to failure"
            values["data"] = FailedSessionInitInfo(
                user="",
                reason=SessionInitFailureReason.SESSION_DETAILS_MISSING,
                details=details,
            )
            return values

        # run `data` field validators
        coerced_data, errors = cls.__fields__["data"].validate(data, {}, loc="")
        if errors is not None:
            details = 'Instantiated SessionInitResponse object using unexpected type for data ({})'.format(
                data.__class__.__name__)
            try:
                as_str = '; converted to string: \n{}'.format(str(data))
                details += as_str
            except:
                # If we can't cast to string, don't worry; just leave out that part in details
                pass
            values["data"] = FailedSessionInitInfo(
                user="",
                reason=SessionInitFailureReason.SESSION_DETAILS_MISSING,
                details=details,
            )
            return values

        values["data"] = coerced_data
        return values

    @root_validator()
    def _update_success(cls, values):
        # Make sure to reset/change self.success if self.data ends up being a failure info object
        values["success"] = values["success"] and isinstance(values["data"], Session)
        return values

    def __eq__(self, other):
        return self.__class__ == other.__class__ \
               and self.success == other.success \
               and self.reason == other.reason \
               and self.message == other.message \
               and self.data.full_equals(other.data) if isinstance(self.data, Session) else self.data == other.data


class SessionManager(ABC):
    """
    Interface for a :class:`Session` manager object that can maintain and query a collection of valid sessions.

    Note in particular the separation of lookup-type methods, rather than a single method with multiple optional args.
    The intent was to separate behavior to avoid ambiguity and convoluted logic among implementations to address cases
    when multiple arguments associate with different sessions.
    """

    @abstractmethod
    def create_session(self, ip_address: str, username: str) -> Session:
        pass

    @abstractmethod
    def lookup_session_by_id(self, session_id: int) -> Optional[Session]:
        pass

    @abstractmethod
    def lookup_session_by_secret(self, session_secret: str) -> Optional[Session]:
        pass

    @abstractmethod
    def lookup_session_by_username(self, username: str) -> Optional[Session]:
        pass

    @abstractmethod
    def refresh_session(self, session: Session) -> bool:
        pass

    @abstractmethod
    def remove_session(self, session: Session):
        pass
