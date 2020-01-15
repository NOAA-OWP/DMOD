import os
import datetime
from typing import Optional

from redis import Redis
from redis.client import Pipeline

from nwmaas.communication import FullAuthSession, Session, SessionManager


# TODO: add something to periodically scrub sessions due to some expiring criteria
class RedisBackendSessionManager(SessionManager):
    _DEFAULT_REDIS_HOST = 'redis'
    _DEFAULT_REDIS_PASS = ''
    _DEFAULT_REDIS_PORT = 6379

    _ENV_NAME_REDIS_HOST = 'REDIS_HOST'
    _ENV_NAME_REDIS_PASS = 'REDIS_PASS'
    _ENV_NAME_REDIS_PORT = 'REDIS_PORT'

    _SESSION_KEY_PREFIX = 'session:'
    _SESSION_HASH_SUBKEY_SECRET = 'secret'
    _SESSION_HASH_SUBKEY_CREATED = 'created'
    #_USER_KEY_PREFIX = 'user:'
    #_USER_HASH_SUBKEY_ACCESS_TYPES = 'access_types'

    @classmethod
    def get_initial_session_id_value(cls):
        """
        Get the first value value for session id values, used to bootstrap ids when the last-used id can't be looked up.

        Note this is primarily used when ids are iterative, or at least deterministically ordered.  However, it should
        still return a valid value (though not necessarily the same value for each invocation) even if ids are not
        deterministically ordered for the subclass implementation.

        For this implementation, since the class uses incrementing numeric ids, the starting value is simply ``1``.

        Returns
        -------
        int
            The starting id value for sessions, which for this type is always ``1``.
        """
        return 1

    @classmethod
    def get_key_for_session(cls, session: FullAuthSession):
        return cls.get_key_for_session_by_id(session.session_id)

    @classmethod
    def get_key_for_session_by_id(cls, session_id):
        return cls.get_session_key_prefix() + str(session_id)

    @classmethod
    def get_redis_host(cls):
        return os.getenv(cls._ENV_NAME_REDIS_HOST, cls._DEFAULT_REDIS_HOST)

    @classmethod
    def get_redis_pass(cls):
        return os.getenv(cls._ENV_NAME_REDIS_PASS, cls._DEFAULT_REDIS_PASS)

    @classmethod
    def get_redis_port(cls):
        return os.getenv(cls._ENV_NAME_REDIS_PORT, cls._DEFAULT_REDIS_PORT)

    @classmethod
    def get_session_key_prefix(cls):
        return cls._SESSION_KEY_PREFIX

    #@classmethod
    #def get_user_key_prefix(cls):
    #    return cls._USER_KEY_PREFIX

    def __init__(self, redis_host: Optional[str] = None, redis_port: Optional[int] = None,
                 redis_pass: Optional[str] = None):
        self._redis = None
        self._redis_host = redis_host if redis_host is not None else self.get_redis_host()
        self._redis_port = redis_port if redis_port is not None else self.get_redis_port()
        self._redis_pass = redis_pass if redis_pass is not None else self.get_redis_pass()

        self._next_session_id_key = 'next_session_id'

        # Keys for hashes created to do fast reverse-lookup for session ids (generally to then lookup the sessions)
        self._all_session_secrets_hash_key = 'all_session_secrets'
        self._all_users_hash_key = 'all_users'

        self._session_redis_hash_subkey_ip_address = 'ip_address'
        self._session_redis_hash_subkey_secret = 'secret'
        self._session_redis_hash_subkey_user = 'user'
        self._session_redis_hash_subkey_created = 'created'
        self._session_redis_hash_subkey_last_accessed = 'last_accessed'

        self._session_redis_hash_subkeys_set = {self._session_redis_hash_subkey_ip_address,
                                                self._session_redis_hash_subkey_secret,
                                                self._session_redis_hash_subkey_user,
                                                self._session_redis_hash_subkey_created,
                                                self._session_redis_hash_subkey_last_accessed}

    def _update_session_record(self, session: FullAuthSession, pipeline: Pipeline, do_ip_address=False, do_secret=False,
                               do_user=False):
        """
        Append to the execution tasks (without triggering execution) of a provided Pipeline to update appropriate
        properties of a serialized Session hash record in Redis.

        Parameters
        ----------
        session: DetailedSession
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

    def _write_session_via_pipeline(self, session: FullAuthSession, pipeline: Optional[Pipeline] = None,
                                    write_attr_subkeys: Optional[set] = None, check_next_id: bool = True):
        """
        Persist data for the given session to a Redis hash using the given pipeline (or new one if ``None`` is passed),
        potentially writing only certain attributes based on ``write_attr_subkey``.

        The ``write_attr_subkeys`` param is examined to determine which session attributes should be written.  Only the
        attributes with corresponding valid keys (i.e., keys within :attr:`_session_redis_hash_subkeys_set`) will have
        their data persisted.  If the param is not a set with at least one valid subkey, including cases when the param
        is ``None``, is empty, or is not a set, then all supported attributes have data persisted.

        If ``check_next_id`` is ``True``, which is the default, the method will also examine the value at the
        :attr:`_next_session_id_key` key to get the next new session id.  If the session provided has this same id, then
        the value of the next new session id will be incremented.

        Parameters
        ----------
        session
        pipeline
        write_attr_subkeys
        check_next_id
        """
        # Optimize by doing the various checks to see if everything should be written ...
        if write_attr_subkeys is None or not isinstance(write_attr_subkeys, set) or len(write_attr_subkeys) == 0:
            write_all = True
        # ... including if the param is non-empty but doesn't hold any valid subkeys
        else:
            valid_subkey_count = 0
            for si in write_attr_subkeys:
                if si in self._session_redis_hash_subkeys_set:
                    valid_subkey_count += 1
            write_all = valid_subkey_count == 0

        session_key = self.get_key_for_session(session)

        # Map the valid subkeys to the values that should be written for them, to make logic a little more elegant below
        persistable_values = {self._session_redis_hash_subkey_ip_address: session.ip_address,
                              self._session_redis_hash_subkey_secret: session.session_secret,
                              self._session_redis_hash_subkey_user: session.user,
                              self._session_redis_hash_subkey_created: session.get_created_serialized(),
                              self._session_redis_hash_subkey_last_accessed: session.get_last_accessed_serialized()}

        did_internal_init_pipeline = False
        if pipeline is None or not isinstance(pipeline, Pipeline):
            pipeline = self.redis.pipeline()
            did_internal_init_pipeline = True

        try:
            if check_next_id:
                pipeline.watch(self._next_session_id_key)
                # Remember, Redis only persists strings (though it can implicitly convert from int to string on its side)
                current_next_id = pipeline.get(self._next_session_id_key)
                if current_next_id is not None and int(current_next_id) == session.session_id:
                    pipeline.incr(self._next_session_id_key, 1)

            # Now use are mapping above to have the pipeline hset values appropriately
            for subkey in persistable_values:
                if write_all or subkey in write_attr_subkeys:
                    pipeline.hset(session_key, subkey, persistable_values[subkey])

            # Then write to hashes to reverse lookup (via session id) using other session attributes, if writing everything
            if write_all:
                pipeline.hset(self._all_session_secrets_hash_key, session.session_secret, session.session_id)
                pipeline.hset(self._all_users_hash_key, session.user, session.session_id)

            pipeline.execute()
        finally:
            if check_next_id:
                pipeline.unwatch()
            if did_internal_init_pipeline:
                pipeline.reset()

    def create_session(self, ip_address, username) -> FullAuthSession:
        pipeline = self.redis.pipeline()
        try:
            pipeline.watch(self._next_session_id_key)

            # Do this in a loop to account for (unlikely) possibility that someone manually used a key out of order
            session_id = None
            while session_id is None:
                # Get a session id, base on stored (or initialized) value at _next_session_id_key, then bump said value
                # Remember, Redis persists strings (though it can implicitly convert from int to string on its side)
                session_id_str: Optional[str] = pipeline.get(self._next_session_id_key)
                if session_id_str is None:
                    session_id = self.get_initial_session_id_value()
                    pipeline.set(self._next_session_id_key, session_id + 1)
                else:
                    session_id = int(session_id_str)
                    pipeline.incr(self._next_session_id_key, 1)
                # However, if the key is already in use (via manual selection), we have to try again
                if pipeline.hlen(self.get_key_for_session_by_id(session_id)) != 0:
                    session_id = None

            session = FullAuthSession(ip_address=ip_address, session_id=session_id, user=username)
            # NOTE: no need to check the next session id in the call below, since we just did that above
            self._write_session_via_pipeline(session=session, pipeline=pipeline, check_next_id=False)
            return session
        finally:
            pipeline.unwatch()
            pipeline.reset()

    def lookup_session_by_id(self, session_id: int) -> Optional[FullAuthSession]:
        record_hash = self.redis.hgetall(self.get_key_for_session_by_id(session_id))
        # Comes back from Redis as a dict, perhaps empty if nothing is found for this session id
        if record_hash is None or len(record_hash) == 0:
            return None
        return FullAuthSession(session_id=session_id,
                               session_secret=record_hash[self._session_redis_hash_subkey_secret],
                               created=record_hash[self._session_redis_hash_subkey_created],
                               ip_address=record_hash[self._session_redis_hash_subkey_ip_address],
                               user=record_hash[self._session_redis_hash_subkey_user],
                               last_accessed=record_hash[self._session_redis_hash_subkey_last_accessed])

    def lookup_session_by_secret(self, session_secret: str) -> Optional[FullAuthSession]:
        session_id: Optional[str] = self.redis.hget(self._all_session_secrets_hash_key, session_secret)
        return None if session_id is None else self.lookup_session_by_id(int(session_id))

    def lookup_session_by_username(self, username: str) -> Optional[FullAuthSession]:
        session_id: Optional[str] = self.redis.hget(self._all_users_hash_key, username)
        return None if session_id is None else self.lookup_session_by_id(int(session_id))

    @property
    def redis(self):
        if self._redis is None:
            self._redis = Redis(host=self._redis_host,
                                port=self._redis_port,
                                db=0,
                                decode_responses=True,
                                password=self._redis_pass)
        return self._redis

    def refresh_session(self, session: Session) -> bool:
        if session.is_expired():
            return False
        looked_up = self.lookup_session_by_id(session.session_id)
        if looked_up is None or looked_up.is_expired() or looked_up.session_secret != session.session_secret:
            return False
        new_last_accessed = datetime.datetime.now()
        looked_up._last_accessed = new_last_accessed
        # TODO(later): consider adding a maximum session time to cap refreshes
        pipeline = self.redis.pipeline()
        attr_write_set = {self._session_redis_hash_subkey_last_accessed}
        try:
            self._write_session_via_pipeline(session=looked_up, pipeline=pipeline, write_attr_subkeys=attr_write_set)
            session._last_accessed = new_last_accessed
            return True
        finally:
            pipeline.reset()

    def remove_session(self, session: FullAuthSession):
        pipeline = self.redis.pipeline()
        pipeline.delete(self.get_key_for_session(session))

        # Then cleanup reverse-lookup hashes
        pipeline.hdel(self._all_session_secrets_hash_key, session.session_secret)
        pipeline.hdel(self._all_users_hash_key, session.user)

        pipeline.execute()

    def user_has_valid_session(self, username: str):
        pass
