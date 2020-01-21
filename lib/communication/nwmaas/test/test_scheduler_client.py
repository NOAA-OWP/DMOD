import asyncio
import json
import unittest
from pathlib import Path
from typing import Union
from ..communication import NWMRequest, SchedulerClient, SchedulerRequestMessage, SchedulerRequestResponse


class MockSendTestingSchedulerClient(SchedulerClient):
    """
    Customized extension of ``SchedulerClient`` for testing purposes, where the :meth:`async_send` method has been
    overridden with a mock implementation to allow for testing without actually needing a real websocket connection.
    """

    def __init__(self):
        super().__init__(endpoint_uri='', ssl_directory=Path('.'))

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

    def set_scheduler_response_none(self):
        self.test_response_selection = 0

    def set_scheduler_response_non_json_string(self):
        self.test_response_selection = 1

    def set_scheduler_response_unrecognized_json(self):
        self.test_response_selection = 2

    def set_scheduler_response_valid_obj_for_failure(self):
        self.test_response_selection = 3

    def set_scheduler_response_valid_obj_for_success(self):
        self.test_response_selection = 4


class TestSchedulerClient(unittest.TestCase):

    def setUp(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.client = MockSendTestingSchedulerClient()

        self.test_model_request_1 = NWMRequest(version=2.0, output='streamflow', parameters={}, session_secret='')
        self.test_scheduler_request_1 = SchedulerRequestMessage(model_request=self.test_model_request_1,
                                                                user_id='default')

    def tearDown(self) -> None:
        pass

    def test_async_make_request_1_a(self):
        """
        Test ``async_make_request()`` when response from sending over websocket is ``None``, ensuring response object's
        value for ``success`` is ``False``.
        """
        self.client.set_scheduler_response_none()
        request = self.test_scheduler_request_1

        response = self.loop.run_until_complete(self.client.async_make_request(request))
        self.assertFalse(response.success)

    def test_async_make_request_1_b(self):
        """
        Test ``async_make_request()`` when response from sending over websocket is ``None``, ensuring response object's
        value for ``data`` is an empty dictionary.
        """
        self.client.set_scheduler_response_none()
        request = self.test_scheduler_request_1

        response = self.loop.run_until_complete(self.client.async_make_request(request))
        self.assertEqual(response.data, {})

    def test_async_make_request_1_c(self):
        """
        Test ``async_make_request()`` when response from sending over websocket is ``None``, ensuring response object's
        value for ``reason`` is the expected string.
        """
        self.client.set_scheduler_response_none()
        request = self.test_scheduler_request_1

        expected_reason = 'Request Send Failure (ValueError)'

        response = self.loop.run_until_complete(self.client.async_make_request(request))
        self.assertEqual(response.reason, expected_reason)

    def test_async_make_request_2_a(self):
        """
        Test ``async_make_request()`` when response from sending over websocket is not a valid JSON string, ensuring
        response object's value for ``success`` is ``False``.
        """
        self.client.set_scheduler_response_non_json_string()
        request = self.test_scheduler_request_1

        response = self.loop.run_until_complete(self.client.async_make_request(request))
        self.assertFalse(response.success)

    def test_async_make_request_2_b(self):
        """
        Test ``async_make_request()`` when response from sending over websocket is not a valid JSON string, ensuring
        response object's value for ``data`` is an empty dictionary.
        """
        self.client.set_scheduler_response_non_json_string()
        request = self.test_scheduler_request_1

        response = self.loop.run_until_complete(self.client.async_make_request(request))
        self.assertEqual(response.data, {})

    def test_async_make_request_2_c(self):
        """
        Test ``async_make_request()`` when response from sending over websocket is not a valid JSON string, ensuring
        response object's value for ``reason`` is the expected string.
        """
        self.client.set_scheduler_response_non_json_string()
        request = self.test_scheduler_request_1

        response = self.loop.run_until_complete(self.client.async_make_request(request))
        self.assertEqual(response.reason, 'Invalid JSON Response')

    def test_async_make_request_3_a(self):
        """
        Test ``async_make_request()`` when response from sending over websocket is a valid JSON string, but not one that
        can be deserialized to a :class:`SchedulerRequestResponse`, ensuring response object's value for ``success`` is
        ``False``.
        """
        self.client.set_scheduler_response_unrecognized_json()
        request = self.test_scheduler_request_1

        response = self.loop.run_until_complete(self.client.async_make_request(request))
        self.assertFalse(response.success)

    def test_async_make_request_3_b(self):
        """
        Test ``async_make_request()`` when response from sending over websocket is a valid JSON string, but not one that
        can be deserialized to a :class:`SchedulerRequestResponse`, ensuring response object's value for ``data`` is the
        parsed response JSON object.
        """
        self.client.set_scheduler_response_unrecognized_json()
        request = self.test_scheduler_request_1

        expected_raw_response = self.client.test_responses[self.client.test_response_selection]
        expected_json_obj = json.loads(expected_raw_response)

        response = self.loop.run_until_complete(self.client.async_make_request(request))
        self.assertEqual(response.data, expected_json_obj)

    def test_async_make_request_3_c(self):
        """
        Test ``async_make_request()`` when response from sending over websocket is a valid JSON string, but not one that
        can be deserialized to a :class:`SchedulerRequestResponse`, ensuring response object's value for ``reason`` is
        the expected string.
        """
        self.client.set_scheduler_response_unrecognized_json()
        request = self.test_scheduler_request_1

        response = self.loop.run_until_complete(self.client.async_make_request(request))
        self.assertEqual(response.reason, 'Could Not Deserialize Response Object')

    def test_async_make_request_4_a(self):
        """
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
        Test ``async_make_request()`` when response from sending over websocket is a valid, deserializeable JSON string,
        where the deserialized to a :class:`SchedulerRequestResponse` indicates a success, ensuring response object's
        value for ``success`` is ``True``.
        """
        self.client.set_scheduler_response_valid_obj_for_success()
        request = self.test_scheduler_request_1

        response = self.loop.run_until_complete(self.client.async_make_request(request))
        self.assertTrue(response.success)
