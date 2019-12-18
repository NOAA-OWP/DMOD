import unittest
from ..communication.maas_request import NWMRequest


class TestNWMRequest(unittest.TestCase):

    def setUp(self) -> None:
        self.request_strings = []
        self.request_jsons = []
        self.request_objs = []

        self.tested_serializeable_type = NWMRequest

        # TODO: improve coverage through more examples

        # Example 0
        self.request_strings.append('{"model": {"NWM": {"version": 2.0, "output": "streamflow", "parameters": {}}}, "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}')
        self.request_jsons.append({'model': {'NWM': {'version': 2.0, 'output': 'streamflow', 'parameters': {}}}, 'session-secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'})
        self.request_objs.append(
            NWMRequest(session_secret='f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c',
                       version=2.0,
                       output='streamflow',
                       parameters={}))

        # Example 1 - like example 0, but with the object initialized with the default 'parameters' value
        self.request_strings.append('{"model": {"NWM": {"version": 2.0, "output": "streamflow", "parameters": {}}}, "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}')
        self.request_jsons.append({'model': {'NWM': {'version': 2.0, 'output': 'streamflow', 'parameters': {}}}, 'session-secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'})
        self.request_objs.append(
            NWMRequest(session_secret='f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c',
                       version=2.0,
                       output='streamflow'))

    def test_factory_init_from_deserialized_json_0_a(self):
        """
        Assert that :meth:`NWMRequest.factory_init_from_deserialized_json` produces an equal object to the
        pre-created object for the examples at the 0th index.
        """
        example_index = 0
        obj = NWMRequest.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj, self.request_objs[example_index])

    def test_factory_init_from_deserialized_json_0_b(self):
        """
        Assert that :meth:`NWMRequest.factory_init_from_deserialized_json` produces an object having the appropriate
        session secret value for the examples at the 0th index.
        """
        example_index = 0
        obj = NWMRequest.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj.session_secret, self.request_objs[example_index].session_secret)

    def test_factory_init_from_deserialized_json_1_a(self):
        """
        Assert that :meth:`NWMRequest.factory_init_from_deserialized_json` produces an equal object to the
        pre-created object for the examples at the 1th index.
        """
        example_index = 1
        obj = NWMRequest.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj, self.request_objs[example_index])

    def test_factory_init_from_deserialized_json_1_b(self):
        """
        Assert that :meth:`NWMRequest.factory_init_from_deserialized_json` produces an object having the appropriate
        session secret value for the examples at the 1th index.
        """
        example_index = 1
        obj = NWMRequest.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj.session_secret, self.request_objs[example_index].session_secret)

    def test_to_dict_0_a(self):
        """
        Assert that the example object at the 0th index serializes to a dict as expected by comparing to the pre-set
        JSON dict example at the 0th index.
        """
        example_index = 0
        ex_dict = self.request_objs[example_index].to_dict()
        self.assertEqual(ex_dict, self.request_jsons[example_index])

    def test_to_dict_1_a(self):
        """
        Assert that the example object at the 1th index serializes to a dict as expected by comparing to the pre-set
        JSON dict example at the 1th index.
        """
        example_index = 1
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

    def test_to_json_1_a(self):
        """
        Assert that the example object at the 1th index serializes to a JSON string as expected by comparing to the
        pre-set JSON dict example at the 1th index.
        """
        example_index = 1
        ex_json_str = self.request_objs[example_index].to_json()
        self.assertEqual(ex_json_str, self.request_strings[example_index])


if __name__ == '__main__':
    unittest.main()
