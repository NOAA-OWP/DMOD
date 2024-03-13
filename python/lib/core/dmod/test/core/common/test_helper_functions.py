"""
@TODO: Put a module wide description here
"""
from __future__ import annotations

import abc
import typing
import unittest


from ....core.common import helper_functions


class ExampleBaseClass(abc.ABC):
    @abc.abstractmethod
    def function_one(self):
        pass

class SecondExampleBase(ExampleBaseClass, abc.ABC):
    @abc.abstractmethod
    def function_two(self):
        ...

class ExampleOne(ExampleBaseClass):
    def function_one(self):
        return 1

class ExampleTwo(ExampleBaseClass):
    def function_one(self):
        return 2

class ExampleThree(SecondExampleBase):
    def function_one(self):
        return 3

    def function_two(self):
        return 9


class TestHelperFunctions(unittest.TestCase):
    def test_humanize_text(self):
        phrase_with_acronyms = "iNeedAAABatteriesNotAA"
        expected_cleanup = "I Need AAA Batteries Not AA"

        cleaned_up_text = helper_functions.humanize_text(phrase_with_acronyms)

        self.assertEqual(expected_cleanup, cleaned_up_text)

        text_with_phrase_to_remove = "DataSourceSpecification"
        expected_cleanup = "Data Source"

        cleaned_up_text = helper_functions.humanize_text(text_with_phrase_to_remove, exclude_phrases=["spEcIfIcAtiOn"])

        self.assertEqual(expected_cleanup, cleaned_up_text)

        text_with_many_types_of_characters = "word1NWC nationalWeather\tservice "
        expected_cleanup = "Word 1 NWC National Weather Service"

        cleaned_up_text = helper_functions.humanize_text(text_with_many_types_of_characters)

        self.assertEqual(cleaned_up_text, expected_cleanup)

        text_with_recursive_removals = "  my   removeRemoveThis This text  "
        expected_cleanup = "My Text"

        cleaned_up_text = helper_functions.humanize_text(text_with_recursive_removals, exclude_phrases=["Remove This"])

        self.assertEqual(expected_cleanup, cleaned_up_text)

    def call_to_convert_character_to_humanized_case_is_valid(
        self,
        previous_letter: typing.Union[None, str],
        current_letter: str,
        next_letter: typing.Union[None, str],
        expected_result: str
    ):
        converted_character = helper_functions.convert_character_to_humanized_case(
            previous_character=previous_letter,
            current_character=current_letter,
            next_character=next_letter
        )

        self.assertEqual(expected_result, converted_character)

    def test_convert_character_to_humanized_case(self):
        self.call_to_convert_character_to_humanized_case_is_valid(
            previous_letter="O",
            current_letter="W",
            next_letter="o",
            expected_result=" W"
        )

        self.call_to_convert_character_to_humanized_case_is_valid(
            previous_letter="N",
            current_letter="W",
            next_letter="S",
            expected_result="W"
        )

        self.call_to_convert_character_to_humanized_case_is_valid(
            previous_letter=None,
            current_letter="H",
            next_letter="e",
            expected_result="H"
        )

        self.call_to_convert_character_to_humanized_case_is_valid(
            previous_letter=None,
            current_letter=" ",
            next_letter=None,
            expected_result=" "
        )

        self.call_to_convert_character_to_humanized_case_is_valid(
            previous_letter="A",
            current_letter=" ",
            next_letter="l",
            expected_result=" "
        )

        self.call_to_convert_character_to_humanized_case_is_valid(
            previous_letter=" ",
            current_letter="c",
            next_letter="1",
            expected_result="C"
        )

        self.call_to_convert_character_to_humanized_case_is_valid(
            previous_letter="d",
            current_letter="1",
            next_letter="N",
            expected_result=" 1"
        )

        self.call_to_convert_character_to_humanized_case_is_valid(
            previous_letter="a",
            current_letter="S",
            next_letter="o",
            expected_result=" S"
        )

        self.call_to_convert_character_to_humanized_case_is_valid(
            previous_letter=None,
            current_letter="i",
            next_letter="N",
            expected_result="I"
        )

    def test_is_true(self):
        self.assertTrue(helper_functions.is_true("True"))
        self.assertTrue(helper_functions.is_true("true"))
        self.assertTrue(helper_functions.is_true("1"))
        self.assertTrue(helper_functions.is_true("YeS"))
        self.assertTrue(helper_functions.is_true("On"))
        self.assertTrue(helper_functions.is_true("T"))
        self.assertTrue(helper_functions.is_true(b"On"))
        self.assertTrue(helper_functions.is_true(b"T"))
        self.assertTrue(helper_functions.is_true(47))
        self.assertTrue(helper_functions.is_true(True))
        self.assertTrue(helper_functions.is_true([1, 2, 3]))

        self.assertFalse(helper_functions.is_true(None))
        self.assertFalse(helper_functions.is_true(False))
        self.assertFalse(helper_functions.is_true("false"))
        self.assertFalse(helper_functions.is_true(" false      "))
        self.assertFalse(helper_functions.is_true('f'))
        self.assertFalse(helper_functions.is_true("0"))
        self.assertFalse(helper_functions.is_true("Totally not True"))
        self.assertFalse(helper_functions.is_true("This is true"))
        self.assertFalse(helper_functions.is_true([]))
        self.assertFalse(helper_functions.is_true({}))
        self.assertFalse(helper_functions.is_true("oFf"))
        self.assertFalse(helper_functions.is_true(b"false"))
        self.assertFalse(helper_functions.is_true(b" false      "))
        self.assertFalse(helper_functions.is_true(b'f'))
        self.assertFalse(helper_functions.is_true(b"0"))
        self.assertFalse(helper_functions.is_true(b"Totally not True"))

    def test_find(self):
        class ExampleClass:
            def __init__(self, value1: int, value2: str, value3: bool):
                self.value1 = value1
                self.value2 = value2
                self.value3 = value3

        example_collection = [
            ExampleClass(8, "example", False),
            ExampleClass(9, "example", True),
            ExampleClass(10, "other", True),
            ExampleClass(11, "other", False),
            ExampleClass(27, "Found it", False),
        ]

        found_value = helper_functions.find(
            example_collection,
            lambda entry: entry.value1 % 9 == 0 and not entry.value3
        )

        self.assertIsNotNone(found_value)

        self.assertEqual(found_value.value1, 27)
        self.assertEqual(found_value.value2, "Found it")
        self.assertEqual(found_value.value3, False)

        missing_value = helper_functions.find(
            example_collection,
            lambda entry: entry.value1 == 999
        )

        self.assertIsNone(missing_value)

    def test_get_subclasses(self):
        class InnerBaseExample(ExampleThree, abc.ABC):
            @abc.abstractmethod
            def function_three(self):
                ...

            def function_one(self):
                return 2

            def function_two(self):
                return "Test"

        class InnerBaseClassImplementation(InnerBaseExample):
            def function_three(self):
                return False

        subclasses = helper_functions.get_subclasses(ExampleBaseClass)

        self.assertEqual(len(subclasses), 4)
        self.assertIn(ExampleOne, subclasses)
        self.assertIn(ExampleTwo, subclasses)
        self.assertIn(ExampleThree, subclasses)
        self.assertIn(InnerBaseClassImplementation, subclasses)