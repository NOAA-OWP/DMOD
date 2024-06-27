"""
Unit tests for decorators
"""
import typing
import unittest
import logging
from collections import namedtuple

from ..core.decorators import deprecated
from ..core.decorators import version_range

DEPRECATION_MESSAGE = "test is deprecated"


class MockLogger:
    _instance = None
    def __init__(self):
        self.messages: typing.List[typing.Tuple[int, str]] = []

    @classmethod
    def log(cls, level: int, msg: str) -> None:
        if cls._instance is None:
            cls._instance = cls()
        cls._instance.messages.append((level, msg))

    @classmethod
    def message_exists(cls, level: int, message: str) -> bool:
        if cls._instance is None:
            return False

        return any(
            message_level == level and message_text == message
            for message_level, message_text in cls._instance.messages
        )


@deprecated(DEPRECATION_MESSAGE)
def deprecated_function():
    ...


VersionMessage = namedtuple("VersionMessage", ["level", "message"])

PASSING_VERSION_MESSAGE = VersionMessage(logging.INFO, "this function should not be alerted")
VERSION_TOO_OLD_MESSAGE = VersionMessage(logging.DEBUG, "this function is too old")
VERSION_TOO_NEW_MESSAGE = VersionMessage(logging.WARNING, "this function is too new")


@version_range(maximum_version="99.99.99", message=PASSING_VERSION_MESSAGE.message, level=PASSING_VERSION_MESSAGE.level, logger=MockLogger)
def versioned_function_one():
    """
    Function used to ensure that NOTHING is logged when the python version is within allowable bounds
    """
    return 1


@version_range(maximum_version=(3, 3, 0), message=VERSION_TOO_NEW_MESSAGE.message, level=VERSION_TOO_NEW_MESSAGE.level, logger=MockLogger)
def versioned_function_two():
    """
    Function used to ensure that a message is recorded as this version of python is too new
    """
    return 2


@version_range(minimum_version="4", message=VERSION_TOO_OLD_MESSAGE.message, level=VERSION_TOO_OLD_MESSAGE.level, logger=MockLogger)
def versioned_function_three():
    """
    Function used to ensure that a message is recorded as this version of python being too old
    """
    return 3


class TestDecorators(unittest.TestCase):
    def test_raises_deprecated_warning(self):
        with self.assertWarns(DeprecationWarning):
            deprecated_function()

    def test_versioned_functions(self):
        self.assertFalse(
            MockLogger.message_exists(
                level=PASSING_VERSION_MESSAGE.level,
                message=PASSING_VERSION_MESSAGE.message
            )
        )
        self.assertFalse(
            MockLogger.message_exists(
                level=VERSION_TOO_OLD_MESSAGE.level,
                message=VERSION_TOO_OLD_MESSAGE.message
            )
        )
        self.assertFalse(
            MockLogger.message_exists(
                level=VERSION_TOO_NEW_MESSAGE.level,
                message=VERSION_TOO_NEW_MESSAGE.message
            )
        )

        one = versioned_function_one()
        two = versioned_function_two()
        three = versioned_function_three()

        self.assertEqual(one, 1)
        self.assertEqual(two, 2)
        self.assertEqual(three, 3)

        self.assertFalse(
            MockLogger.message_exists(
                level=PASSING_VERSION_MESSAGE.level,
                message=PASSING_VERSION_MESSAGE.message
            )
        )
        self.assertTrue(
            MockLogger.message_exists(
                level=VERSION_TOO_OLD_MESSAGE.level,
                message=VERSION_TOO_OLD_MESSAGE.message
            )
        )
        self.assertTrue(
            MockLogger.message_exists(
                level=VERSION_TOO_NEW_MESSAGE.level,
                message=VERSION_TOO_NEW_MESSAGE.message
            )
        )
