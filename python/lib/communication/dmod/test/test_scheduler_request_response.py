import unittest
from ..communication.scheduler_request import SchedulerRequestResponse


class TestSchedulerRequestResponse(unittest.TestCase):

    def setUp(self) -> None:
        self.request_strings = []
        self.request_jsons = []
        self.request_objs = []

        self.tested_serializeable_type = SchedulerRequestResponse

        # Example 0
        self.request_strings.append('{"data": {"job_id": "42"}, "message": "", "reason": "Job Scheduled", "success": true}')
        self.request_jsons.append({"success": True, "reason": "Job Scheduled", "message": "", "data": {"job_id": "42"}})
        self.request_objs.append(
            SchedulerRequestResponse(success=True, reason="Job Scheduled", message="", data={"job_id": "42"}))

    def test_factory_init_from_deserialized_json_0_a(self):
        """
        Assert that factory init method for deserializing produces an equal object to the pre-created object for the
        examples at the 0th index.
        """
        example_index = 0
        obj = SchedulerRequestResponse.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj, self.request_objs[example_index])

    def test_job_id_0_a(self):
        """
        Assert the value of job_id is as expected for the pre-created example object at the 0th index.
        """
        example_index = 0
        expected_job_id = '42'
        self.assertEqual(expected_job_id, self.request_objs[example_index].job_id)

    def test_job_id_0_b(self):
        """
        Assert the value of job_id is as expected for the object deserialized from the example JSON at the 0th index.
        """
        example_index = 0
        expected_job_id = '42'
        obj = SchedulerRequestResponse.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(expected_job_id, obj.job_id)

    def test_to_dict_0_a(self):
        """
        Assert that the example object at the 0th index serializes to a dict as expected by comparing to the pre-set
        JSON dict example at the 0th index.
        """
        example_index = 0
        ex_dict = self.request_objs[example_index].to_dict()
        self.assertEqual(ex_dict, self.request_jsons[example_index])

    def test_to_json_0_a(self):
        """
        Assert that the example object at the 0th index serializes to a JSON string as expected by comparing to the
        pre-set JSON dict example at the 0th index.
        """
        example_index = 0
        ex_json_str = self.request_objs[example_index].to_json()
        self.assertEqual(ex_json_str, self.request_strings[example_index])


if __name__ == '__main__':
    unittest.main()
