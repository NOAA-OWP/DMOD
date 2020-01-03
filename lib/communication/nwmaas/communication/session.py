import datetime
import hashlib
import random
from .message import AbstractInitRequest, MessageEventType, Response
from .serializeable import Serializable
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Union


class SessionInitFailureReason(Enum):
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

    _DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    _serialized_attributes = ['session_id', 'session_secret', 'created']
    """ list of str: the names of attributes/properties to include when serializing an instance """

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
        return cls(session_id=json_obj['session_id'], session_secret=json_obj['session_secret'],
                   created=json_obj['created'])

    @classmethod
    def full_equals(cls, obj1, obj2) -> bool:
        """
        Test if two objects are both of this type and are more "fully" equal than can be determined from the standard
        equality implementation, by comparing all the attributes from :meth:`get_serialized_attributes`.

        Parameters
        ----------
        obj1
        obj2

        Returns
        -------
        fully_equal : bool
            whether the objects are of the same type and with equal values for all serialized attributes
        """
        if obj1.__class__ != cls or obj2.__class__ != cls:
            return False
        try:
            for attr in cls._serialized_attributes:
                if getattr(obj1, attr) != getattr(obj2, attr):
                    return False
            return True
        except Exception as e:
            # TODO: do something with this exception
            return False

    @classmethod
    def get_datetime_format(cls):
        return cls._DATETIME_FORMAT

    @classmethod
    def get_serialized_attributes(cls):
        return tuple(cls._serialized_attributes)

    def __eq__(self, other):
        return isinstance(other, Session) and self.session_id == other.session_id

    def __init__(self, session_id: Union[str, int], session_secret: str = None,
                 created: Union[datetime.datetime, str] = datetime.datetime.now()):
        """
        Instantiate, either from an existing record - in which case values for 'secret' and 'created' are provided - or
        from a newly acquired session id - in which case 'secret' is randomly generated, 'created' is set to now(), and
        the expectation is that a new session record will be created from this instance.

        Parameters
        ----------
        session_id : Union[str, int]
            numeric session id value
        session_secret : :obj:`str`, optional
            the session secret, if deserializing this object from an existing session record
        created : Union[:obj:`datetime.datetime`, :obj:`str`]
            the date and time of session creation, either as a datetime object or parseable string, set to
            :method:`datetime.datetime.now()` by default
        """

        self._session_id = int(session_id)
        if session_secret is None:
            random.seed()
            self._session_secret = hashlib.sha256(str(random.random()).encode('utf-8')).hexdigest()
        else:
            self._session_secret = session_secret

        try:
            if isinstance(created, str):
                self._created = datetime.datetime.strptime(created, Session._DATETIME_FORMAT)
            elif not isinstance(created, datetime.datetime):
                raise RuntimeError()
            else:
                self._created = created
        except:
            self._created = datetime.datetime.now()

    def __hash__(self):
        return self.session_id

    @property
    def created(self):
        """:obj:`datetime.datetime`: The date and time this session was created."""
        return self._created

    def get_as_dict(self) -> dict:
        """
        Get a serialized representation of this instance as a :obj:`dict` instance.

        Returns
        -------
        dict
            a serialized representation of this instance
        """
        attributes = {}
        for attr in self._serialized_attributes:
            attr_val = getattr(self, attr)
            if isinstance(attr_val, datetime.datetime):
                attributes[attr] = attr_val.strftime(Session._DATETIME_FORMAT)
            else:
                attributes[attr] = getattr(self, attr)
        return attributes

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

    def is_serialized_attribute(self, attribute) -> bool:
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
        for attr in self._serialized_attributes:
            if attribute == attr:
                return True
        return False

    @property
    def json_attributes(self) -> tuple:
        """
        Get a tuplized (and therefore immutable) copy of the attribute names for serialized JSON representations of the
        instance.

        Returns
        -------
        tuple of str:
            a tuplized (and therefore immutable) copy of the attribute names for serialized JSON representations
        """
        return tuple(self._serialized_attributes)

    @property
    def session_id(self):
        """int: The unique identifier for this session."""
        return int(self._session_id)

    @property
    def session_secret(self):
        """str: The unique random secret for this session."""
        return self._session_secret

    def to_dict(self) -> dict:
        return self.get_as_dict()


# TODO: work more on this later, when authentication becomes more important
class FullAuthSession(Session):

    _serialized_attributes = ['session_id', 'session_secret', 'created', 'ip_address', 'user']

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
            return cls(session_id=json_obj['session_id'], session_secret=json_obj['session_secret'],
                       created=json_obj['created'], ip_address=json_obj['ip_address'], user=json_obj['user'])
        except:
            return Session.factory_init_from_deserialized_json(json_obj)

    def __init__(self, ip_address: str, session_id: Union[str, int], session_secret: str = None,
                 created: Union[datetime.datetime, str] = datetime.datetime.now(), user: str = 'default'):
        super().__init__(session_id=session_id, session_secret=session_secret, created=created)
        self._user = user if user is not None else 'default'
        self._ip_address = ip_address

    @property
    def ip_address(self):
        return self._ip_address

    @property
    def user(self):
        return self._user


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

    event_type: MessageEventType = MessageEventType.SESSION_INIT
    """ :class:`MessageEventType`: the event type for this message implementation """

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
        return SessionInitMessage(username=json_obj['username'], user_secret=json_obj['user_secret'])

    def __init__(self, username: str, user_secret: str):
        self.username = username
        self.user_secret = user_secret

    def to_dict(self) -> dict:
        return {'username': self.username, 'user_secret': self.user_secret}


class FailedSessionInitInfo(Serializable):
    """
    A :class:`~.serializeable.Serializable` type for representing details on why a :class:`SessionInitMessage` didn't
    successfully init a session.
    """

    @classmethod
    def get_datetime_format(cls):
        return Session.get_datetime_format()

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        try:
            # Allow for fail_time to be not present or set to None ...
            if 'fail_time' not in json_obj or json_obj['fail_time'] is None:
                fail_time = None
            # ... or to be already a datetime object ...
            elif isinstance(json_obj['fail_time'], datetime.datetime):
                fail_time = json_obj['fail_time']
            # ... or to be a string that can be parsed to a datetime object (or else throw exception and return None)
            else:
                fail_time = datetime.datetime.strptime(json_obj['fail_time'], cls.get_datetime_format())

            # Similarly, allow reason to be unspecified or None (i.e., UNKNOWN) ...
            if 'reason' not in json_obj or json_obj['reason'] is None:
                reason = SessionInitFailureReason.UNKNOWN
            # ... or to be already a SessionInitFailureReason object ...
            elif isinstance(json_obj['reason'], SessionInitFailureReason):
                reason = json_obj['reason']
            # ... or to be a valid SessionInitFailureReason name
            else:
                reason = SessionInitFailureReason[json_obj['reason']]

            return FailedSessionInitInfo(user=json_obj['user'], reason=reason, fail_time=fail_time,
                                         details=json_obj['details'])
        except:
            return None

    def __eq__(self, other):
        if self.__class__ != other.__class__ or self.user != other.user or self.reason != other.reason:
            return False
        if self.fail_time is not None and other.fail_time is not None and self.fail_time != other.fail_time:
            return False
        return True

    def __init__(self, user: str, reason: SessionInitFailureReason = SessionInitFailureReason.UNKNOWN,
                 fail_time: Optional[datetime.datetime] = None, details: Optional[str] = None):
        self.user = user
        self.reason = reason
        self.fail_time = fail_time if fail_time is not None else datetime.datetime.now()
        self.details = details

    def to_dict(self) -> dict:
        fail_time_str = self.fail_time.strftime(self.get_datetime_format()) if self.fail_time is not None else None
        return {'user': self.user, 'reason': self.reason, 'fail_time': fail_time_str, 'details': self.details}


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

    response_to_type = SessionInitMessage
    """ Type[`SessionInitMessage`]: the type or subtype of :class:`Message` for which this type is the response"""

    @classmethod
    def _factory_init_data_attribute(cls, json_obj: dict) -> Optional[SessionInitDataType]:
        """
        Initialize the argument value for a constructor param used to set the :attr:`data` attribute appropriate for
        this type, given the parent JSON object, which for this type means deserializing the dict value to either a
        session object or a failure info object.

        Parameters
        ----------
        json_obj : dict
            the parent JSON object containing the desired session data serialized value

        Returns
        -------
        data
            the resulting :class:`Session` or :class:`FailedSessionInitInfo` object obtained after processing,
            or None if no valid object could be processed of either type
        """
        data = None
        try:
            data = json_obj['data']
        except:
            det = 'Received serialized JSON response object that did not contain expected key for serialized session.'
            return FailedSessionInitInfo(user='', reason=SessionInitFailureReason.SESSION_DETAILS_MISSING, details=det)

        try:
            # If we can, return the FullAuthSession or Session obtained by this class method
            return FullAuthSession.factory_init_from_deserialized_json(data)
        except:
            try:
                return FailedSessionInitInfo.factory_init_from_deserialized_json(data)
            except:
                return None

    def __eq__(self, other):
        return self.__class__ == other.__class__ \
               and self.success == other.success \
               and self.reason == other.reason \
               and self.message == other.message \
               and self.data.__class__.full_equals(self.data, other.data) if isinstance(self.data,
                                                                                        Session) else self.data == other.data

    def __init__(self, success: bool, reason: str, message: str = '', data: Optional[SessionInitDataType] = None):
        super().__init__(success=success, reason=reason, message=message, data=data)

        # If we received a dict for data, try to deserialize using the class method (failures will set to None,
        # which will get handled by the next conditional logic)
        if isinstance(self.data, dict):
            # Remember, the class method expects a JSON obj dict with the data as a child element, not the data directly
            self.data = self.__class__._factory_init_data_attribute({'success': self.success, 'data': data})

        if self.data is None:
            details = 'Instantiated SessionInitResponse object without session data; defaulting to failure'
            self.data = FailedSessionInitInfo(user='', reason=SessionInitFailureReason.SESSION_DETAILS_MISSING,
                                              details=details)
        elif not (isinstance(self.data, Session) or isinstance(self.data, FailedSessionInitInfo)):
            details = 'Instantiated SessionInitResponse object using unexpected type for data ({})'.format(
                self.data.__class__.__name__)
            try:
                as_str = '; converted to string: \n{}'.format(str(self.data))
                details += as_str
            except:
                # If we can't cast to string, don't worry; just leave out that part in details
                pass
            self.data = FailedSessionInitInfo(user='', reason=SessionInitFailureReason.SESSION_DETAILS_MISSING,
                                              details=details)

        # Make sure to reset/change self.success if self.data ends up being a failure info object
        self.success = self.success and isinstance(self.data, Session)


class SessionManager(ABC):

    @abstractmethod
    def create_session(self, ip_address: str, username: str) -> Session:
        pass

    @abstractmethod
    def lookup_session(self, secret: str):
        pass

    @abstractmethod
    def remove_session(self, session: Session):
        pass


