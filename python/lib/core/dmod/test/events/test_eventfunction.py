"""
Tests for dmod.core.events.EventFunction
"""
from __future__ import annotations

import unittest
import inspect

from ...core.events.base_function import EventFunction
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


async def async_example_function(event: Event, arg1: int, arg2: int, *args, **kwargs):
    return ASYNC_TEST_FUNCTION_RESULT


def example_function(event: Event, arg1: int, arg2: int, *args, **kwargs):
    return TEST_FUNCTION_RESULT


class TestEventFunction(unittest.IsolatedAsyncioTestCase):
    async def async_method(self, event: Event, arg1: int, arg2: int, *args, **kwargs):
        return ASYNC_METHOD_RESULT

    def method(self, event: Event, arg1: int, arg2: int, *args, **kwargs):
        return METHOD_RESULT

    async def test_eventfunction(self):
        async_test_eventfunction = EventFunction(async_example_function)
        test_eventfunction = EventFunction(example_function)
        async_method_eventfunction = EventFunction(self.async_method)
        method_eventfunction = EventFunction(self.method)

        self.assertTrue(async_test_eventfunction.is_async)
        self.assertFalse(test_eventfunction.is_async)
        self.assertTrue(async_method_eventfunction.is_async)
        self.assertFalse(method_eventfunction.is_async)

        async_test_eventfunction_result = async_test_eventfunction(EVENT, ARG1, ARG2, ARG3, ARG4, arg5=ARG5)
        self.assertTrue(inspect.isawaitable(async_test_eventfunction_result))

        async_test_eventfunction_result = await async_test_eventfunction_result

        self.assertEqual(async_test_eventfunction_result, ASYNC_TEST_FUNCTION_RESULT)

        test_eventfunction_result = test_eventfunction(EVENT, ARG1, ARG2, ARG3, ARG4, arg5=ARG5)
        self.assertFalse(inspect.isawaitable(test_eventfunction_result))

        self.assertEqual(test_eventfunction_result, TEST_FUNCTION_RESULT)

        async_method_eventfunction_result = async_method_eventfunction(EVENT, ARG1, ARG2, ARG3, ARG4, arg5=ARG5)
        self.assertTrue(inspect.isawaitable(async_method_eventfunction_result))

        async_method_eventfunction_result = await async_method_eventfunction_result

        self.assertEqual(async_method_eventfunction_result, ASYNC_METHOD_RESULT)

        method_eventfunction_result = method_eventfunction(EVENT, ARG1, ARG2, ARG3, ARG4, arg5=ARG5)
        self.assertFalse(inspect.isawaitable(method_eventfunction_result))

        self.assertEqual(method_eventfunction_result, METHOD_RESULT)
