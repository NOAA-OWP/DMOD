import asyncio
import hashlib
import json
import jsonschema
from pathlib import Path
from request_handler.request_handler import RequestHandler, RequestType
from socket import gethostname
import ssl
import unittest

#TODO Not sure this implemented correctly for python unittest
class TestWebSocketInterface(unittest.TestCase):
    _current_dir = Path(__file__).resolve().parent

    _client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    _localhost_pem = _current_dir.parent.joinpath('ssl', 'certificate.pem')
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
        self.client_ssl_context = TestRequestHandler._client_ssl_context
        self.host_name = TestRequestHandler._host_name
        self.port = '3012'
        self.request_handler = RequestHandler(hostname=self.host_name, port=self.port)
        # self.running_handler = asyncio.gather(self._run_handler())
        self.uri = ('wss://{}:'.format(self.host_name) if self.client_ssl_context else 'ws://localhost:') + self.port

    def tearDown(self):
        # asyncio.run(self._stop_handler())
        pass

    def test_NoOpCommHandler_listener(self):
        """
        Test the listener of the NoOpCommHandler
        """
        async with websockets.connect(self.uri, ssl=self.client_ssl_context) as websocket:
                     logging.debug("Sending data")
                     await websocket.send("")

if __name__ == '__main__':
    unittest.main()
