"""
Tests for dmod.core.events.EventFunctionGroup
"""
from __future__ import annotations

import typing
import unittest

from ...core.events.base_function import EventFunctionParameter
from ...core.events.base_function import EventFunctionGroup
from ...core.events.base_function import Event

EVENT = Event("click")
ARG1 = 1
ARG2 = 4
ARG3 = True
ARG4 = False
ARG5 = "String"

ASYNC_TEST_FUNCTION_RESULT = 14
TEST_FUNCTION_RESULT = 4
ASYNC_METHOD_RESULT = 8
METHOD_RESULT = 2

EXPECTED_PARAMETERS: typing.Sequence[EventFunctionParameter] = [
    EventFunctionParameter(
        index=0,
        name="event",
        type=Event.__name__,
        required=True
    ),
    EventFunctionParameter(
        index=1,
        name="arg1",
        required=True
    ),
    EventFunctionParameter(
        index=2,
        name="arg2",
        default=9,
        required=False,
        type=int
    ),
    EventFunctionParameter(
        index=3,
        name="args",
        is_args=True
    ),
    EventFunctionParameter(
        index=4,
        name="kwargs",
        is_kwargs=True
    )
]


async def async_test_function(event: Event, arg1: int, arg2: int = 9, *args, **kwargs):
    return ASYNC_TEST_FUNCTION_RESULT


def test_function(event: Event, arg1: int, arg2: int = 9, *args, **kwargs):
    return TEST_FUNCTION_RESULT


def invalid_function(arg1):
    return METHOD_RESULT


class TestEventFunctionGroup(unittest.IsolatedAsyncioTestCase):
    async def async_method(self, event: Event, arg1: int, arg2: int = 9, *args, **kwargs):
        return ASYNC_METHOD_RESULT

    def method(self, event: Event, arg1: int, arg2: int = 9, *args, **kwargs):
        return METHOD_RESULT

    def invalid_method(self, event, arg1, arg2):
        return ASYNC_METHOD_RESULT

    async def test_eventfunctiongroup(self):
        self.assertRaises(
            ValueError,
            EventFunctionGroup,
            EXPECTED_PARAMETERS,
            self.async_method,
            invalid_function,
            self.invalid_method
        )

        predefined_group = EventFunctionGroup(
            EXPECTED_PARAMETERS,
            self.async_method,
            self.method,
            async_test_function,
            test_function
        )

        self.assertFalse(predefined_group.signature_matches(self.invalid_method))
        self.assertFalse(predefined_group.signature_matches(self.invalid_method))
        self.assertTrue(predefined_group.signature_matches(self.method))
        self.assertTrue(predefined_group.signature_matches(self.async_method))
        self.assertTrue(predefined_group.signature_matches(async_test_function))
        self.assertTrue(predefined_group.signature_matches(test_function))

        built_group = EventFunctionGroup(EXPECTED_PARAMETERS)

        self.assertFalse(built_group.signature_matches(self.invalid_method))
        self.assertFalse(built_group.signature_matches(self.invalid_method))
        self.assertTrue(built_group.signature_matches(self.method))
        self.assertTrue(built_group.signature_matches(self.async_method))
        self.assertTrue(built_group.signature_matches(async_test_function))
        self.assertTrue(built_group.signature_matches(test_function))

        invalid_functions = list()

        built_group.add_function(self.async_method, invalid_functions)
        self.assertEqual(len(invalid_functions), 0)

        built_group.add_function(self.method, invalid_functions)
        self.assertEqual(len(invalid_functions), 0)

        built_group.add_function(async_test_function, invalid_functions)
        self.assertEqual(len(invalid_functions), 0)

        built_group.add_function(test_function, invalid_functions)
        self.assertEqual(len(invalid_functions), 0)

        built_group.add_function(invalid_function, invalid_functions)
        self.assertEqual(len(invalid_functions), 1)

        built_group.add_function(self.invalid_method, invalid_functions)
        self.assertEqual(len(invalid_functions), 2)

        leftover_coroutines = predefined_group(EVENT, ARG1, ARG2, ARG3, arg4=ARG4, arg5=ARG5)
        self.assertEqual(len(leftover_coroutines), 2)

        predefined_coroutine_results = {await coroutine for coroutine in leftover_coroutines}

        try:
            await predefined_group.fire(EVENT, ARG1, ARG2, ARG3, arg4=ARG4, arg5=ARG5)
        except BaseException as e:
            self.fail(f"Calling the async 'fire' function on the predefined group failed. {str(e)}")

        leftover_built_coroutines = built_group(EVENT, ARG1, ARG2, ARG3, arg4=ARG4, arg5=ARG5)
        self.assertEqual(len(leftover_built_coroutines), 2)

        built_coroutine_results = {await coroutine for coroutine in leftover_built_coroutines}

        try:
            await built_group.fire(EVENT, ARG1, ARG2, ARG3, arg4=ARG4, arg5=ARG5)
        except BaseException as e:
            self.fail(f"Calling the async 'fire' function on the built group failed. {str(e)}")

        self.assertEqual(predefined_coroutine_results, built_coroutine_results)