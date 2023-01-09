import unittest
from ..core.meta_data import DataDomain, DataFormat, DataRequirement, DataCategory, DiscreteRestriction


class TestDataRequirement(unittest.TestCase):

    def setUp(self) -> None:
        example_domains = []
        restriction = DiscreteRestriction(variable="CATCHMENT_ID", values=['cat-1'])
        example_domains.append(DataDomain(data_format=DataFormat.AORC_CSV, discrete_restrictions=[restriction]))

        self.example_reqs = []
        self.example_reqs.append(DataRequirement(domain=example_domains[0], is_input=True,
                                                 category=DataCategory.FORCING))

    def tearDown(self) -> None:
        pass

    def test_domain_0_a(self):
        """
        Test domain returns the right type.
        """
        ex = 0
        requirement = self.example_reqs[ex]
        domain = requirement.domain
        self.assertTrue(isinstance(domain, DataDomain))

    def test_to_dict_0_a(self):
        ex = 0
        requirement = self.example_reqs[ex]
        as_dict = requirement.to_dict()
        self.assertTrue(isinstance(as_dict, dict))
        self.assertTrue("domain" in as_dict)

    def test_to_dict_0_b(self):
        ex = 0
        requirement = self.example_reqs[ex]
        as_dict = requirement.to_dict()
        self.assertTrue(requirement.is_input)
        self.assertTrue(isinstance(as_dict["is_input"], bool))
        self.assertTrue(as_dict["is_input"])

    def test_factory_init_from_deserialized_json_0_a(self):
        """
        Test that the general functionality works for example 0.
        """
        ex = 0
        requirement = self.example_reqs[ex]
        as_dict = requirement.to_dict()
        duplicate = DataRequirement.factory_init_from_deserialized_json(as_dict)
        self.assertEqual(requirement.category, duplicate.category)
        # TODO: be nice to have this later, but requires implementing equals() in this type
        #self.assertEqual(requirement.domain, duplicate.domain)
        self.assertEqual(requirement.is_input, duplicate.is_input)
