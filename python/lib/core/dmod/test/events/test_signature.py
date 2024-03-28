"""
Tests for dmod.core.events.Signature
"""
from __future__ import annotations

import typing
import unittest
from ...core.events.base_function import Signature
from ...core.events.base_function import EventFunctionParameter
from ...core.events.base_function import Event

def example_function(event: Event, arg1, arg2: int, arg3: bool, *args, **kwargs):
    return 5


class TestSignature(unittest.TestCase):
    def non_compliant_method(self, event: Event, arg1: str, arg2: bool, arg3: int, **kwargs):
        return 17

    def compliant_method(self, event: Event, arg1, arg2: int, arg3: bool, *args, **kwargs):
        return 8

    def test_from_function(self):
        signature = Signature.from_function(example_function)

        expected_parameters: typing.List[EventFunctionParameter] = list()
        expected_parameters.append(
            EventFunctionParameter(
                index=0,
                name="event",
                type=Event.__name__,
                required=True
            )
        )
        expected_parameters.append(
            EventFunctionParameter(
                index=1,
                name="arg1",
                required=True
            )
        )
        expected_parameters.append(
            EventFunctionParameter(
                index=2,
                name="arg2",
                type=int.__name__,
                required=True
            )
        )
        expected_parameters.append(
            EventFunctionParameter(
                index=3,
                name="arg3",
                type=bool.__name__,
                required=True
            )
        )
        expected_parameters.append(
            EventFunctionParameter(
                index=4,
                name="args",
                is_args=True
            )
        )
        expected_parameters.append(
            EventFunctionParameter(
                index=5,
                name="kwargs",
                is_kwargs=True
            )
        )

        manual_signature = Signature(expected_parameters)
        compliant_signature = Signature.from_function(self.compliant_method)
        self.assertTrue(manual_signature.complies_with(signature))
        self.assertTrue(signature.complies_with(manual_signature))
        self.assertTrue(signature.complies_with(compliant_signature))
        self.assertTrue(manual_signature.complies_with(compliant_signature))
        self.assertTrue(compliant_signature.complies_with(signature))
        self.assertTrue(compliant_signature.complies_with(manual_signature))

        non_compliant_signature = Signature.from_function(self.non_compliant_method)

        # The non-compliant signature should not comply with the standard signature defined above because
        # the standard signature can accept an arbitrary number of positional arguments while the non-compliant
        # version can't. The arguments (event, 1, 2, 3, 4, 5, 6, 7, example="value") work for the standard
        # signatures but not the non-compliant version
        self.assertFalse(non_compliant_signature.complies_with(signature))
        self.assertFalse(non_compliant_signature.complies_with(manual_signature))
        self.assertFalse(non_compliant_signature.complies_with(compliant_signature))

        # All other signatures should comply with the example set forth by the non-compliant version.
        # Despite the standard signatures accepting a wide array of variables, the non-compliant version is
        # much more restrictive, making it a subset of the above. Since it is a subset, the
        # superset should work as well.
        self.assertTrue(signature.complies_with(non_compliant_signature))
        self.assertTrue(manual_signature.complies_with(non_compliant_signature))
        self.assertTrue(compliant_signature.complies_with(non_compliant_signature))