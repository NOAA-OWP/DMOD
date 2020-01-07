import asyncio
import hashlib
import json
import os
import signal
import ssl
import sys
import unittest
from ..communication.message import MessageEventType
from ..communication.websocket_interface import NoOpHandler
from pathlib import Path
from socket import gethostname
import websockets


class WebSocketInterfaceTestBase(unittest.TestCase):

    _current_dir = Path(__file__).resolve().parent
    _json_schemas_dir = _current_dir.parent.joinpath('communication', 'schemas')
    _valid_request_json_file = _json_schemas_dir.joinpath('request.json')
    _valid_auth_json_file = _json_schemas_dir.joinpath('auth.json')

    @staticmethod
    def run_coroutine(coroutine):
        """
        Helper function to run asynchronous coroutines.

        :param coroutine: The asynchronous coroutine to run
        :return: The result of the asynchronous coroutine
        """
        return asyncio.get_event_loop().run_until_complete(coroutine)

    @staticmethod
    async def async_run_subproc_from_code(sub_proc_code: str) -> asyncio.subprocess.Process:
        """
        Helper function for creating and running a Python subprocess executing the given string as Python code.

        Parameters
        ----------
        sub_proc_code: str
            Python code to execute in the subprocess

        Returns
        -------
        The started subprocess object
        """
        return await asyncio.create_subprocess_exec(sys.executable, '-c', sub_proc_code, stdout=asyncio.subprocess.PIPE)

    def setUp(self):
        test_dir_name = os.getenv('TEST_SSL_CERT_DIR')
        if test_dir_name is None:
            self.test_ssl_dir = Path(__file__).resolve().parent.joinpath('ssl')
        else:
            self.test_ssl_dir = Path(test_dir_name).resolve()

        self._client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._client_ssl_context.load_verify_locations(self.test_ssl_dir.joinpath('certificate.pem'))

        self.port = '3012'
        self.host = gethostname()

        self.uri = 'wss://{}:'.format(self.host) + self.port

    def tearDown(self):
        pass


class TestWebSocketInterface(WebSocketInterfaceTestBase):

    def setUp(self):
        super().setUp()
        with self.__class__._valid_request_json_file.open(mode='r') as valid_test_file:
            self.test_job_data = json.load(valid_test_file)
        with self.__class__._valid_auth_json_file.open(mode='r') as valid_auth_file:
            self.test_auth_data = json.load(valid_auth_file)
        self.test_job_data['client_id'] = 10

        self.test_request_data = {MessageEventType.SESSION_INIT: self.test_auth_data, MessageEventType.NWM_MAAS_REQUEST: self.test_job_data}
        self._parse_return_offset = 42

        self.session_secret = hashlib.sha256('blah'.encode('utf-8')).hexdigest()
        self.request_handler = NoOpHandler(listen_host=self.host, port=self.port, ssl_dir=self.test_ssl_dir)

    def _exec_parse(self, test_source: MessageEventType, session_secret=None, check_for_auth=False):
        if session_secret is not None:
            self.test_request_data[test_source]['session-secret'] = session_secret
        #return_code = self.run_coroutine(self.request_handler.parse(json.dumps(self.test_request_data)))
        return self.request_handler.loop.run_until_complete(
            self.request_handler.parse_request_type(self.test_request_data[test_source], check_for_auth))

    def test_parse_request_type_1a(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test JOB request example, without checking
        for auth.
        """
        req_type, errors = self._exec_parse(test_source=MessageEventType.NWM_MAAS_REQUEST, session_secret=self.session_secret)
        self.assertEqual(req_type, MessageEventType.NWM_MAAS_REQUEST)

    def test_parse_request_type_1b(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test JOB request example, checking for
        auth.
        """
        req_type, errors = self._exec_parse(test_source=MessageEventType.NWM_MAAS_REQUEST, session_secret=self.session_secret,
                                            check_for_auth=True)
        self.assertEqual(req_type, MessageEventType.NWM_MAAS_REQUEST)

    def test_parse_request_type_1c(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test JOB request example, but with a
        modified invalid session-secret.
        """
        req_type, errors = self._exec_parse(test_source=MessageEventType.NWM_MAAS_REQUEST, session_secret='some_string',
                                            check_for_auth=True)
        self.assertEqual(req_type, MessageEventType.INVALID)

    def test_parse_request_type_1d(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test JOB request example, but modified
        to be without model.
        """
        self.test_job_data.pop('model')
        req_type, errors = self._exec_parse(test_source=MessageEventType.NWM_MAAS_REQUEST, session_secret='some_string',
                                            check_for_auth=True)
        self.assertEqual(req_type, MessageEventType.INVALID)

    def test_parse_request_type_2a(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example.
        """
        req_type, errors = self._exec_parse(test_source=MessageEventType.SESSION_INIT, session_secret=self.session_secret,
                                            check_for_auth=True)
        self.assertEqual(req_type, MessageEventType.SESSION_INIT)

    def test_parse_request_type_2b(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        with check_for_auth turned off
        """
        req_type, errors = self._exec_parse(test_source=MessageEventType.SESSION_INIT, session_secret=self.session_secret,
                                            check_for_auth=False)
        self.assertEqual(req_type, MessageEventType.INVALID)

    def test_parse_request_type_2c(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        with a modified, too short username
        """
        self.test_auth_data['username'] = 'short'
        req_type, errors = self._exec_parse(test_source=MessageEventType.SESSION_INIT, session_secret=self.session_secret,
                                            check_for_auth=True)
        self.assertEqual(req_type, MessageEventType.INVALID)

    def test_parse_request_type_2d(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        with a modified, too short user_secret
        """
        self.test_auth_data['user_secret'] = 'short'
        req_type, errors = self._exec_parse(test_source=MessageEventType.SESSION_INIT, session_secret=self.session_secret,
                                            check_for_auth=True)
        self.assertEqual(req_type, MessageEventType.INVALID)

    def test_parse_request_type_2e(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        modified to be missing username
        """
        self.test_auth_data.pop('username')
        req_type, errors = self._exec_parse(test_source=MessageEventType.SESSION_INIT, session_secret=self.session_secret,
                                            check_for_auth=True)
        self.assertEqual(req_type, MessageEventType.INVALID)

    def test_parse_request_type_2f(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        modified to be missing user_secret
        """
        self.test_auth_data.pop('user_secret')
        req_type, errors = self._exec_parse(test_source=MessageEventType.SESSION_INIT, session_secret=self.session_secret,
                                            check_for_auth=True)
        self.assertEqual(req_type, MessageEventType.INVALID)


if __name__ == '__main__':
    unittest.main()
