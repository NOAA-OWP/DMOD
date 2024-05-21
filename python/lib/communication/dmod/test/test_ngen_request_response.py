import json
import unittest
from ..communication.maas_request import NGENRequestResponse
from ..communication.maas_request.model_exec_request_response_body import ModelExecRequestResponseBody
from ..communication.message import InitRequestResponseReason
from ..communication.scheduler_request import SchedulerRequestResponse


class TestNGENRequestResponse(unittest.TestCase):

    _RAW_RESPONSE_STR_EX_1 = '{"success": false, "reason": "UNRECOGNIZED_SESSION_SECRET", "message": "Request with secret 824c69aa7fabcacb43cc914558f58bf02f6ad866a7a2f952ababab2376a69792 does not correspond to a known authenticated session", "data": {}}'
    _RAW_RESPONSE_STR_EX_2 = '{"success": true, "reason": "ACCEPTED", "message": "Success submitting job to scheduler (returned id 42)", "data": {"job_id": 42, "scheduler_response": {"success": true, "reason": "Job Scheduled", "message": "", "data": {"job_id": 42}}}}'

    @classmethod
    def get_raw_response_string_example_1(cls):
        return cls._RAW_RESPONSE_STR_EX_1

    @classmethod
    def get_raw_response_string_example_2(cls):
        return cls._RAW_RESPONSE_STR_EX_2

    def setUp(self) -> None:
        self.response_strings = {1: self._RAW_RESPONSE_STR_EX_1, 2: self._RAW_RESPONSE_STR_EX_2}
        self.response_jsons = dict()
        for k in self.response_strings:
            self.response_jsons[k] = json.loads(self.response_strings[k])

    def tearDown(self) -> None:
        pass

    def test_factory_init_from_deserialized_json_1_a(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 1 to make sure it deserializes.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[1])
        self.assertIsNotNone(obj)

    def test_factory_init_from_deserialized_json_1_b(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 1 to make sure it deserializes to the right
        object type.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[1])
        self.assertEqual(obj.__class__, NGENRequestResponse)

    def test_factory_init_from_deserialized_json_1_c(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 1 to make sure the deserialized object has
        the expected value for ``success``.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[1])
        self.assertFalse(obj.success)

    def test_factory_init_from_deserialized_json_1_d(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 1 to make sure the deserialized object has
        the expected value for ``reason``.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[1])
        self.assertEqual(obj.reason, InitRequestResponseReason.UNRECOGNIZED_SESSION_SECRET.name)

    def test_factory_init_from_deserialized_json_2_a(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 2 to make sure it deserializes.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[2])
        self.assertIsNotNone(obj)

    def test_factory_init_from_deserialized_json_2_b(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 2 to make sure it deserializes to the right
        object type.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[2])
        self.assertEqual(obj.__class__, NGENRequestResponse)

    def test_factory_init_from_deserialized_json_2_c(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 2 to make sure the deserialized object has
        the expected value for ``success``.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[2])
        self.assertTrue(obj.success)

    def test_factory_init_from_deserialized_json_2_d(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 2 to make sure the deserialized object has
        the expected value for ``reason``.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[2])
        self.assertEqual(obj.reason, InitRequestResponseReason.ACCEPTED.name)

    def test_factory_init_from_deserialized_json_2_e(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 2 to make sure the deserialized object has
        the expected dictionary value for ``data``.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[2])
        self.assertEqual(obj.data.__class__, ModelExecRequestResponseBody)

    def test_factory_init_from_deserialized_json_2_f(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 2 to make sure the deserialized object has
        the expected dictionary value for ``data``, with the expected ``job_id`` key.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[2])
        self.assertTrue('job_id' in obj.data)

    def test_factory_init_from_deserialized_json_2_g(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 2 to make sure the deserialized object has
        the expected dictionary value for ``data``, with the ``job_id`` element having the correct value.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[2])
        self.assertEqual(obj.data['job_id'], '42')

    def test_factory_init_from_deserialized_json_2_h(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 2 to make sure the deserialized object has
        the expected dictionary value for ``data``, with the expected ``scheduler_response`` key.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[2])
        self.assertTrue('scheduler_response' in obj.data)

    def test_factory_init_from_deserialized_json_2_i(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 2 to make sure the deserialized object has
        the expected dictionary value for ``data``, with the ``scheduler_response`` being of the right type.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[2])
        self.assertEqual(obj.data['scheduler_response'].__class__, SchedulerRequestResponse)

    def test_factory_init_from_deserialized_json_2_j(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 2 to make sure the deserialized object has
        the expected dictionary value for ``data``, with value mapped to ``scheduler_response`` being deserializeable.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[2])
        sched_dict = obj.data['scheduler_response']
        sched_resp = SchedulerRequestResponse.factory_init_from_deserialized_json(sched_dict)
        self.assertIsNotNone(sched_resp)

    def test_factory_init_from_deserialized_json_2_k(self):
        """
        Test ``factory_init_from_deserialized_json()`` on raw string example 2 to make sure the deserialized object has
        the expected dictionary value for ``data``, with value mapped to ``scheduler_response`` being deserializeable to
        a :class:`SchedulerRequestResponse`.
        """
        obj = NGENRequestResponse.factory_init_from_deserialized_json(self.response_jsons[2])
        sched_resp = SchedulerRequestResponse.factory_init_from_deserialized_json(obj.data['scheduler_response'])
        self.assertEqual(sched_resp.__class__, SchedulerRequestResponse)

    # TODO: add some meaningful tests (directly)
