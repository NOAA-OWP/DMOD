import asyncio
import logging
import ssl
import unittest
from typing import Optional, Union
from ..communication import NWMRequest, SchedulerClient, SchedulerRequestMessage, SchedulerRequestResponse, \
    TransportLayerClient
from dmod.core.exception import DmodRuntimeError


class MockTransportLayerClient(TransportLayerClient):

    @classmethod
    def get_endpoint_protocol_str(cls, use_secure_connection: bool = True) -> str:
        return "mock"

    def __init__(self):
        super().__init__(endpoint_host='', endpoint_port=8888)

        self.test_responses = dict()

        # 0: response of None
        self.test_responses[0] = None
        # 1: response that is not a valid JSON string
        self.test_responses[1] = 'not valid json'
        # 2: response that is valid JSON, but not for deserializing to a response object
        self.test_responses[2] = '{"valid": true, "can_be_deserialized": false}'
        # 3: deserializeable response with failure indication
        self.test_responses[3] = str(SchedulerRequestResponse(success=False, reason='Testing Failure'))
        # 4: deserializeable response with success indication
        self.test_responses[4] = str(SchedulerRequestResponse(success=True, reason='Testing Success'))

        # By default, select response 0
        self.test_response_selection = 0

    async def async_send(self, data: Union[str, bytearray], await_response: bool = False):
        """
        Mock override of super-class implementation, simply returning a value from :attr:`test_responses` obtained from
        using the current value of :attr:`test_response_selection` as the lookup key.

        Parameters
        ----------
        data
        await_response

        Returns
        -------

        """
        response = self.test_responses[self.test_response_selection]
        if response is None:
            return response
        else:
            return str(response)

    async def async_recv(self) -> str:
        pass

    @property
    def client_ssl_context(self) -> ssl.SSLContext:
        pass

    @property
    def _get_endpoint_uri(self) -> str:
        return ''

    def set_client_response_none(self):
        self.test_response_selection = 0

    def set_client_response_non_json_string(self):
        self.test_response_selection = 1

    def set_client_response_unrecognized_json(self):
        self.test_response_selection = 2

    def set_client_response_valid_obj_for_failure(self):
        self.test_response_selection = 3

    def set_client_response_valid_obj_for_success(self):
        self.test_response_selection = 4


class MockSendTestingSchedulerClient(SchedulerClient):
    """
    Customized extension of ``SchedulerClient`` for testing purposes, where the :meth:`async_send` method has been
    overridden with a mock implementation to allow for testing without actually needing a real websocket connection.
    """

    def __init__(self):
        super().__init__(transport_client=MockTransportLayerClient())

    def set_scheduler_response_none(self):
        self._transport_client.test_response_selection = 0

    def set_scheduler_response_non_json_string(self):
        self._transport_client.test_response_selection = 1

    def set_scheduler_response_unrecognized_json(self):
        self._transport_client.test_response_selection = 2

    def set_scheduler_response_valid_obj_for_failure(self):
        self._transport_client.test_response_selection = 3

    def set_scheduler_response_valid_obj_for_success(self):
        self._transport_client.test_response_selection = 4


class TestSchedulerClient(unittest.TestCase):

    @classmethod
    def disable_logging(cls, level: Optional[int] = logging.ERROR):
        """
        Disable logging on the provided level, enabling all if level is ``None``.

        If ``level`` is ``None``, it is replaced with ``logging.NOTSET``.  This will then have the effect of enabling
        logging on all levels.

        Parameters
        ----------
        level : Optional[int]
            Logging level to disable (``logging.ERROR`` by default), where ``None`` implies all should be enabled.
        """
        if level is None:
            level = logging.NOTSET
        logging.disable(level)

    def setUp(self) -> None:
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        self.client = MockSendTestingSchedulerClient()

        self.test_model_request_1 = NWMRequest(config_data_id='1', session_secret='')
        self.test_scheduler_request_1 = SchedulerRequestMessage(model_request=self.test_model_request_1,
                                                                user_id='default')

    def tearDown(self) -> None:
        self.loop.stop()
        self.loop.close()

    def test_async_make_request_1_a(self):
        """
        Test when function gets ``None`` returned over websocket that a ::class:`ValueError` is raised.

        Test ``async_make_request()`` in the case where it receives ``None`` back over the websocket connection, to
        confirm that the function then raises a ::class:`ValueError`.
        """
        self.client.set_scheduler_response_none()
        request = self.test_scheduler_request_1

        self.disable_logging()
        with self.assertRaises(ValueError):
            self.loop.run_until_complete(self.client.async_make_request(request))
        self.disable_logging(None)

    def test_async_make_request_2_a(self):
        """
        Test when function gets back invalid JSON over websocket that a ::class:`DmodRuntimeError` is raised.

        Test ``async_make_request()`` when response from sending over websocket is not a valid JSON string, ensuring
        that a ::class:`DmodRuntimeError` is raised..
        """
        self.client.set_scheduler_response_non_json_string()
        request = self.test_scheduler_request_1

        with self.assertRaises(DmodRuntimeError):
            self.loop.run_until_complete(self.client.async_make_request(request))

    def test_async_make_request_3_a(self):
        """
        Test when function gets wrongly formatted JSON over websocket that a ::class:`DmodRuntimeError` is raised.

        Test ``async_make_request()`` when response from sending over websocket is a valid JSON string, but not one that
        can be deserialized to a :class:`SchedulerRequestResponse`, ensuring a ::class:`DmodRuntimeError` is raised.
        """
        self.client.set_scheduler_response_unrecognized_json()
        request = self.test_scheduler_request_1

        self.disable_logging()
        with self.assertRaises(DmodRuntimeError):
            self.loop.run_until_complete(self.client.async_make_request(request))
        self.disable_logging(None)

    def test_async_make_request_4_a(self):
        """
        Test when function gets JSON over websocket indicating failure that response object ``success`` is ``False``.

        Test ``async_make_request()`` when response from sending over websocket is a valid, deserializeable JSON string,
        where the deserialized to a :class:`SchedulerRequestResponse` indicates a failure, ensuring response object's
        value for ``success`` is ``False``.
        """
        self.client.set_scheduler_response_valid_obj_for_failure()
        request = self.test_scheduler_request_1

        response = self.loop.run_until_complete(self.client.async_make_request(request))
        self.assertFalse(response.success)

    def test_async_make_request_5_a(self):
        """
        Test when function gets JSON over websocket indicating success that response object ``success`` is ``True``.

        Test ``async_make_request()`` when response from sending over websocket is a valid, deserializeable JSON string,
        where the deserialized to a :class:`SchedulerRequestResponse` indicates a success, ensuring response object's
        value for ``success`` is ``True``.
        """
        self.client.set_scheduler_response_valid_obj_for_success()
        request = self.test_scheduler_request_1

        response = self.loop.run_until_complete(self.client.async_make_request(request))
        self.assertTrue(response.success)
