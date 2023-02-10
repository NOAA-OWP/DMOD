import datetime
import logging
from typing import Optional

from redis.client import Pipeline

from dmod.communication import FullAuthSession, Session, SessionManager
from dmod.redis import RedisBacked


# TODO: add something to periodically scrub sessions due to some expiring criteria
class RedisBackendSessionManager(SessionManager, RedisBacked):
    _LOGGER = None
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
    def get_log_file_name(cls):
        return 'redis_backend_session_manager.log'

    @classmethod
    def get_logger(cls):
        if cls._LOGGER is None:
            logger = logging.getLogger(cls.__name__)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(logging.FileHandler(filename=cls.get_log_file_name()))
            cls._LOGGER = logger
        return cls._LOGGER


    @classmethod
    def get_session_key_prefix(cls):
        return cls._SESSION_KEY_PREFIX

    #@classmethod
    #def get_user_key_prefix(cls):
    #    return cls._USER_KEY_PREFIX

    def __init__(self, redis_host: Optional[str] = None, redis_port: Optional[int] = None,
                 redis_pass: Optional[str] = None):
        super().__init__(redis_host=redis_host, redis_port=redis_port, redis_pass=redis_pass)

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

    def _write_session_via_pipeline(self, session: FullAuthSession, pipeline: Optional[Pipeline] = None,
                                    write_attr_subkeys: Optional[set] = None):
        """
        Persist data for the given session to a Redis hash using the given pipeline (or new one if ``None`` is passed),
        potentially writing only certain attributes based on ``write_attr_subkey``.

        The ``write_attr_subkeys`` param is examined to determine which session attributes should be written.  Only the
        attributes with corresponding valid keys (i.e., keys within :attr:`_session_redis_hash_subkeys_set`) will have
        their data persisted.  If the param is not a set with at least one valid subkey, including cases when the param
        is ``None``, is empty, or is not a set, then all supported attributes have data persisted.

        Parameters
        ----------
        session
        pipeline
        write_attr_subkeys
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
            # Now use are mapping above to have the pipeline hset values appropriately
            for subkey in persistable_values:
                if write_all or subkey in write_attr_subkeys:
                    pipeline.hset(session_key, subkey, persistable_values[subkey])

            # Then write to hashes to reverse lookup (via session id) using other session attributes
            if write_all:
                pipeline.hset(self._all_session_secrets_hash_key, session.session_secret, session.session_id)
                pipeline.hset(self._all_users_hash_key, session.user, session.session_id)

            pipeline.execute()
        except Exception as e:
            self.get_logger().error('Encountered {} instance: {}'.format(e.__class__.__name__, str(e)))
            raise e
        finally:
            if did_internal_init_pipeline:
                pipeline.reset()

    # TODO: test
    def _get_next_session_id_via_pipeline(self, pipeline: Pipeline) -> int:
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
        return session_id

    def create_session(self, ip_address, username) -> FullAuthSession:
        with self.redis.pipeline() as pipeline:
            try:
                pipeline.watch(self._next_session_id_key)

                session_id = self._get_next_session_id_via_pipeline(pipeline)

                session = FullAuthSession(ip_address=ip_address, session_id=session_id, user=username)
                # NOTE: no need to check the next session id in the call below, since we just did that above
                #self._write_session_via_pipeline(session=session, pipeline=pipeline, check_next_id=False)

                # Map the valid subkeys to the values that should be written for them
                persistable_values = {
                    self._session_redis_hash_subkey_ip_address: session.ip_address,
                    self._session_redis_hash_subkey_secret: session.session_secret,
                    self._session_redis_hash_subkey_user: session.user,
                    self._session_redis_hash_subkey_created: session.get_created_serialized(),
                    self._session_redis_hash_subkey_last_accessed: session.get_last_accessed_serialized()
                }

                session_key = self.get_key_for_session(session)

                for subkey in persistable_values:
                    pipeline.hset(session_key, subkey, persistable_values[subkey])

                pipeline.hset(self._all_session_secrets_hash_key, session.session_secret, session.session_id)
                pipeline.hset(self._all_users_hash_key, session.user, session.session_id)

                return session
            except Exception as e:
                self.get_logger().error('Encountered {} instance: {}'.format(e.__class__.__name__, str(e)))
                raise e

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

    def refresh_session(self, session: Session) -> bool:
        if session.is_expired():
            return False
        looked_up = self.lookup_session_by_id(session.session_id)
        if looked_up is None or looked_up.is_expired() or looked_up.session_secret != session.session_secret:
            return False
        new_last_accessed = datetime.datetime.now()
        looked_up.last_accessed = new_last_accessed
        # TODO(later): consider adding a maximum session time to cap refreshes
        attr_write_set = {self._session_redis_hash_subkey_last_accessed}
        pipeline = self.redis.pipeline()
        try:
            self._write_session_via_pipeline(session=looked_up, pipeline=pipeline, write_attr_subkeys=attr_write_set)
            session.last_accessed = new_last_accessed
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
