import asyncio
import unittest
from dmod.communication import SessionInitFailureReason
from .externalrequests_test_utils import FailureTestingAuthUtil, SucceedTestAuthUtil, TestingSessionManager
from ..externalrequests.auth_handler import InnerSessionAuthUtil, SessionInitMessage


class TestInnerSessionAuthUtil(unittest.TestCase):

    def setUp(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.valid_init_msg_1 = SessionInitMessage(username='test_1', user_secret='test_1')
        # A second init message for the user from msg_1 above, for testing cases when a previous session exists
        self.valid_init_msg_1b = SessionInitMessage(username='test_1', user_secret='test_1')
        self.valid_init_msg_2 = SessionInitMessage(username='test_2', user_secret='test_2')
        self.client_ip_2 = '127.0.0.2'
        self.session_manager = TestingSessionManager()
        pass

    def tearDown(self) -> None:
        pass

    def test_failure_info_1(self):
        """
        Test behavior of ``failure_info`` property (and also ``session``) authentication fails.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=FailureTestingAuthUtil(),
                                         authorizer=SucceedTestAuthUtil())

        failure_info = self.loop.run_until_complete(auth_util.failure_info)
        session = self.loop.run_until_complete(auth_util.session)

        # failure info should not be None, and session SHOULD be None in this case
        self.assertIsNotNone(failure_info)
        self.assertIsNone(session)
        self.assertEqual(failure_info.reason, SessionInitFailureReason.AUTHENTICATION_DENIED)

    def test_failure_info_2(self):
        """
        Test behavior of ``failure_info`` property (and also ``session``) when authorization fails.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=FailureTestingAuthUtil())

        failure_info = self.loop.run_until_complete(auth_util.failure_info)
        session = self.loop.run_until_complete(auth_util.session)

        # failure info should not be None, and session SHOULD be None in this case
        self.assertIsNotNone(failure_info)
        self.assertIsNone(session)
        self.assertEqual(failure_info.reason, SessionInitFailureReason.USER_NOT_AUTHORIZED)

    def test_is_authenticated_1(self):
        """
        Test behavior of ``is_authenticated`` property when authentication is against "always-succeeds" authenticator.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=SucceedTestAuthUtil())
        is_authentic = self.loop.run_until_complete(auth_util.is_authenticated)
        self.assertTrue(is_authentic)

    def test_is_authenticated_2(self):
        """
        Test behavior of ``is_authenticated`` property when authentication is against "always-fails" authenticator.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=FailureTestingAuthUtil(),
                                         authorizer=FailureTestingAuthUtil())
        is_authentic = self.loop.run_until_complete(auth_util.is_authenticated)
        self.assertFalse(is_authentic)

    def test_is_authorized_1(self):
        """
        Test behavior of ``is_authorized`` property when authenticator determines authentic and authorizer determines
        authorized.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=SucceedTestAuthUtil())
        is_authorized = self.loop.run_until_complete(auth_util.is_authorized)
        self.assertTrue(is_authorized)

    def test_is_authorized_2(self):
        """
        Test behavior of ``is_authorized`` property when authenticator determines authentic but authorizer determines
        not authorized.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=FailureTestingAuthUtil())
        is_authorized = self.loop.run_until_complete(auth_util.is_authorized)
        self.assertFalse(is_authorized)

    def test_is_authorized_3(self):
        """
        Test behavior of ``is_authorized`` property when authenticator does not determine authentic and authorizer
        determines (or at least would determine) not authorized.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=FailureTestingAuthUtil(),
                                         authorizer=FailureTestingAuthUtil())
        is_authorized = self.loop.run_until_complete(auth_util.is_authorized)
        self.assertFalse(is_authorized)

    def test_is_authorized_4(self):
        """
        Test behavior of ``is_authorized`` property when authorizer would determine authorized, but authenticator does
        not determine authentic.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=FailureTestingAuthUtil(),
                                         authorizer=SucceedTestAuthUtil())
        is_authorized = self.loop.run_until_complete(auth_util.is_authorized)
        self.assertFalse(is_authorized)

    def test_is_needs_new_session_1(self):
        """
        Test behavior of ``is_needs_new_session`` property when authenticator does not determine authentic and
        authorizer determines (or at least would determine) not authorized
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=FailureTestingAuthUtil(),
                                         authorizer=FailureTestingAuthUtil())
        is_needs_new_session = self.loop.run_until_complete(auth_util.is_needs_new_session)
        self.assertFalse(is_needs_new_session)

    def test_is_needs_new_session_2(self):
        """
        Test behavior of ``is_needs_new_session`` property when authenticator does determine authentic but authorizer
        determines not authorized
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=FailureTestingAuthUtil())
        is_needs_new_session = self.loop.run_until_complete(auth_util.is_needs_new_session)
        self.assertFalse(is_needs_new_session)

    def test_is_needs_new_session_3(self):
        """
        Test behavior of ``is_needs_new_session`` property when authenticator does determine authentic and authorizer
        determines authorized, when there is no other session for this user or any other users.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=SucceedTestAuthUtil())
        is_needs_new_session = self.loop.run_until_complete(auth_util.is_needs_new_session)
        self.assertTrue(is_needs_new_session)

    def test_is_needs_new_session_4(self):
        """
        Test behavior of ``is_needs_new_session`` property when authenticator does determine authentic and authorizer
        determines authorized, when there is no other session for this user but are for other users.
        """
        other_auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_2,
                                               session_ip_addr=self.client_ip_2,
                                               session_manager=self.session_manager,
                                               authenticator=SucceedTestAuthUtil(),
                                               authorizer=SucceedTestAuthUtil())
        other_user_session = self.loop.run_until_complete(other_auth_util.session)
        self.assertIsNotNone(other_user_session)

        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=SucceedTestAuthUtil())
        is_needs_new_session = self.loop.run_until_complete(auth_util.is_needs_new_session)
        self.assertTrue(is_needs_new_session)

    def test_is_needs_new_session_5(self):
        """
        Test behavior of ``is_needs_new_session`` property when authenticator does determine authentic and authorizer
        determines authorized, when there is another session for this user.
        """
        other_auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                               session_ip_addr=self.client_ip_2,
                                               session_manager=self.session_manager,
                                               authenticator=SucceedTestAuthUtil(),
                                               authorizer=SucceedTestAuthUtil())
        original_user_session = self.loop.run_until_complete(other_auth_util.session)
        self.assertIsNotNone(original_user_session)

        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1b,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=SucceedTestAuthUtil())
        is_needs_new_session = self.loop.run_until_complete(auth_util.is_needs_new_session)
        self.assertFalse(is_needs_new_session)

    def test_newly_created_1(self):
        """
        Test behavior of ``newly_created`` property when authenticator does determine authentic and authorizer
        determines authorized, when there is no other session for this user, or any other users.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=SucceedTestAuthUtil())
        session = self.loop.run_until_complete(auth_util.session)
        self.assertIsNotNone(session)
        is_newly_created = self.loop.run_until_complete(auth_util.newly_created)
        self.assertTrue(is_newly_created)

    def test_newly_created_2(self):
        """
        Test behavior of ``newly_created`` property when authenticator does determine authentic and authorizer
        determines authorized, when there is no other session for this user, but are for other users.
        """
        other_auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_2,
                                               session_ip_addr=self.client_ip_2,
                                               session_manager=self.session_manager,
                                               authenticator=SucceedTestAuthUtil(),
                                               authorizer=SucceedTestAuthUtil())
        other_user_session = self.loop.run_until_complete(other_auth_util.session)
        self.assertIsNotNone(other_user_session)

        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=SucceedTestAuthUtil())
        session = self.loop.run_until_complete(auth_util.session)
        self.assertIsNotNone(session)
        is_newly_created = self.loop.run_until_complete(auth_util.newly_created)
        self.assertTrue(is_newly_created)

    def test_newly_created_3(self):
        """
        Test behavior of ``newly_created`` property when authenticator does not determine authentic.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=FailureTestingAuthUtil(),
                                         authorizer=SucceedTestAuthUtil())
        session = self.loop.run_until_complete(auth_util.session)
        self.assertIsNone(session)
        is_newly_created = self.loop.run_until_complete(auth_util.newly_created)
        self.assertFalse(is_newly_created)

    def test_newly_created_4(self):
        """
        Test behavior of ``newly_created`` property when authenticator does determine authentic but authorizer does not
        determine authorized.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=FailureTestingAuthUtil())
        session = self.loop.run_until_complete(auth_util.session)
        self.assertIsNone(session)
        is_newly_created = self.loop.run_until_complete(auth_util.newly_created)
        self.assertFalse(is_newly_created)

    def test_newly_created_5(self):
        """
        Test behavior of ``newly_created`` property when authenticator does determine authentic and authorizer
        determines authorized, when there is another session for this user.
        """
        other_auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                               session_ip_addr=self.client_ip_2,
                                               session_manager=self.session_manager,
                                               authenticator=SucceedTestAuthUtil(),
                                               authorizer=SucceedTestAuthUtil())
        original_user_session = self.loop.run_until_complete(other_auth_util.session)
        self.assertIsNotNone(original_user_session)

        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1b,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=SucceedTestAuthUtil())
        session = self.loop.run_until_complete(auth_util.session)
        self.assertIsNotNone(session)
        is_newly_created = self.loop.run_until_complete(auth_util.newly_created)
        self.assertFalse(is_newly_created)

    def test_session_1(self):
        """
        Test behavior of ``session`` property (and also ``failure_info``)  authentication and authorization are both
        successful.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=self.valid_init_msg_1,
                                         session_ip_addr=self.client_ip_2,
                                         session_manager=self.session_manager,
                                         authenticator=SucceedTestAuthUtil(),
                                         authorizer=SucceedTestAuthUtil())

        failure_info = self.loop.run_until_complete(auth_util.failure_info)
        session = self.loop.run_until_complete(auth_util.session)

        self.assertIsNone(failure_info)
        self.assertIsNotNone(session)
        self.assertEqual(self.valid_init_msg_1.username, session.user)
        self.assertEqual(self.client_ip_2, session.ip_address)
