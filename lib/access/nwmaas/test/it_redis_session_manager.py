import datetime
import unittest

from ..access.redis_session_manager import FullAuthSession, RedisBackendSessionManager


class IntegrationTestRedisBackendSessionManager(unittest.TestCase):

    def _get_next_session_id(self):
        sid_str = self._session_manager.redis.get(self._session_manager._next_session_id_key)
        return int(sid_str) if sid_str is not None else 1

    def setUp(self) -> None:
        self._session_manager = RedisBackendSessionManager(redis_host='127.0.0.1',
                                                           redis_port=19379,
                                                           redis_pass='***REMOVED***')
        self._redis_user_1 = 'test_user_1'
        self._redis_user_2 = 'test_user_2'
        self._session_ip_1 = '127.0.0.2'
        self._session_ip_2 = '127.0.0.3'

        self._starting_session_id = self._get_next_session_id()

    def tearDown(self) -> None:
        for sid in range(self._starting_session_id, self._get_next_session_id()):
            session = self._session_manager.lookup_session_by_id(sid)
            if session is not None:
                self._session_manager.remove_session(session)

    def test_create_session_1_a(self):
        """
        Test that the ``create_session()`` method returns a valid session as expected.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        self.assertTrue(isinstance(created_session, FullAuthSession))
        self.assertEqual(user, created_session.user)
        self.assertEqual(ip_addr, created_session.ip_address)

    def test_create_session_1_b(self):
        """
        Test that the ``create_session()`` method returns a valid session with the expected username.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        self.assertEqual(user, created_session.user)

    def test_create_session_1_c(self):
        """
        Test that the ``create_session()`` method returns a valid session with the expected ip address.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        self.assertEqual(ip_addr, created_session.ip_address)

    def test_create_session_1_d(self):
        """
        Test that the ``create_session()`` method creates a new, valid session that did not already exist, based on a
        check of creation time.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1
        pre_creation_time = datetime.datetime.now()

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        self.assertTrue(pre_creation_time < created_session.created)

    def test_create_session_2_a(self):
        """
        Test that the ``create_session()`` method creates and persists the returned session, such that it can be looked
        up again via the session id.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        lookup_session = self._session_manager.lookup_session_by_id(created_session.session_id)
        self.assertTrue(created_session.full_equals(lookup_session))

    def test_create_session_2_b(self):
        """
        Test that the ``create_session()`` method creates and persists the returned session, such that it can be looked
        up again via the username.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        lookup_session = self._session_manager.lookup_session_by_username(user)
        self.assertTrue(created_session.full_equals(lookup_session))

    def test_create_session_2_c(self):
        """
        Test that the ``create_session()`` method creates and persists the returned session, such that it can be looked
        up again via the session secret.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        lookup_session = self._session_manager.lookup_session_by_secret(created_session.session_secret)
        self.assertTrue(created_session.full_equals(lookup_session))

    def test_create_session_3_a(self):
        """
        Test that the ``create_session()`` method properly increments the next session id when it creates records.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1
        user_2 = self._redis_user_2
        ip_addr_2 = self._session_ip_2

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        created_session_2 = self._session_manager.create_session(ip_address=ip_addr_2, username=user_2)

        self.assertEqual(created_session.session_id+1, created_session_2.session_id)

    def test_lookup_session_by_id_1_a(self):
        """
        Test that the ``lookup_session_by_id()`` method returns ``None`` when there is no session for a supplied
        id.
        """
        session_id = 0
        self.assertIsNone(self._session_manager.lookup_session_by_id(session_id))

    def test_lookup_session_by_id_1_b(self):
        """
        Test that the ``lookup_session_by_id()`` method returns ``None`` when there is no session for a supplied
        id.
        """
        session_id = 1
        self.assertIsNone(self._session_manager.lookup_session_by_id(session_id))

    def test_lookup_session_by_secret_1_a(self):
        """
        Test that the ``lookup_session_by_secret()`` method returns ``None`` when there is no session for a supplied
        id.
        """
        session_secret = ''
        self.assertIsNone(self._session_manager.lookup_session_by_secret(session_secret))

    def test_lookup_session_by_secret_1_b(self):
        """
        Test that the ``lookup_session_by_secret()`` method returns ``None`` when there is no session for a supplied
        id.
        """
        session_secret = 'abcdefghijklmnopqrstuvwxyz'
        self.assertIsNone(self._session_manager.lookup_session_by_secret(session_secret))

    def test_lookup_session_by_username_1_a(self):
        """
        Test that the ``lookup_session_by_username()`` method returns ``None`` when there is no session for a supplied
        username.
        """
        user = self._redis_user_1
        self.assertIsNone(self._session_manager.lookup_session_by_username(user))

    def test_lookup_session_by_username_1_b(self):
        """
        Test that the ``lookup_session_by_username()`` method returns ``None`` when there is no session for a supplied
        username.
        """
        user = self._redis_user_2
        self.assertIsNone(self._session_manager.lookup_session_by_username(user))

    def test_remove_session_1_a(self):
        """
        Test that ``remove_session()`` properly removes a session.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        session = self._session_manager.lookup_session_by_username(user)
        if session is None:
            session = self._session_manager.create_session(ip_address=ip_addr, username=user)

        self._session_manager.remove_session(session)
        self.assertIsNone(self._session_manager.lookup_session_by_id(session.session_id))

    def test_remove_session_1_b(self):
        """
        Test that ``remove_session()`` properly removes a session.
        """
        user = self._redis_user_2
        ip_addr = self._session_ip_2

        session = self._session_manager.lookup_session_by_username(user)
        if session is None:
            session = self._session_manager.create_session(ip_address=ip_addr, username=user)

        self._session_manager.remove_session(session)
        lookup_session = self._session_manager.lookup_session_by_id(session.session_id)
        self.assertIsNone(lookup_session)

    def test_remove_session_1_c(self):
        """
        Test that ``remove_session()`` removes only the appropriate session.
        """
        user_1 = self._redis_user_1
        ip_addr_1 = self._session_ip_1
        user_2 = self._redis_user_2
        ip_addr_2 = self._session_ip_2

        session_1 = self._session_manager.lookup_session_by_username(user_1)
        if session_1 is None:
            session_1 = self._session_manager.create_session(ip_address=ip_addr_1, username=user_1)

        session_2 = self._session_manager.lookup_session_by_username(user_2)
        if session_2 is None:
            session_2 = self._session_manager.create_session(ip_address=ip_addr_2, username=user_2)

        self._session_manager.remove_session(session_1)

        lookup_session_2 = self._session_manager.lookup_session_by_id(session_2.session_id)
        self.assertTrue(session_2.full_equals(lookup_session_2))
