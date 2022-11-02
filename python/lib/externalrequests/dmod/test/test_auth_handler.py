import asyncio
import unittest
from dmod.communication import SessionInitFailureReason
from .externalrequests_test_utils import FailureTestingAuthUtil, SucceedTestAuthUtil, TestingSessionManager, TestingSession
from ..externalrequests.auth_handler import AuthHandler, SessionInitMessage, SessionInitResponse


class TestAuthHandler(unittest.TestCase):

    def setUp(self) -> None:
        self.loop = asyncio.get_event_loop()

        self.valid_init_msg_1 = SessionInitMessage(username='test_1', user_secret='test_1')
        # A second init message for the user from msg_1 above, for testing cases when a previous session exists
        self.valid_init_msg_1b = SessionInitMessage(username='test_1', user_secret='test_1')
        self.valid_init_msg_2 = SessionInitMessage(username='test_2', user_secret='test_2')

        self.client_ip_2 = '127.0.0.2'
        self.client_ip_3 = '127.0.0.3'

        self.session_manager = TestingSessionManager()

        self.succeed_auth_util = SucceedTestAuthUtil()
        self.failure_auth_util = FailureTestingAuthUtil()

        # Setting auth to succeed by default for the handler
        self.auth_handler = AuthHandler(self.session_manager, self.succeed_auth_util, self.succeed_auth_util)

    def tearDown(self) -> None:
        pass

    def test_handle_request_1(self):
        """
        Test when a session init request results in failure due to lack of authentication and (though not necessarily
        checked) lack of authorization.
        """
        self.auth_handler._authenticator = self.failure_auth_util
        self.auth_handler._authorizer = self.failure_auth_util

        init_response: SessionInitResponse = self.loop.run_until_complete(
            self.auth_handler.handle_request(self.valid_init_msg_1, client_ip=self.client_ip_2))

        self.assertFalse(init_response.success)
        self.assertEqual(SessionInitFailureReason.AUTHENTICATION_DENIED, init_response.data.reason)

    def test_handle_request_2(self):
        """
        Test when a session init request results in failure due to lack of authentication (though authorization would
        have been successful).
        """
        self.auth_handler._authenticator = self.failure_auth_util

        init_response: SessionInitResponse = self.loop.run_until_complete(
            self.auth_handler.handle_request(self.valid_init_msg_1, client_ip=self.client_ip_2))

        self.assertFalse(init_response.success)
        self.assertEqual(SessionInitFailureReason.AUTHENTICATION_DENIED, init_response.data.reason)

    def test_handle_request_3(self):
        """
        Test when a session init request results in failure due to lack of authorization, though with successful
        authentication.
        """
        self.auth_handler._authorizer = self.failure_auth_util

        init_response: SessionInitResponse = self.loop.run_until_complete(
            self.auth_handler.handle_request(self.valid_init_msg_1, client_ip=self.client_ip_2))

        self.assertFalse(init_response.success)
        self.assertEqual(SessionInitFailureReason.USER_NOT_AUTHORIZED, init_response.data.reason)

    def test_handle_request_4(self):
        """
        Test when a session init request results in success.
        """

        init_response: SessionInitResponse = self.loop.run_until_complete(
            self.auth_handler.handle_request(self.valid_init_msg_1, client_ip=self.client_ip_2))

        self.assertTrue(init_response.success)
        self.assertTrue(isinstance(init_response.data, TestingSession))

    def test_handle_request_5(self):
        """
        Test when a session init request results in success with the expected user in the generated session.
        """

        init_response: SessionInitResponse = self.loop.run_until_complete(
            self.auth_handler.handle_request(self.valid_init_msg_1, client_ip=self.client_ip_2))

        self.assertTrue(init_response.success)
        self.assertEqual(self.valid_init_msg_1.username, init_response.data.user)

    def test_handle_request_5(self):
        """
        Test when a session init request results in success with the expected user in the generated session.
        """

        init_response: SessionInitResponse = self.loop.run_until_complete(
            self.auth_handler.handle_request(self.valid_init_msg_2, client_ip=self.client_ip_2))

        self.assertTrue(init_response.success)
        self.assertEqual(self.valid_init_msg_2.username, init_response.data.user)

    def test_handle_request_6(self):
        """
        Test when a session init request results in success with the expected client address in the generated session.
        """

        init_response: SessionInitResponse = self.loop.run_until_complete(
            self.auth_handler.handle_request(self.valid_init_msg_1, client_ip=self.client_ip_3))

        self.assertTrue(init_response.success)
        self.assertEqual(self.client_ip_3, init_response.data.ip_address)
