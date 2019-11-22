import asyncio
import json
import jsonschema
import ssl
import unittest
from socket import gethostname
from request_handler.request_handler.RequestHandler import RequestHandler
from pathlib import Path


class TestRequestHandler(unittest.TestCase):
    _current_dir = Path(__file__).resolve().parent
    _json_schemas_dir = _current_dir.parent.joinpath('schemas')
    _valid_request_json_file = _json_schemas_dir.joinpath('request.json')

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
        with TestRequestHandler._valid_request_json_file.open(mode='r') as valid_test_file:
            self.test_request_data = json.load(valid_test_file)

        self._parse_return_offset = 42
        self.client_ssl_context = TestRequestHandler._client_ssl_context
        self.host_name = TestRequestHandler._host_name
        self.port = '3012'

        self.request_handler = RequestHandler(hostname=self.host_name, port=self.port)
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

    def _test_parse_with_set_client_id(self, client_id):
        self.test_request_data['client_id'] = client_id
        expected_return_code = client_id + self._parse_return_offset
        return_code = self.run_coroutine(self.request_handler.parse(json.dumps(self.test_request_data)))
        self.assertEqual(expected_return_code, return_code)

    def test_parse_1(self):
        """
        Test the parse method of the RequestHandler class with the valid 'client_id' value of 1.
        """
        self._test_parse_with_set_client_id(client_id=1)

    def test_parse_2(self):
        """
        Test the parse method of the RequestHandler class with the invalid 'client_id' value of 'some_string'.

        At present, the schema requires 'client_id' to be a number.
        """
        self.test_request_data['client_id'] = 'some_string'
        with self.assertRaises(jsonschema.exceptions.ValidationError) as context_manager:
            self.run_coroutine(self.request_handler.parse(json.dumps(self.test_request_data)))

    def test_parse_3(self):
        """
        Test the parse method of the RequestHandler class with the valid 'client_id' value of 25.
        """
        self._test_parse_with_set_client_id(client_id=25)

    def test_parse_4(self):
        """
        Test the parse method of the RequestHandler class with a invalid request, due to it lacking a 'model' property.
        """
        self.test_request_data.pop('model')
        with self.assertRaises(jsonschema.exceptions.ValidationError) as context_manager:
            self.run_coroutine(self.request_handler.parse(json.dumps(self.test_request_data)))

    def test_parse_5(self):
        """
        Test the parse method of the RequestHandler class with the unexpected, but valid, 'client_id' value of 33.5.

        The schema currently dictates that the 'client_id' value need only be a number, thus float values should also
        be supported and behave as expected.
        """
        self._test_parse_with_set_client_id(client_id=33.5)
