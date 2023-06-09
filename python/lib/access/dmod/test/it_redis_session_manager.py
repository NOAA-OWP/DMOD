import datetime
import time
import unittest
import os

from dotenv import load_dotenv
from pathlib import Path
from typing import Optional

from ..access.redis_session_manager import FullAuthSession, RedisBackendSessionManager


class IntegrationTestRedisBackendSessionManager(unittest.TestCase):

    # TODO: look at moving this also to environemnt var instead of hard-coding here and in test_package.sh (though this
    # TODO:     would probably required utility helper class for working in the environment)
    _TEST_ENV_FILE_BASENAME = ".test_env"

    @classmethod
    def find_project_root_directory(cls, current_directory: Optional[Path]) -> Optional[Path]:
        """
        Given a directory (with ``None`` implying the current directory) assumed to be at or under this project's root,
        find the project root directory.

        This implementation attempts to find a directory having both a ``.git/`` child directory and a ``.env`` file.

        Parameters
        ----------
        current_directory

        Returns
        -------
        Optional[Path]
            The project root directory, or ``None`` if it fails to find it.
        """
        abs_root = Path(current_directory.absolute().root)
        while current_directory.absolute() != abs_root:
            if not current_directory.is_dir():
                current_directory = current_directory.parent
                continue
            git_sub_dir = current_directory.joinpath('.git')
            child_env_file = current_directory.joinpath('.env')
            if git_sub_dir.exists() and git_sub_dir.is_dir() and child_env_file.exists() and child_env_file.is_file():
                return current_directory
            current_directory = current_directory.parent
        return None

    @classmethod
    def source_env_files(cls, env_file_basename: str):
        current_dir = Path().absolute()

        # Find the global .test_env file from project root, and source
        proj_root = cls.find_project_root_directory(current_dir)
        if proj_root is None:
            raise RuntimeError("Error: unable to find project root directory for integration testing.")

        global_test_env = proj_root.joinpath(env_file_basename)
        if global_test_env.exists():
            load_dotenv(dotenv_path=str(global_test_env.absolute()))

        # Also, search for any other .test_env files, but only source if they are in the same directory as this file
        this_test_file_parent_directory = Path(__file__).parent.absolute()
        for test_env_file in proj_root.glob('**/' + env_file_basename):
            if test_env_file.parent.absolute() == this_test_file_parent_directory:
                load_dotenv(dotenv_path=str(test_env_file))
                # Also, since there can be only one, go ahead and return here
                break

    @classmethod
    def source_env_property(cls, env_var_name: str):
        value = os.getenv(env_var_name, None)
        if value is None:
            cls.source_env_files(cls._TEST_ENV_FILE_BASENAME)
            value = os.getenv(env_var_name, None)
        return value

    def __init__(self, methodName='runTest'):
        super().__init__(methodName=methodName)
        self._redis_test_pass = None
        self._redis_test_port = None

    def _get_next_session_id(self):
        sid_str = self._session_manager.redis.get(self._session_manager._next_session_id_key)
        sid = int(sid_str) if sid_str is not None else 1
        while self._session_manager.redis.hlen(self._session_manager.get_key_for_session_by_id(sid)) != 0:
            sid += 1
        return sid

    def _manual_init_session(self, user, ip_addr, created, last_access_delta):
        """
        Manually init a session object for testing purposes, separately from a full call to ``create_session()``.

        Parameters
        ----------
        user: str
            the session username

        ip_addr: str
            the session host or ip address

        created: datetime.datetime
            the session creation time

        last_access_delta: datetime.timedelta
            the timedelta that implicitly represents the last_access attribute value, relative to the created value

        Returns
        -------
        FullAuthSession
            a new :class:`FullAuthSession` object
        """
        next_id = self._get_next_session_id()
        last_access = created + last_access_delta
        return FullAuthSession(ip_address=ip_addr, user=user, session_id=next_id, created=created,
                               last_accessed=last_access)

    @property
    def redis_test_pass(self):
        if not self._redis_test_pass:
            self._redis_test_pass = self.source_env_property('IT_REDIS_CONTAINER_PASS')
        return self._redis_test_pass

    @property
    def redis_test_port(self):
        if not self._redis_test_port:
            self._redis_test_port = self.source_env_property('IT_REDIS_CONTAINER_HOST_PORT')
        return self._redis_test_port

    def setUp(self) -> None:
        self._session_manager = RedisBackendSessionManager(redis_host='127.0.0.1',
                                                           redis_port=self.redis_test_port,
                                                           redis_pass=self.redis_test_pass)
        self._redis_user_1 = 'test_user_1'
        self._redis_user_2 = 'test_user_2'
        self._redis_user_3 = 'test_user_3'
        self._session_ip_1 = '127.0.0.2'
        self._session_ip_2 = '127.0.0.3'
        self._session_ip_3 = '127.0.0.4'

        self._starting_session_id = self._get_next_session_id()

    def tearDown(self) -> None:
        for sid in range(self._starting_session_id, self._get_next_session_id()):
            session = self._session_manager.lookup_session_by_id(sid)
            if session is not None:
                self._session_manager.remove_session(session)

    def test__write_session_via_pipeline_1_a(self):
        """
        Test that the ``_write_session_via_pipeline()`` method writes as expected and properly updates the next session
        id key, confirmed by checking that the manually created session is written correctly.
        """
        user_1 = self._redis_user_1
        ip_addr_1 = self._session_ip_1
        created_1 = datetime.datetime.now()
        last_access_delta_1 = datetime.timedelta(minutes=5.0)

        user_2 = self._redis_user_2
        ip_addr_2 = self._session_ip_2

        created_session_1 = self._manual_init_session(user=user_1, ip_addr=ip_addr_1, created=created_1,
                                                      last_access_delta=last_access_delta_1)
        if created_session_1.is_expired():
            raise RuntimeError("Manually created session for writing test should not already be expired")

        if self._session_manager.lookup_session_by_id(created_session_1.session_id) is not None:
            raise RuntimeError("Manually created session for writing test should not already have persisted record")

        self._session_manager._write_session_via_pipeline(session=created_session_1, write_attr_subkeys=set())

        created_session_2 = self._session_manager.create_session(ip_address=ip_addr_2, username=user_2)

        lookup_session_1 = self._session_manager.lookup_session_by_id(created_session_1.session_id)

        msg = "Manual written session 1 " + str(created_session_1) + " differs from retrieved " + str(lookup_session_1)
        self.assertTrue(created_session_1.full_equals(lookup_session_1), msg=msg)

    def test__write_session_via_pipeline_1_b(self):
        """
        Test that the ``_write_session_via_pipeline()`` method writes as expected and properly updates the next session
        id key, confirmed by checking that the normally created session is written correctly.
        """
        user_1 = self._redis_user_1
        ip_addr_1 = self._session_ip_1
        created_1 = datetime.datetime.now()
        last_access_delta_1 = datetime.timedelta(minutes=5.0)

        user_2 = self._redis_user_2
        ip_addr_2 = self._session_ip_2

        created_session_1 = self._manual_init_session(user=user_1, ip_addr=ip_addr_1, created=created_1,
                                                      last_access_delta=last_access_delta_1)
        if created_session_1.is_expired():
            raise RuntimeError("Manually created session for writing test should not already be expired")

        if self._session_manager.lookup_session_by_id(created_session_1.session_id) is not None:
            raise RuntimeError("Manually created session for writing test should not already have persisted record")

        self._session_manager._write_session_via_pipeline(session=created_session_1, write_attr_subkeys=set())

        created_session_2 = self._session_manager.create_session(ip_address=ip_addr_2, username=user_2)

        lookup_session_1 = self._session_manager.lookup_session_by_id(created_session_1.session_id)
        lookup_session_2 = self._session_manager.lookup_session_by_id(created_session_2.session_id)

        msg = "Normal session 2 " + str(created_session_2) + " differs from retrieved " + str(lookup_session_2)
        self.assertTrue(created_session_2.full_equals(lookup_session_2), msg=msg)

    def test__write_session_via_pipeline_1_c(self):
        """
        Test that the ``_write_session_via_pipeline()`` method writes as expected and properly updates the next session
        id key, confirmed by checking that the normally created session is written correctly.
        """
        user_1 = self._redis_user_1
        ip_addr_1 = self._session_ip_1
        created_1 = datetime.datetime.now()
        last_access_delta_1 = datetime.timedelta(minutes=5.0)

        user_2 = self._redis_user_2
        ip_addr_2 = self._session_ip_2

        created_session_1 = self._manual_init_session(user=user_1, ip_addr=ip_addr_1, created=created_1,
                                                      last_access_delta=last_access_delta_1)
        if created_session_1.is_expired():
            raise RuntimeError("Manually created session for writing test should not already be expired")

        if self._session_manager.lookup_session_by_id(created_session_1.session_id) is not None:
            raise RuntimeError("Manually created session for writing test should not already have persisted record")

        self._session_manager._write_session_via_pipeline(session=created_session_1, write_attr_subkeys=set())

        created_session_2 = self._session_manager.create_session(ip_address=ip_addr_2, username=user_2)

        lookup_session_1 = self._session_manager.lookup_session_by_secret(created_session_1.session_secret)
        lookup_session_2 = self._session_manager.lookup_session_by_secret(created_session_2.session_secret)

        msg = "Manually created and persisted session did non increment 'next_session_id' for next session properly"
        self.assertTrue(lookup_session_1.session_id + 1 == lookup_session_2.session_id, msg=msg)

    def test__write_session_via_pipeline_2_a(self):
        """
        Test that the ``_write_session_via_pipeline()`` method writes as expected when writing the entire object, with
        no write_attr_subkeys due to it being the default (of ``None``).
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1
        created = datetime.datetime.now()
        last_access_delta = datetime.timedelta(minutes=5.0)

        created_session = self._manual_init_session(user=user, ip_addr=ip_addr, created=created,
                                                    last_access_delta=last_access_delta)
        if created_session.is_expired():
            raise RuntimeError("Manually created session for writing test should not already be expired")

        if self._session_manager.lookup_session_by_id(created_session.session_id) is not None:
            raise RuntimeError("Manually created session for writing test should not already have persisted record")

        self._session_manager._write_session_via_pipeline(session=created_session)
        lookup_session = self._session_manager.lookup_session_by_id(created_session.session_id)
        self.assertTrue(created_session.full_equals(lookup_session))

    def test__write_session_via_pipeline_2_b(self):
        """
        Test that the ``_write_session_via_pipeline()`` method writes as expected when writing the entire object, with
        no write_attr_subkeys due to it being explicitly ``None``.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1
        created = datetime.datetime.now()
        last_access_delta = datetime.timedelta(minutes=5.0)

        created_session = self._manual_init_session(user=user, ip_addr=ip_addr, created=created,
                                                    last_access_delta=last_access_delta)
        if created_session.is_expired():
            raise RuntimeError("Manually created session for writing test should not already be expired")

        if self._session_manager.lookup_session_by_id(created_session.session_id) is not None:
            raise RuntimeError("Manually created session for writing test should not already have persisted record")

        self._session_manager._write_session_via_pipeline(session=created_session, write_attr_subkeys=None)
        lookup_session = self._session_manager.lookup_session_by_id(created_session.session_id)
        self.assertTrue(created_session.full_equals(lookup_session))

    def test__write_session_via_pipeline_2_c(self):
        """
        Test that the ``_write_session_via_pipeline()`` method writes as expected when writing the entire object, with
        no write_attr_subkeys due to it being an empty set.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1
        created = datetime.datetime.now()
        last_access_delta = datetime.timedelta(minutes=5.0)

        created_session = self._manual_init_session(user=user, ip_addr=ip_addr, created=created,
                                                    last_access_delta=last_access_delta)
        if created_session.is_expired():
            raise RuntimeError("Manually created session for writing test should not already be expired")

        if self._session_manager.lookup_session_by_id(created_session.session_id) is not None:
            raise RuntimeError("Manually created session for writing test should not already have persisted record")

        self._session_manager._write_session_via_pipeline(session=created_session, write_attr_subkeys=set())
        lookup_session = self._session_manager.lookup_session_by_id(created_session.session_id)
        self.assertTrue(created_session.full_equals(lookup_session))

    def test__write_session_via_pipeline_2_d(self):
        """
        Test that the ``_write_session_via_pipeline()`` method writes as expected when writing the entire object, with
        no write_attr_subkeys due to it being an non-set object.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1
        created = datetime.datetime.now()
        last_access_delta = datetime.timedelta(minutes=5.0)

        created_session = self._manual_init_session(user=user, ip_addr=ip_addr, created=created,
                                                    last_access_delta=last_access_delta)
        if created_session.is_expired():
            raise RuntimeError("Manually created session for writing test should not already be expired")

        if self._session_manager.lookup_session_by_id(created_session.session_id) is not None:
            raise RuntimeError("Manually created session for writing test should not already have persisted record")

        self._session_manager._write_session_via_pipeline(session=created_session, write_attr_subkeys="blah")
        lookup_session = self._session_manager.lookup_session_by_id(created_session.session_id)
        self.assertTrue(created_session.full_equals(lookup_session))

    def test__write_session_via_pipeline_2_e(self):
        """
        Test that the ``_write_session_via_pipeline()`` method writes as expected when writing the entire object, with
        no write_attr_subkeys due to it being a non-empty set, but without any of the valid subkeys.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1
        created = datetime.datetime.now()
        last_access_delta = datetime.timedelta(minutes=5.0)

        created_session = self._manual_init_session(user=user, ip_addr=ip_addr, created=created,
                                                    last_access_delta=last_access_delta)
        if created_session.is_expired():
            raise RuntimeError("Manually created session for writing test should not already be expired")

        if self._session_manager.lookup_session_by_id(created_session.session_id) is not None:
            raise RuntimeError("Manually created session for writing test should not already have persisted record")

        self._session_manager._write_session_via_pipeline(session=created_session, write_attr_subkeys={"notvalid"})
        lookup_session = self._session_manager.lookup_session_by_id(created_session.session_id)
        self.assertTrue(created_session.full_equals(lookup_session))

    def test__write_session_via_pipeline_2_f(self):
        """
        Test that the ``_write_session_via_pipeline()`` method writes as expected when writing the entire object, with
        no write_attr_subkeys due to it being a non-empty set, but without any of the valid subkeys.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1
        created = datetime.datetime.now()
        last_access_delta = datetime.timedelta(minutes=5.0)

        created_session = self._manual_init_session(user=user, ip_addr=ip_addr, created=created,
                                                    last_access_delta=last_access_delta)
        if created_session.is_expired():
            raise RuntimeError("Manually created session for writing test should not already be expired")

        if self._session_manager.lookup_session_by_id(created_session.session_id) is not None:
            raise RuntimeError("Manually created session for writing test should not already have persisted record")

        self._session_manager._write_session_via_pipeline(session=created_session, write_attr_subkeys={1, 2, 3})
        lookup_session = self._session_manager.lookup_session_by_id(created_session.session_id)
        self.assertTrue(created_session.full_equals(lookup_session))

    def test__write_session_via_pipeline_3_a(self):
        """
        Test that the ``_write_session_via_pipeline()`` method writes as expected when writing a specified subset of
        keys, by checking the persisted value for equality to the modified local copy.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1
        last_access_delta = datetime.timedelta(minutes=5.0)

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)

        # Modify some things, keeping the original values
        attr_modified = set()

        attr_modified.add(self._session_manager._session_redis_hash_subkey_last_accessed)
        original_last_accessed = created_session.last_accessed
        time.sleep(5)
        updated_last_accessed = datetime.datetime.now()
        created_session.last_accessed = updated_last_accessed

        self._session_manager._write_session_via_pipeline(session=created_session, write_attr_subkeys=attr_modified)

        lookup_session = self._session_manager.lookup_session_by_id(created_session.session_id)
        msg = "After manual write of single attribute, lookup did not return expected/equal session value"
        self.assertTrue(created_session.full_equals(lookup_session), msg=msg)

    def test__write_session_via_pipeline_3_b(self):
        """
        Test that the ``_write_session_via_pipeline()`` method writes as expected when writing a specified subset of
        keys.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1
        last_access_delta = datetime.timedelta(minutes=5.0)

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)

        # Modify some things, keeping the original values
        attr_modified = set()

        attr_modified.add(self._session_manager._session_redis_hash_subkey_last_accessed)
        original_last_accessed = created_session.last_accessed
        time.sleep(5)
        updated_last_accessed = datetime.datetime.now()
        created_session.last_accessed = updated_last_accessed

        attr_modified.add(self._session_manager._session_redis_hash_subkey_ip_address)
        original_ip_address = ip_addr
        updated_ip_address = self._session_ip_2
        created_session.ip_address = updated_ip_address

        self._session_manager._write_session_via_pipeline(session=created_session, write_attr_subkeys=attr_modified)

        lookup_session = self._session_manager.lookup_session_by_id(created_session.session_id)
        msg = "After manual write of two attribute, lookup did not return expected/equal session value"
        self.assertTrue(created_session.full_equals(lookup_session), msg=msg)

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

    def test_create_session_4_a(self):
        """
        Test that the ``create_session()`` method properly handles the case when the tracked next session id happens to
        already be in use.
        """
        user_1 = self._redis_user_1
        ip_addr_1 = self._session_ip_1
        created_1 = datetime.datetime.now()
        last_access_delta_1 = datetime.timedelta(minutes=5.0)

        user_2 = self._redis_user_2
        ip_addr_2 = self._session_ip_2

        user_3 = self._redis_user_3
        ip_addr_3 = self._session_ip_3

        created_session_1 = self._manual_init_session(user=user_1, ip_addr=ip_addr_1, created=created_1,
                                                      last_access_delta=last_access_delta_1)
        initial_sid_in_sequence = created_session_1.session_id
        created_session_1.session_id = initial_sid_in_sequence + 1

        if created_session_1.is_expired():
            raise RuntimeError("Manually created session for writing test should not already be expired")

        if self._session_manager.lookup_session_by_id(created_session_1.session_id) is not None:
            raise RuntimeError("Manually created session for writing test should not already have persisted record")

        self._session_manager._write_session_via_pipeline(session=created_session_1)
        created_session_2 = self._session_manager.create_session(ip_address=ip_addr_2, username=user_2)
        created_session_3 = self._session_manager.create_session(ip_address=ip_addr_3, username=user_3)

        self.assertTrue(created_session_2.session_id == initial_sid_in_sequence and created_session_3.session_id == initial_sid_in_sequence + 2)

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

    def test_refresh_session_1_a(self):
        """
        Test that ``refresh_session()`` fails for session argument that has expired.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1
        created = datetime.datetime.now() - datetime.timedelta(hours=2.0)
        last_access_delta = datetime.timedelta(minutes=35.0)

        created_session = self._manual_init_session(user=user, ip_addr=ip_addr, created=created,
                                                    last_access_delta=last_access_delta)
        self.assertFalse(self._session_manager.refresh_session(created_session))

    def test_refresh_session_2_a(self):
        """
        Test that ``refresh_session()`` fails for session without a record.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        self._session_manager.remove_session(created_session)
        self.assertFalse(self._session_manager.refresh_session(created_session))

    def test_refresh_session_2_b(self):
        """
        Test that ``refresh_session()`` fails for session where the argument has not expired but (somehow) the persisted
        record has expired.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1
        created = datetime.datetime.now() - datetime.timedelta(hours=2.0)
        last_access_delta = datetime.timedelta(minutes=35.0)

        created_session = self._manual_init_session(user=user, ip_addr=ip_addr, created=created,
                                                    last_access_delta=last_access_delta)

        self._session_manager._write_session_via_pipeline(session=created_session)
        created_session.last_accessed = datetime.datetime.now()
        if created_session.is_expired():
            raise RuntimeError("Expecting test to have non-expired local session object, but was expired")

        self.assertFalse(self._session_manager.refresh_session(created_session))

    def test_refresh_session_2_c(self):
        """
        Test that ``refresh_session()`` fails for session where the session has not expired but (somehow) the session
        secret values differ between the argument and the persisted record.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        created_session.session_secret = created_session.session_secret + "a"
        self.assertFalse(self._session_manager.refresh_session(created_session))

    def test_refresh_session_3_a(self):
        """
        Test that ``refresh_session()`` succeeds for a new session by returning ``True``.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        refresh_result = self._session_manager.refresh_session(created_session)
        self.assertTrue(refresh_result)

    def test_refresh_session_3_b(self):
        """
        Test that ``refresh_session()`` succeeds for a new session by updating the ``last_accessed`` value of the
        argument object.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        initial_last_accessed = created_session.last_accessed
        time.sleep(1)
        self._session_manager.refresh_session(created_session)

        self.assertTrue(initial_last_accessed < created_session.last_accessed)

    def test_refresh_session_3_c(self):
        """
        Test that ``refresh_session()`` succeeds for a new session by updating the ``last_accessed`` value of the
        argument object, to the expected value.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        time.sleep(1)
        approx_now = datetime.datetime.now()
        self._session_manager.refresh_session(created_session)
        rough_diff = created_session.last_accessed - approx_now
        self.assertTrue(rough_diff < datetime.timedelta(seconds=0.3))

    def test_refresh_session_3_d(self):
        """
        Test that ``refresh_session()`` succeeds for a new session by updating the ``last_accessed`` value of the
        persisted record to the expected value.
        """
        user = self._redis_user_1
        ip_addr = self._session_ip_1

        created_session = self._session_manager.create_session(ip_address=ip_addr, username=user)
        time.sleep(1)
        self._session_manager.refresh_session(created_session)
        lookup_session = self._session_manager.lookup_session_by_id(created_session.session_id)
        self.assertTrue(created_session.full_equals(lookup_session))

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
