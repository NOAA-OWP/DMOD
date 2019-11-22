import datetime
import hashlib
import json
import os
import random
from redis import Redis, WatchError
from redis.client import Pipeline
from typing import Union


class Session:
    """
    A bare-bones representation of a session between a :obj:`request_handler.RequestHandler` and some compatible client,
    over which requests for jobs may be made, and potentially other communication may take place.
    """

    _DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

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

        """ list of str: the names of attributes/properties to include when serializing an instance as JSON """
        self._json_attributes = ['session_id', 'session_secret', 'created']

    def __eq__(self, other):
        return isinstance(other, Session) and self._session_id == other.session_id

    def __hash__(self):
        return self._session_id

    @property
    def created(self):
        """:obj:`datetime.datetime`: The date and time this session was created."""
        return self._created

    def get_as_json(self):
        """
        Get a serialized JSON representation of this instance.

        Returns
        -------

        """
        attribs = {}
        for attr in self._json_attributes:
            attr_val = getattr(self, attr)
            if isinstance(attr_val, datetime.datetime):
                attribs[attr] = attr_val.strftime(Session._DATETIME_FORMAT)
            else:
                attribs[attr] = getattr(self, attr)

        return json.dumps(attribs)

    def get_created_serialized(self):
        return self.created.strftime(Session._DATETIME_FORMAT)

    def is_json_attribute(self, attribute) -> bool:
        """
        Test whether an attribute of the given name is included in the serialized version of the instance returned by
        :method:`get_as_json` (at the top level).

        Parameters
        ----------
        attribute

        Returns
        -------
        True if there is an attribute with the given name in the self._json_attributes list, or False otherwise
        """
        for attr in self._json_attributes:
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
        return tuple(self._json_attributes)

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
        self._json_attributes.append('ip_address')
        self._json_attributes.append('user')
        self._user = user if user is not None else 'default'
        self._ip_address = ip_address

    @property
    def ip_address(self):
        return self._ip_address

    @property
    def user(self):
        return self._user


class SessionManager:
    _SESSION_KEY_PREFIX = 'session:'
    _SESSION_HASH_SUBKEY_SECRET = 'secret'
    _SESSION_HASH_SUBKEY_CREATED = 'created'

    def __init__(self):
        host = os.environ.get("REDIS_HOST", "redis")
        port = os.environ.get("REDIS_PORT", 6379)
        print('****************** redis host is: ' + host)

        self.redis = Redis(host=host,
                           port=port,
                           # db=0, encoding="utf-8", decode_responses=True,
                           db=0, decode_responses=True,
                           password=os.environ.get("REDIS_PASS", '***REMOVED***'))
        self._next_session_id_key = 'next_session_id'
        self._all_session_secrets_hash_key = 'all_session_secrets'

        self._session_redis_hash_subkey_ip_address = 'ip_address'
        self._session_redis_hash_subkey_secret = 'secret'
        self._session_redis_hash_subkey_user = 'user'
        self._session_redis_hash_subkey_created = 'created'

    @staticmethod
    def get_key_for_session(session: FullAuthSession):
        return SessionManager.get_key_for_session_by_id(session.session_id)

    @staticmethod
    def get_key_for_session_by_id(session_id):
        return SessionManager._SESSION_KEY_PREFIX + str(session_id)

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

    def remove_session(self, session: FullAuthSession):
        pipeline = self.redis.pipeline()
        pipeline.delete(self.get_key_for_session(session))
        pipeline.hdel(self._all_session_secrets_hash_key, session.session_secret)
        pipeline.execute()









