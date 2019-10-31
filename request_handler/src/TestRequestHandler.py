import asyncio
import json
import jsonschema
import os
import pathlib
import ssl
import unittest
from socket import gethostname
from .RequestHandler import RequestHandler


class TestRequestHandler(unittest.TestCase):

    _client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    _localhost_pem = pathlib.Path(__file__).parent.joinpath('ssl', "certificate.pem")
    _host_name = gethostname()
    #localhost_pem = pathlib.Path(__file__).resolve().parents[1].joinpath('macbook_ssl', "certificate.pem")
    #hostname = 'localhost'
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
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self._parse_return_offset = 42
        self.client_ssl_context = self._client_ssl_context
        self.host_name = 'localhost'
        self.port = '3012'
        self.path_request_json_file = current_dir + '/schemas/request.json'
        with open(self.path_request_json_file, 'r') as test_file:
            self.test_request_data = json.load(test_file)
        self.request_handler = RequestHandler(hostname=self.host_name, port=self.port)
        #self.running_handler = asyncio.create_task(self.run_handler())
        self.uri = ('wss://{}:'.format(self.host_name) if self.client_ssl_context else 'ws://localhost:') + self.port

    def tearDown(self):
        pass

    # async def run_handler(self):
    #     await self.request_handler.run()
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

    def test_parse_1(self):
        self.test_request_data['client_id'] = 1
        return_code = self.run_coroutine(self.request_handler.parse(json.dumps(self.test_request_data)))
        self.assertEqual(self.test_request_data['client_id'] + self._parse_return_offset, return_code)

    def test_parse_2(self):
        self.test_request_data['client_id'] = 'lovely'
        with self.assertRaises(jsonschema.exceptions.ValidationError) as context_manager:
            self.run_coroutine(self.request_handler.parse(json.dumps(self.test_request_data)))

    def test_parse_3(self):
        self.test_request_data['client_id'] = 25
        return_code = self.run_coroutine(self.request_handler.parse(json.dumps(self.test_request_data)))
        self.assertEqual(self.test_request_data['client_id'] + self._parse_return_offset, return_code)

    def test_parse_4(self):
        self.test_request_data.pop('model')
        with self.assertRaises(jsonschema.exceptions.ValidationError) as context_manager:
            self.run_coroutine(self.request_handler.parse(json.dumps(self.test_request_data)))

