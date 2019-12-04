import datetime
import hashlib
import json
import os
import random
from .message import Message, MessageEventType, Response
from abc import ABC, abstractmethod
from redis import Redis
from redis.client import Pipeline
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


# TODO: work more on this later, when authentication becomes more important
class FullAuthSession(Session):

    def __init__(self, ip_address, session_id, session_secret=None, created=datetime.datetime.now(), user='default'):
        super().__init__(session_id=session_id, session_secret=session_secret, created=created)
        self._serialized_attributes.append('ip_address')
        self._serialized_attributes.append('user')
        self._user = user if user is not None else 'default'
        self._ip_address = ip_address

    @property
    def ip_address(self):
        return self._ip_address

    @property
    def user(self):
        return self._user


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


class RedisBackendSessionManager(SessionManager):
    _SESSION_KEY_PREFIX = 'session:'
    _SESSION_HASH_SUBKEY_SECRET = 'secret'
    _SESSION_HASH_SUBKEY_CREATED = 'created'

    @classmethod
    def get_key_for_session(cls, session: FullAuthSession):
        return cls.get_key_for_session_by_id(session.session_id)

    @classmethod
    def get_key_for_session_by_id(cls, session_id):
        return cls.get_session_key_prefix() + str(session_id)

    @classmethod
    def get_session_key_prefix(cls):
        return cls._SESSION_KEY_PREFIX

    def __init__(self):
        self._redis_host = os.environ.get("REDIS_HOST", "redis")
        self._redis_port = os.environ.get("REDIS_PORT", 6379)
        self._redis_pass = os.environ.get("REDIS_PASS", '***REMOVED***')
        #print('****************** redis host is: ' + self._redis_host)

        self._redis = None

        self._next_session_id_key = 'next_session_id'
        self._all_session_secrets_hash_key = 'all_session_secrets'

        self._session_redis_hash_subkey_ip_address = 'ip_address'
        self._session_redis_hash_subkey_secret = 'secret'
        self._session_redis_hash_subkey_user = 'user'
        self._session_redis_hash_subkey_created = 'created'

    def _update_session_record(self, session: FullAuthSession, pipeline: Pipeline, do_ip_address=False, do_secret=False,
                               do_user=False):
        """
        Append to the execution tasks (without triggering execution) of a provided Pipeline to update appropriate
        properties of a serialized Session hash record in Redis.

        Parameters
        ----------
        session: FullAuthSession
            The deserialized, updated Session object from which some data in a Redis session hash data structure should
            be updated.
        pipeline: Pipeline
            The created Redis transactional pipeline.
        do_ip_address: bool
            Whether the ip_address key value should be updated for the session record.
        do_secret: bool
            Whether the secret key value should be updated for the session record.
        do_user: bool
            Whether the user key value should be updated for the session record.

        Returns
        -------

        """
        session_key = self.get_key_for_session(session)
        # Build a map of the valid hash structure sub-keys in redis to tuples of (should-update-field-flag, new-value)
        keys_and_flags = {
            'ip_address': (do_ip_address, session.ip_address),
            'secret': (do_secret, session.session_secret),
            'user': (do_user, session.user)
        }
        for key in keys_and_flags:
            if keys_and_flags[key][0]:
                pipeline.hset(session_key, key, keys_and_flags[key][1])

    def create_session(self, ip_address, username) -> Session:
        pipeline = self.redis.pipeline()
        try:
            pipeline.watch(self._next_session_id_key)
            session_id = pipeline.get(self._next_session_id_key)
            if session_id is None:
                session_id = 1
                pipeline.set(self._next_session_id_key, 2)
            else:
                pipeline.incr(self._next_session_id_key, 1)
            session = FullAuthSession(ip_address=ip_address, session_id=session_id, user=username)
            session_key = self.get_key_for_session(session)
            pipeline.hset(session_key, self._session_redis_hash_subkey_ip_address, session.ip_address)
            pipeline.hset(session_key, self._session_redis_hash_subkey_secret, session.session_secret)
            pipeline.hset(session_key, self._session_redis_hash_subkey_user, session.user)
            pipeline.hset(session_key, self._session_redis_hash_subkey_created, session.get_created_serialized())
            pipeline.hset(self._all_session_secrets_hash_key, session.session_secret, session.session_id)
            pipeline.execute()
            return session
        finally:
            pipeline.unwatch()
            pipeline.reset()

    def lookup_session(self, secret):
        session_id = self.redis.hget(self._all_session_secrets_hash_key, secret)
        if session_id is not None:
            record_hash = self.redis.hgetall(self.get_key_for_session_by_id(session_id))
            session = FullAuthSession(session_id=session_id,
                                      session_secret=record_hash[self._session_redis_hash_subkey_secret],
                                      #created=record_hash[self._session_redis_hash_subkey_created])
                                      created=record_hash[self._session_redis_hash_subkey_created],
                                      ip_address=record_hash[self._session_redis_hash_subkey_ip_address],
                                      user=record_hash[self._session_redis_hash_subkey_user])
            return session
        else:
            return None

    @property
    def redis(self):
        if self._redis is None:
            self._redis = Redis(host=self._redis_host,
                                port=self._redis_port,
                                # db=0, encoding="utf-8", decode_responses=True,
                                db=0,
                                decode_responses=True,
                                password=self._redis_pass)
        return self._redis

    def remove_session(self, session: FullAuthSession):
        pipeline = self.redis.pipeline()
        pipeline.delete(self.get_key_for_session(session))
        pipeline.hdel(self._all_session_secrets_hash_key, session.session_secret)
        pipeline.execute()
