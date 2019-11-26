import asyncio
import hashlib
import json
import jsonschema
from pathlib import Path
from request_handler.request_handler import RequestHandler, RequestType
from socket import gethostname
import ssl
import unittest


class TestRequestHandler(unittest.TestCase):
    _current_dir = Path(__file__).resolve().parent
    _json_schemas_dir = _current_dir.parent.joinpath('schemas')
    _valid_request_json_file = _json_schemas_dir.joinpath('request.json')
    _valid_auth_json_file = _json_schemas_dir.joinpath('auth.json')

    _client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    _ssl_dir = _current_dir.parent.parent.joinpath('communication', 'ssl')
    _localhost_pem = _ssl_dir.joinpath('certificate.pem')
    _host_name = gethostname()
    # _localhost_pem = Path(__file__).resolve().parents[1].joinpath('macbook_ssl', "certificate.pem")
    # _host_name = 'localhost'
    _client_ssl_context.load_verify_locations(_localhost_pem)

    @staticmethod
    def run_coroutine(coroutine):
        """
        Helper function to run asynchronous coroutines.

        :param coroutine: The asynchronous coroutine to run
        :return: The result of the asynchronous coroutine
        """
        return asyncio.get_event_loop().run_until_complete(coroutine)

    def setUp(self):
        with TestRequestHandler._valid_request_json_file.open(mode='r') as valid_test_file:
            self.test_job_data = json.load(valid_test_file)
        with TestRequestHandler._valid_auth_json_file.open(mode='r') as valid_auth_file:
            self.test_auth_data = json.load(valid_auth_file)
        self.test_job_data['client_id'] = 10

        self.test_request_data = {RequestType.AUTHENTICATION: self.test_auth_data, RequestType.JOB: self.test_job_data}
        self._parse_return_offset = 42
        self.client_ssl_context = TestRequestHandler._client_ssl_context
        self.host_name = TestRequestHandler._host_name
        self.port = '3012'
        self.ssl_dir = TestRequestHandler._ssl_dir
        self.session_secret = hashlib.sha256('blah'.encode('utf-8')).hexdigest()

        self.request_handler = RequestHandler(hostname=self.host_name, port=self.port, ssl_dir=self.ssl_dir)
        # self.running_handler = asyncio.gather(self._run_handler())
        self.uri = ('wss://{}:'.format(self.host_name) if self.client_ssl_context else 'ws://localhost:') + self.port

    def tearDown(self):
        # asyncio.run(self._stop_handler())
        pass

    # async def _run_handler(self):
    #     await self.request_handler.run()
    #
    # async def _stop_handler(self):
    #     await self.request_handler.shutdown()
    #
    # async def websock_try(self):
    #     try:
    #         async with websockets.connect(self.uri, ssl=self.client_ssl_context) as websocket:
    #             client_test = 1
    #             logging.debug("Sending data")
    #             await websocket.send(json.dumps(self.test_request_data))
    #             logging.debug("Data sent")
    #             response = await websocket.recv()
    #             logging.debug("Producer got response: {}".format(response))
    #             assert(int(response) == 42 + client_test)
    #
    #     except websockets.exceptions.ConnectionClosed:
    #         logging.info("Connection Closed at Publisher")
    #     except Exception as e:
    #         logging.error("FS {}".format(e))
    #         raise e

    def _exec_parse(self, test_source: RequestType, session_secret=None, check_for_auth=False):
        if session_secret is not None:
            self.test_request_data[test_source]['session-secret'] = session_secret
        #return_code = self.run_coroutine(self.request_handler.parse(json.dumps(self.test_request_data)))
        return self.run_coroutine(
            self.request_handler.parse_request_type(self.test_request_data[test_source], check_for_auth))

    def test_parse_request_type_1a(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test JOB request example, without checking
        for auth.
        """
        req_type, errors = self._exec_parse(test_source=RequestType.JOB, session_secret=self.session_secret)
        self.assertEqual(req_type, RequestType.JOB)

    def test_parse_request_type_1b(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test JOB request example, checking for
        auth.
        """
        req_type, errors = self._exec_parse(test_source=RequestType.JOB, session_secret=self.session_secret,
                                            check_for_auth=True)
        self.assertEqual(req_type, RequestType.JOB)

    def test_parse_1c(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test JOB request example, but with a
        modified invalid session-secret.
        """
        req_type, errors = self._exec_parse(test_source=RequestType.JOB, session_secret='some_string',
                                            check_for_auth=True)
        self.assertEqual(req_type, RequestType.INVALID)

    def test_parse_1d(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test JOB request example, but modified
        to be without model.
        """
        self.test_job_data.pop('model')
        req_type, errors = self._exec_parse(test_source=RequestType.JOB, session_secret='some_string',
                                            check_for_auth=True)
        self.assertEqual(req_type, RequestType.INVALID)

    def test_parse_2a(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example.
        """
        req_type, errors = self._exec_parse(test_source=RequestType.AUTHENTICATION, session_secret=self.session_secret,
                                            check_for_auth=True)
        self.assertEqual(req_type, RequestType.AUTHENTICATION)

    def test_parse_2b(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        with check_for_auth turned off
        """
        req_type, errors = self._exec_parse(test_source=RequestType.AUTHENTICATION, session_secret=self.session_secret,
                                            check_for_auth=False)
        self.assertEqual(req_type, RequestType.INVALID)

    def test_parse_2c(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        with a modified, too short username
        """
        self.test_auth_data['username'] = 'short'
        req_type, errors = self._exec_parse(test_source=RequestType.AUTHENTICATION, session_secret=self.session_secret,
                                            check_for_auth=True)
        self.assertEqual(req_type, RequestType.INVALID)

    def test_parse_2d(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        with a modified, too short user_secret
        """
        self.test_auth_data['user_secret'] = 'short'
        req_type, errors = self._exec_parse(test_source=RequestType.AUTHENTICATION, session_secret=self.session_secret,
                                            check_for_auth=True)
        self.assertEqual(req_type, RequestType.INVALID)

    def test_parse_2e(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        modified to be missing username
        """
        self.test_auth_data.pop('username')
        req_type, errors = self._exec_parse(test_source=RequestType.AUTHENTICATION, session_secret=self.session_secret,
                                            check_for_auth=True)
        self.assertEqual(req_type, RequestType.INVALID)

    def test_parse_2f(self):
        """
        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        modified to be missing user_secret
        """
        self.test_auth_data.pop('user_secret')
        req_type, errors = self._exec_parse(test_source=RequestType.AUTHENTICATION, session_secret=self.session_secret,
                                            check_for_auth=True)
        self.assertEqual(req_type, RequestType.INVALID)
