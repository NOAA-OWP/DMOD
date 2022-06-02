import json
import unittest
from ..communication.session import FullAuthSession, SessionInitResponse


class TestSessionInitResponse(unittest.TestCase):

    def setUp(self) -> None:
        self.request_strings = []
        self.request_jsons = []
        self.request_objs = []

        self.tested_serializeable_type = SessionInitResponse

        # Example 0
        raw_json_str_0 = '{"success": true, "reason": "Successful Auth", "message": "", "data": {"session_id": 1, "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c", "created": "2019-12-10 16:27:54.000000", "ip_address": "10.0.1.6", "user": "someone", "last_accessed": "2019-12-10 16:27:54.000000"}}'
        raw_json_obj_0 = json.loads(raw_json_str_0)
        sorted_json_str_0 = json.dumps(raw_json_obj_0, sort_keys=True)
        self.request_strings.append(sorted_json_str_0)
        self.request_jsons.append({"success": True, "reason": "Successful Auth", "message": "",
                                   "data": {"session_id": 1,
                                            "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c",
                                            "created": "2019-12-10 16:27:54.000000", "ip_address": "10.0.1.6",
                                            "user": "someone", "last_accessed": "2019-12-10 16:27:54.000000"}})
        self.request_objs.append(
            SessionInitResponse(success=True, reason='Successful Auth', message='',
                                data=FullAuthSession(session_id=1,
                                                     session_secret='f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c',
                                                     created='2019-12-10 16:27:54.000000',
                                                     last_accessed='2019-12-10 16:27:54.000000',
                                                     ip_address='10.0.1.6',
                                                     user='someone')))

    def test_factory_init_from_deserialized_json_0_a(self):
        """
        Assert that factory init method for deserializing produces an equal object to the pre-created object for the
        examples at the 0th index.
        """
        example_index = 0
        obj = self.tested_serializeable_type.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj, self.request_objs[example_index])

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
