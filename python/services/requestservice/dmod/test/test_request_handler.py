import asyncio
import hashlib
import json
import jsonschema
from pathlib import Path
from dmod.communication import MessageEventType
#from requestsservice.request_handler import RequestHandler
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
        self.client_ssl_context = TestRequestHandler._client_ssl_context
        self.host_name = TestRequestHandler._host_name
        self.port = '3012'
        self.ssl_dir = TestRequestHandler._ssl_dir
        self.session_secret = hashlib.sha256('blah'.encode('utf-8')).hexdigest()

        self.request_handler = RequestHandler(listen_host=self.host_name, port=self.port, ssl_dir=self.ssl_dir)
        # self.running_handler = asyncio.gather(self._run_handler())
        self.uri = ('wss://{}:'.format(self.host_name) if self.client_ssl_context else 'ws://localhost:') + self.port

    def tearDown(self):
        # asyncio.run(self._stop_handler())
        pass

    # TODO: add implementation-specific/relevant tests
