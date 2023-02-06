import unittest
from pydantic import ValidationError
from .scheduler_test_utils import _mock_resources
from ..scheduler.resources import Resource, ResourceAvailability


class TestResource(unittest.TestCase):
    def setUp(self) -> None:
        self._resource = Resource(
            resource_id="1",
            hostname="somehost",
            availability="active",
            state="ready",
            cpu_count=4,
            memory=(2 ** 30) * 8,
            total_cpu_count=8,
            total_memory=(2 ** 30) * 16,
        )

    def test_factory_init_from_dict_coerces_fields_correctly(self):
        for i, input in enumerate(_mock_resources):
            with self.subTest(i=i):
                o = Resource.factory_init_from_dict(input)
                assert o.resource_id == input["node_id"]
                assert o.pool_id == input["node_id"]
                assert o.hostname == input["Hostname"]
                assert (
                    o.availability.name.casefold() == input["Availability"].casefold()
                )
                assert o.state.name.casefold() == input["State"].casefold()
                assert o.memory == input["MemoryBytes"]
                assert o.cpu_count == input["CPUs"]
                assert o.total_cpus == input["CPUs"]
                assert o.total_memory == input["MemoryBytes"]

    def test_factory_init_from_dict_works_case_insensitively(self):
        input = {
            "NODE_ID": "Node-0003",
            "hostname": "hostname3",
            "AVAILABILITY": "active",
            "state": "ready",
            "CPUS": 42,
            "memorybytes": 200000000000,
        }
        o = Resource.factory_init_from_dict(input)
        assert o.resource_id == input["NODE_ID"]
        assert o.pool_id == input["NODE_ID"]
        assert o.hostname == input["hostname"]
        assert o.availability.name.casefold() == input["AVAILABILITY"].casefold()
        assert o.state.name.casefold() == input["state"].casefold()
        assert o.memory == input["memorybytes"]
        assert o.cpu_count == input["CPUS"]
        assert o.total_cpus == input["CPUS"]
        assert o.total_memory == input["memorybytes"]

    def test_set_availability(self):
        resource = self._resource
        availability = ResourceAvailability.UNKNOWN
        resource.set_availability(availability)
        assert resource.availability == ResourceAvailability.UNKNOWN

        availability = ResourceAvailability.ACTIVE
        resource.set_availability(availability)
        assert resource.availability == ResourceAvailability.ACTIVE

        availability = ResourceAvailability.INACTIVE
        resource.set_availability(availability)
        assert resource.availability == ResourceAvailability.INACTIVE

        resource.set_availability("unknown")
        assert resource.availability == ResourceAvailability.UNKNOWN

        resource.set_availability("active")
        assert resource.availability == ResourceAvailability.ACTIVE

        resource.set_availability("inactive")
        assert resource.availability == ResourceAvailability.INACTIVE

        # remove in future
        with self.assertWarns(DeprecationWarning):
            availability = ResourceAvailability.UNKNOWN
            resource.availability = availability
            assert resource.availability == ResourceAvailability.UNKNOWN

        with self.assertWarns(DeprecationWarning):
            availability = ResourceAvailability.ACTIVE
            resource.availability = availability
            assert resource.availability == ResourceAvailability.ACTIVE

        with self.assertWarns(DeprecationWarning):
            availability = ResourceAvailability.INACTIVE
            resource.availability = availability
            assert resource.availability == ResourceAvailability.INACTIVE

    def test_eq(self):
        resource = self._resource
        assert resource == resource
        assert resource == Resource.factory_init_from_dict(resource.to_dict())

    def test_init_with_more_cpu_than_total_cpu(self):
        with self.assertRaises(ValidationError):
            Resource(
                cpu_count=8,
                total_cpu_count=4,
                resource_id="1",
                hostname="somehost",
                availability="active",
                state="ready",
                memory=8,
                total_memory=8,
            )

    def test_init_with_more_memory_than_total_memory(self):
        with self.assertRaises(ValidationError):
            Resource(
                memory=8,
                total_memory=4,
                resource_id="1",
                hostname="somehost",
                availability="active",
                state="ready",
                cpu_count=8,
                total_cpu_count=8,
            )
