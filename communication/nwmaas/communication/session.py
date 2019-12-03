import datetime
import hashlib
import json
import random
from .message import Message, MessageEventType, Response
from typing import Union


class Session:
    """
    A bare-bones representation of a session between a :obj:`request_handler.RequestHandler` and some compatible client,
    over which requests for jobs may be made, and potentially other communication may take place.
    """

    _DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    @classmethod
    def get_datetime_format(cls):
        return cls._DATETIME_FORMAT

    def __init__(self, session_id: int, session_secret: str = None,
                 created: Union[datetime.datetime, str] = datetime.datetime.now()):
        """
        Instantiate, either from an existing record - in which case values for 'secret' and 'created' are provided - or
        from a newly acquired session id - in which case 'secret' is randomly generated, 'created' is set to now(), and
        the expectation is that a new session record will be created from this instance.

        Parameters
        ----------
        session_id : int
            numeric session id value
        session_secret : :obj:`str`, optional
            the session secret, if deserializing this object from an existing session record
        created : Union[:obj:`datetime.datetime`, :obj:`str`]
            the date and time of session creation, either as a datetime object or parseable string, set to
            :method:`datetime.datetime.now()` by default
        """

        self._session_id = session_id
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

        """ list of str: the names of attributes/properties to include when serializing an instance """
        self._serialized_attributes = ['session_id', 'session_secret', 'created']

    def __eq__(self, other):
        return isinstance(other, Session) and self._session_id == other.session_id

    def __hash__(self):
        return self._session_id

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

    def get_as_json(self) -> object:
        """
        Get a serialized JSON representation of this instance.

        Returns
        -------
        object
            a serialized JSON representation of this instance
        """
        return json.dumps(self.get_as_dict())

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
        return self._session_id

    @property
    def session_secret(self):
        """str: The unique random secret for this session."""
        return self._session_secret


class SessionInitMessage(Message):
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

    def __init__(self, username: str, user_secret: str):
        self.username = username
        self.user_secret = user_secret

    def to_dict(self) -> dict:
        return {'username': self.username, 'user_secret': self.user_secret}


class SessionInitResponse(Response):
    """
    The :class:`Response` subtype used to response to a :class:`SessionInitMessage`.

    In particular, the :attr:`data` attribute should contain a serialized version of the :class:`Session` created as a
    result of the request, in the form of a JSON object (as provided by :meth:`Session.get_as_dict`).  In particular,
    this includes the :attr:`Session.session_secret` attribute, which will be needed by the requesting client to send
    further messages via the authenticated session.

    Parameters
    ----------
    success : bool
        Was the requested new session initialized successfully for the client
    reason : str
        A summary of the results of the session request
    message : str
        More details on the results of the session request, if any, typically only used when a request is unsuccessful
    data : dict
        For successful requests, the serialized session details, including the session_secret

    Attributes
    ----------
    success : bool
        Was the requested new session initialized successfully for the client
    reason : str
        A summary of the results of the session request
    message : str
        More details on the results of the session request, if any, typically only used when a request is unsuccessful
    data : dict
        For successful requests, the serialized session details, including the session_secret

    """

    response_to_type = SessionInitMessage
    """ :class:`Message`: the type of Message for which this type is the response"""

    def __init__(self, success: bool, reason: str, message: str = '', data=None):
        super().__init__(success=success, reason=reason, message=message, data=data)
