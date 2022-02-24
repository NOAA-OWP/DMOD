import unittest
from ..modeldata.data import CatchmentDataRequirement, DataRequirement, DataCategory
from ..modeldata.subset import SubsetDefinition


class TestCatchmentDataRequirement(unittest.TestCase):

    def setUp(self) -> None:
        example_subset_defs = []
        example_subset_defs.append(SubsetDefinition(catchment_ids=['cat-1'], nexus_ids=['nex-1']))

        self.example_reqs = []
        self.example_reqs.append(CatchmentDataRequirement(domain_params=example_subset_defs[0], is_input=True,
                                                          category=DataCategory.FORCING))

    def tearDown(self) -> None:
        pass

    def test_domain_params_0_a(self):
        """
        Test domain params returns the right type.
        """
        ex = 0
        requirement = self.example_reqs[ex]
        domain_params: SubsetDefinition = requirement.domain_params
        self.assertTrue(isinstance(domain_params, SubsetDefinition))

    def test_to_dict_0_a(self):
        ex = 0
        requirement = self.example_reqs[ex]
        as_dict = requirement.to_dict()
        self.assertTrue(isinstance(as_dict, dict))
        self.assertEqual(CatchmentDataRequirement.__name__, as_dict[CatchmentDataRequirement._KEY_REQ_SUBTYPE])

    def test_factory_init_from_deserialized_json_0_a(self):
        """
        Test that the general functionality works for example 0.
        """
        ex = 0
        requirement = self.example_reqs[ex]
        as_dict = requirement.to_dict()
        duplicate = CatchmentDataRequirement.factory_init_from_deserialized_json(as_dict)
        self.assertEqual(requirement.category, duplicate.category)
        self.assertEqual(requirement.domain_params, duplicate.domain_params)
        self.assertEqual(requirement.is_input, duplicate.is_input)

    def test_factory_init_from_deserialized_json_0_b(self):
        """
        Test that the superclass recursive call functionality works for example 0.
        """
        ex = 0
        requirement = self.example_reqs[ex]
        as_dict = requirement.to_dict()
        duplicate = DataRequirement.factory_init_from_deserialized_json(as_dict)
        self.assertEqual(duplicate.__class__, requirement.__class__)
        self.assertEqual(requirement.category, duplicate.category)
        self.assertEqual(requirement.domain_params, duplicate.domain_params)
        self.assertEqual(requirement.is_input, duplicate.is_input)
