import unittest
from ..communication.dataset_management_message import DatasetManagementMessage, MaaSDatasetManagementMessage, \
    ManagementAction
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DiscreteRestriction, StandardDatasetIndex
from copy import deepcopy


class TestDatasetManagementMessage(unittest.TestCase):

    @classmethod
    def get_test_class_type(cls):
        return DatasetManagementMessage

    def _init_base_examples_and_objects(self) -> tuple:
        base_objects = dict()
        base_examples = dict()

        # Create valid base data entry and message object for CREATE
        base_examples[ManagementAction.CREATE] = {'action': 'CREATE', 'category': 'FORCING',
                                                  'dataset_name': 'my_dataset',
                                                  'data_domain': {
                                                      "data_format": "AORC_CSV", "continuous": {}, "discrete": {
                                                        StandardDatasetIndex.CATCHMENT_ID : {"variable": "CATCHMENT_ID", "values": []}}
                                                  },
                                                  'read_only': False, 'pending_data': False}
        all_catchments_restriction = DiscreteRestriction(variable='CATCHMENT_ID', values=[])
        domain = DataDomain(data_format=DataFormat.AORC_CSV, discrete_restrictions=[all_catchments_restriction])
        msg_obj = DatasetManagementMessage(action=ManagementAction.CREATE, dataset_name='my_dataset', domain=domain,
                                           category=DataCategory.FORCING)
        base_objects[msg_obj.management_action] = msg_obj

        # Create valid base data entry and message object for LIST_ALL
        base_examples[ManagementAction.LIST_ALL] = {'action': 'LIST_ALL', 'category': None, 'read_only': False,
                                                    'pending_data': False}
        msg_obj = DatasetManagementMessage(action=ManagementAction.LIST_ALL)
        base_objects[msg_obj.management_action] = msg_obj
        return base_examples, base_objects

    def setUp(self) -> None:
        self.TEST_CLASS_TYPE = self.get_test_class_type()
        self.base_examples, self.base_objects = self._init_base_examples_and_objects()

        # Now create testing examples
        self.example_data = []
        # do this as a dict, since we won't have something at every index
        self.example_object = dict()

        # 0 - Good example of CREATE
        self.example_data.append(self.base_examples[ManagementAction.CREATE])
        # Also add the example object
        self.example_object[0] = self.base_objects[ManagementAction.CREATE]

        # 1 - Bad example of create - no name
        bad_no_name = deepcopy(self.base_examples[ManagementAction.CREATE])
        bad_no_name.pop('dataset_name')
        self.example_data.append(bad_no_name)

        # 2 - Bad example of create - no category
        bad_no_category = deepcopy(self.base_examples[ManagementAction.CREATE])
        bad_no_category.pop('category')
        self.example_data.append(bad_no_category)

        # 3 - Bad example of CREATE - bad action string ('ManagementAction.CREATE' instead of 'CREATE')
        bad_invalid_action = deepcopy(self.base_examples[ManagementAction.CREATE])
        bad_invalid_action['action'] = 'ManagementAction.CREATE'
        self.example_data.append(bad_invalid_action)

        # 4 - Good example of LIST_ALL
        self.example_data.append(self.base_examples[ManagementAction.LIST_ALL])
        # Also add the example object
        self.example_object[4] = self.base_objects[ManagementAction.LIST_ALL]

        # 5 - Another good LIST_ALL, without explicit category=None in the data
        good_mod_no_category = deepcopy(self.base_examples[ManagementAction.LIST_ALL])
        good_mod_no_category.pop('category')
        self.example_data.append(good_mod_no_category)
        # Also add the example object
        self.example_object[5] = self.base_objects[ManagementAction.LIST_ALL]

    def test_category_0_a(self):
        """ Test getting category value for valid CREATE message data. """
        ex_indx = 0
        expected_category = DataCategory.FORCING

        message_object = self.example_object[ex_indx]
        category = message_object.data_category

        self.assertEqual(expected_category, category)

    def test_category_4_a(self):
        """ Test getting category value for valid LIST_ALL message data that has no category defined. """
        ex_indx = 4

        message_object = self.example_object[ex_indx]
        category = message_object.data_category

        self.assertIsNone(category)

    def test_factory_init_from_deserialized_json_0_a(self):
        """ Test deserialization for valid CREATE message data. """
        ex_indx = 0
        expected_action = ManagementAction.CREATE

        data = self.example_data[ex_indx]
        expected_object = self.base_objects[expected_action]

        obj = self.TEST_CLASS_TYPE.factory_init_from_deserialized_json(data)
        self.assertEqual(expected_object, obj)

    def test_factory_init_from_deserialized_json_1_a(self):
        """ Test deserialization fails for CREATE message data if there is no dataset name. """
        ex_indx = 1
        #expected_action = ManagementAction.CREATE
        data = self.example_data[ex_indx]

        obj = self.TEST_CLASS_TYPE.factory_init_from_deserialized_json(data)
        self.assertIsNone(obj)

    def test_factory_init_from_deserialized_json_2_a(self):
        """ Test deserialization fails for CREATE message data if there is no data category. """
        ex_indx = 2
        #expected_action = ManagementAction.CREATE
        data = self.example_data[ex_indx]

        obj = self.TEST_CLASS_TYPE.factory_init_from_deserialized_json(data)
        self.assertIsNone(obj)

    def test_factory_init_from_deserialized_json_3_a(self):
        """ Test deserialization fails for CREATE message data if the action string is serialized incorrectly. """
        ex_indx = 3
        #expected_action = ManagementAction.CREATE
        data = self.example_data[ex_indx]

        obj = self.TEST_CLASS_TYPE.factory_init_from_deserialized_json(data)
        self.assertIsNone(obj)

    def test_factory_init_from_deserialized_json_5_a(self):
        """ Test deserialization for valid LIST_ALL message data. """
        ex_indx = 5
        expected_action = ManagementAction.LIST_ALL

        data = self.example_data[ex_indx]
        expected_object = self.base_objects[expected_action]

        obj = self.TEST_CLASS_TYPE.factory_init_from_deserialized_json(data)
        self.assertEqual(expected_object, obj)

    def test_to_dict_0_a(self):
        """ Test serialization for valid CREATE message data. """
        ex_indx = 0
        expected_action = ManagementAction.CREATE

        expected_data = self.example_data[ex_indx]
        data = self.base_objects[expected_action].to_dict()

        self.assertEqual(expected_data, data)

    def test_to_dict_5_a(self):
        """ Test serialization for valid LIST_ALL message data. """
        ex_indx = 5
        expected_action = ManagementAction.LIST_ALL

        expected_data = self.example_data[ex_indx]
        data = self.base_objects[expected_action].to_dict()

        self.assertEqual(expected_data, data)


class TestMaaSDatasetManagementMessage(TestDatasetManagementMessage):

    @classmethod
    def get_test_class_type(cls):
        return MaaSDatasetManagementMessage

    def _init_base_examples_and_objects(self) -> tuple:
        base_examples, base_objects = super(TestMaaSDatasetManagementMessage, self)._init_base_examples_and_objects()
        secret_val = '409770e8cc4bfd10e276b98aff1d3817c8848e1747b3ad2e13f88ca45252e67e'

        # Update the examples from the base test
        for action in base_examples:
            # Data dicts should just be able to have the secret added
            base_examples[action]['session_secret'] = secret_val
            # The right objects have to be create, but they can be based on the subtype ones getting replaced
            base_objects[action] = MaaSDatasetManagementMessage.factory_create(mgmt_msg=base_objects[action],
                                                                               session_secret=secret_val)
        return base_examples, base_objects

    def setUp(self) -> None:
        super(TestMaaSDatasetManagementMessage, self).setUp()

        # 6 - In addition to the 0-6 above, this gets example 7 for an otherwise valid example, but without a secret
        bad_no_secret = deepcopy(self.base_examples[ManagementAction.CREATE])
        bad_no_secret.pop('session_secret')
        self.example_data.append(bad_no_secret)
