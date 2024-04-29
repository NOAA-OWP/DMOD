"""
Unit tests used to ensure that dmod.core.context operations behave as intended
"""
from __future__ import annotations

import abc
import dataclasses
import inspect
import logging
import os
import sys
import typing
import unittest
import multiprocessing
import string
import random
import re

from collections import namedtuple
from itertools import permutations
from multiprocessing import managers
from multiprocessing import pool

from typing_extensions import ParamSpec
from typing_extensions import Self

from ..core import context

VARIABLE_ARGUMENTS = ParamSpec("VARIABLE_ARGUMENTS")

T = typing.TypeVar("T")
R = typing.TypeVar("R")

STATIC_METHOD_ONE_VALUE = 95
STATIC_METHOD_TWO_VALUE = "blue"

CLASS_METHOD_ONE_VALUE = False
CLASS_METHOD_TWO_VALUE = 3+3j

STRING_INTEGER_PATTERN = re.compile(r"-?\d+")
MEMBER_SPLIT_PATTERN = re.compile(r"[./]")

MutationTuple = namedtuple("MutationTuple", ["field", "value", "should_be_equal"])


def shared_class_two_instance_method_formula(*args) -> int:
    """
    The formula for the instance method for SharedClassTwo

    Args:
        *args: The values to include in the formula

    Returns:
        An integer representing the size of passed in values
    """
    total: int = 0

    for item in args:
        if isinstance(item, typing.Sized):
            total += len(item)
        else:
            total += item

    return total


def make_word(min_length: int = None, max_length: int = None, character_set: str = None, avoid: str = None) -> str:
    """
    Create a random jumble of characters to build a new word

    Args:
        min_length: The shortest the word can be
        max_length: The longest a word can be
        character_set: What characters can make up the word
        avoid: A word to avoid creating

    Returns:
        A semi random string of a semi-random length
    """
    if min_length is None:
        min_length = 2

    if max_length is None:
        max_length = 8

    max_length = max(5, max_length)

    if character_set is None:
        character_set = string.ascii_letters + string.digits

    word: str = avoid

    while word == avoid:
        word = ''.join(random.choice(character_set) for _ in range(random.randint(min_length, max_length)))

    return word


def make_number(minimum: int = 0, maximum: int = 3000, avoid: int = None) -> int:
    """
    Create a random number

    Args:
        minimum: The minimum allowable number
        maximum: The maximum allowable number
        avoid: A number to avoid

    Returns:
        A random number
    """
    number = random.randint(minimum, maximum)

    while number == avoid:
        number = random.randint(minimum, maximum)

    return number


def make_numbers(
    minimum: int = 0,
    maximum: int = 3000,
    length: int = None,
    avoid: typing.Sequence[int] = None
) -> typing.Tuple[int, ...]:
    """
    Make a tuple of random numbers

    Args:
        minimum: the minimum value of the numbers to generate
        maximum: The maximum value of the numbers to generate
        length: The length of the sequence of numbers to generate
        avoid: A sequence of numbers to avoid generating

    Returns:
        A tuple of random integers
    """
    if length is None:
        length = random.randint(4, 12)

    numbers = tuple(
        make_number(minimum=minimum, maximum=maximum)
        for _ in range(length)
    )

    while numbers == tuple(avoid):
        numbers = tuple(
            make_number(minimum=minimum, maximum=maximum)
            for _ in range(length)
        )

    return numbers


class Sentinel:
    """
    Represents a value that represents a void of anything. This differs from 'None' in that 'None' is an
    acceptable value. Encountering a `Sentinel` value indicates that something went wrong.
    """
    def __eq__(self, other):
        return False

    def __hash__(self):
        return -0

    def __bool__(self):
        return False


SENTINEL = Sentinel()
"""Value indicating that no value was given. Defined at module level to ensure that it is portable across processes"""


@dataclasses.dataclass
class TestStepResult(typing.Generic[T]):
    """
    A basic structure tying the name of a test step to the result of its operation
    """
    test_name: str
    step_name: str
    value: T
    expected_result: typing.Union[T, None] = dataclasses.field(default=SENTINEL)
    ignore_result: bool = dataclasses.field(default=True)

    @property
    def step_was_successful(self) -> bool:
        """
        Indicates if the test step operated as expected
        """
        if isinstance(self.expected_result, PassableFunction):
            expectation = self.expected_result()
        else:
            expectation = self.expected_result

        if isinstance(self.value, BaseException) and not isinstance(expectation, BaseException):
            return False

        if self.ignore_result and isinstance(expectation, Sentinel):
            return True

        try:
            return self.value == expectation
        except Exception as e:
            print(e, file=sys.stderr)
            return False


@dataclasses.dataclass
class PassableFunction(typing.Generic[T, R]):
    """
    A structure containing instructions on how to construct and call a function
    """
    function: typing.Union[typing.Callable[[VARIABLE_ARGUMENTS], T], typing.Callable[[], T]]
    args: typing.Optional[typing.Tuple[typing.Any, ...]] = dataclasses.field(default=None)
    kwargs: typing.Optional[typing.Dict[str, typing.Any]] = dataclasses.field(default_factory=dict)
    operation_name: str = dataclasses.field(default=SENTINEL)

    def __call__(self) -> typing.Union[R, Exception]:
        try:
            if self.args and self.kwargs:
                result = self.function(*self.args, **self.kwargs)
            elif self.args:
                result = self.function(*self.args)
            elif self.kwargs:
                result = self.function(**self.kwargs)
            else:
                result = self.function()

            return self.handle_result(result)
        except Exception as e:
            return e

    def handle_result(self, result: T) -> typing.Union[R, Exception]:
        """
        Reinterpret the result in a fashion that is appropriate for the context

        This is useful for wrapping results of the called function

        Args:
            result: The value of the called function

        Returns:
            The mapped result
        """
        return result

    def __str__(self) -> str:
        args = ', '.join(map(str, self.args))
        kwargs = ', '.join(map(lambda name_and_value: f"{name_and_value[0]}={name_and_value[1]}", self.kwargs.items()))

        if args and kwargs:
            parameters = f"({args}, {kwargs})"
        elif args:
            parameters = f"({args})"
        elif kwargs:
            parameters = f"({kwargs})"
        else:
            parameters = "()"

        return f"{self.function.__qualname__}{parameters}"

    def __repr__(self) -> str:
        return self.__str__()


@dataclasses.dataclass
class TestStep(PassableFunction[T, TestStepResult[T]]):
    """
    A structure containing instructions on an action to perform.

    A collection of TestSteps are intended to be operated upon asynchronously
    """
    test_name: typing.Optional[str] = dataclasses.field(default=None)
    expected_result: typing.Union[T, PassableFunction, Sentinel] = dataclasses.field(default=SENTINEL)

    def __init__(
        self,
        test_name: str = None,
        expected_result: typing.Union[T, PassableFunction, Sentinel] = SENTINEL,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        if not self.operation_name:
            self.operation_name = self.function.__qualname__

        self.test_name = test_name
        self.expected_result = expected_result

    def copy(self) -> TestStep[T]:
        """
        Create a copy of this step
        """
        return TestStep(
            test_name=self.test_name,
            operation_name=self.operation_name,
            function=self.function,
            args=self.args,
            kwargs=self.kwargs,
            expected_result=self.expected_result
        )

    def handle_result(self, result: T) -> TestStepResult[T]:
        return TestStepResult(
            test_name=self.test_name,
            step_name=self.operation_name,
            value=result,
            expected_result=self.expected_result
        )


class TestSteps:
    """
    A collection of TestSteps that help organize and may handle tests
    """
    def __init__(self, series_name: str, steps: typing.Iterable[TestStep] = None, worker_count: int = None):
        self.series_name = series_name
        self.__latest_results: typing.Optional[typing.List[TestStepResult]] = None
        self.__success: typing.Optional[bool] = None
        self.__steps: typing.Optional[typing.List[TestStep]] = None

        if steps:
            self.add(steps)

        self.worker_count = max(2, worker_count or os.cpu_count() // 3)

    def phrase_failure(self) -> str:
        """
        Describes all failures in a human readable fashion
        """
        if self.succeeded:
            raise Exception(f"{self.series_name}: Cannot create a failure phrase - the test was succeessful.")

        message_lines = [
            self.series_name,
            "",
            "Tests Failed",
            "",
            *self.failures
        ]
        return os.linesep.join(message_lines)

    def clear(self):
        """
        Set the current state of the test to empty
        """
        self.__steps = None
        self.series_name = None
        self.__latest_results = None
        self.__success = None

    @property
    def succeeded(self) -> bool:
        """
        Whether the most recent execution of the test was a success
        """
        if self.__success is None:
            raise Exception("Cannot tell if a series of test steps was successful - none have run")
        return self.__success

    @property
    def results(self) -> typing.Sequence[TestStepResult]:
        """
        The rest results from the most recent run
        """
        if self.__latest_results is None:
            raise Exception("No results for step tests - nothing has been run yet")
        return self.__latest_results

    @property
    def failures(self) -> typing.Sequence[str]:
        """
        A sequence of messages describing each failure from the most recent tests
        """
        failed_steps: typing.List[str] = []
        for step_number, step_result in enumerate(self.results, start=1):
            if isinstance(step_result, TestStepResult) and step_result.step_was_successful:
                continue

            if isinstance(step_result, BaseException):
                failed_step = self.__steps[step_number - 1]
                message = f"#{step_number} '{failed_step.operation_name}' failed - Encountered Exception '{step_result}'"
            elif isinstance(step_result, TestStepResult):
                message = (f"#{step_number})'{step_result.step_name}' failed - expected '{step_result.expected_result}' "
                           f"but resulted in '{step_result.value}'")
            else:
                failed_step = self.__steps[step_number - 1]
                message = (f"#{step_number} '{failed_step.operation_name}' failed - a result object was not returned. "
                           f"Received '{step_result} ({type(step_result)}' instead")

            failed_steps.append(message)

        return failed_steps

    def add(self, steps: typing.Union[typing.Iterable[TestStep], TestStep], *args: TestStep) -> Self:
        """
        Add one or more steps to the test

        Args:
            steps: A step or collection of steps to add
            *args: Steps to add

        Returns:
            This instance
        """
        if isinstance(steps, TestStep):
            if self.__steps is None:
                self.__steps = []
            steps.test_name = self.series_name
            self.__steps.append(steps)
        elif isinstance(steps, typing.Iterable):
            if self.__steps is None:
                self.__steps = []
            for step in steps:
                step.test_name = self.series_name
                self.__steps.append(step)
        else:
            raise TypeError("Only a TestStep or a collection of test steps may be added to a TestSteps")

        if args:
            self.add(args)

        return self

    def run(self) -> bool:
        """
        Run all steps

        Returns:
            True if all steps succeeded
        """
        if not self.series_name:
            raise ValueError("Cannot run a series of test steps without a series name")

        if not self.__steps:
            raise ValueError("Cannot run a series of test steps without a series of test steps")

        # Shuffle all the inputs.
        # We don't want to risk missing a failure because everything was done in the exact right order.
        #   It's not perfect, but failing 5% of the time is better than failing 0% of the time when there's
        #   a hard to catch issue
        random.shuffle(self.__steps)
        with multiprocessing.Pool(processes=self.worker_count) as process_pool:  # type: pool.Pool
            application_results: typing.List[TestStepResult] = process_pool.map(
                TestStep.__call__,
                iterable=self.__steps
            )

        errors = [result for result in application_results if isinstance(result, BaseException)]
        if errors:
            self.__success = False
        else:
            self.__success = all(result.step_was_successful for result in application_results)

        self.__latest_results = application_results
        return self.__success

    def assert_success(self, test_case: unittest.TestCase):
        """
        Run the tests (if not already run) and fail the test case if the tests didn't succeed

        Args:
            test_case: The test to fail if the steps don't all pass
        """
        if self.__latest_results is None:
            self.run()

        if not self.succeeded:
            test_case.fail(self.phrase_failure())


class SharedClass(abc.ABC):
    """
    Base class for test classes that will have generated proxies
    """
    @staticmethod
    @abc.abstractmethod
    def class_name():
        """
        The name of the class
        """
        raise NotImplementedError("SharedClass.class_name was not implemented on this subclass")

    @classmethod
    def class_identifier(cls) -> str:
        """
        An identifier for the class based on its name and where it came from
        """
        return f"{__file__}{cls.class_name()}"

    @staticmethod
    @abc.abstractmethod
    def static_method(*args, **kwargs):
        """
        An unbound-function to test operations against
        """
        raise NotImplementedError("SharedClass.static_method was not implemented on this subclass")

    @classmethod
    @abc.abstractmethod
    def class_method(cls, *args, **kwargs):
        """
        A class-bound function used to test proxied class methods
        """
        raise NotImplementedError(f"{cls.class_identifier()}.class_method has not been implemented")

    @abc.abstractmethod
    def instance_method(self, *args, **kwargs):
        """
        A instance bound function used to test proxied instance methods
        """
        raise NotImplementedError(f"{self.class_identifier()}.instance_method has not been implemented")

    @abc.abstractmethod
    def copy(self):
        """
        Copies the current instance

        Will test the code's ability to create and operate on a non-remote instance
        """
        raise NotImplementedError(f"{self.class_identifier()}.copy has not been implemented")


class SharedClassOne(SharedClass):
    """
    The first example implementation of a shared class

    This is meant to test a class with a large amount of dunders
    """
    def copy(self):
        return self.__class__(
            one_a=self.one_a
        )

    @staticmethod
    def class_name():
        return "SharedClassOne"

    def __init__(self, one_a: int):
        self.one_a = one_a

    @property
    def a(self) -> int:
        """
        Get the value of the 'one_a' instance variable
        """
        return self.one_a

    @a.setter
    def a(self, a: int):
        self.one_a = a

    def get_a(self) -> int:
        """
        Get the value of the 'one_a' instance variable
        """
        return self.one_a

    def set_a(self, a: int) -> None:
        """
        Set the value of the 'one_a' instance variable

        Args:
            a: The new value for 'one_a'
        """
        self.one_a = a

    @staticmethod
    def static_method(*args, **kwargs):
        return STATIC_METHOD_ONE_VALUE

    @classmethod
    def class_method(cls, *args, **kwargs):
        return CLASS_METHOD_ONE_VALUE

    def instance_method(self, *args, **kwargs):
        return self.one_a * 9

    def __eq__(self, other):
        return self.a == other.a

    def __hash__(self):
        return hash(self.one_a)

    def __ne__(self, other):
        return self.a != other.a

    def __lt__(self, other):
        return self.a < other.a

    def __le__(self, other):
        return self.a <= other.a

    def __gt__(self, other):
        return self.a > other.a

    def __ge__(self, other):
        return self.a >= other.a

    def __add__(self, other):
        return self.__class__(self.a + other.a)

    def __sub__(self, other):
        return self.__class__(self.a - other.a)

    def __mul__(self, other):
        return self.__class__(self.a * other.a)

    def __truediv__(self, other):
        return self.__class__(self.one_a / other.one_a)

    def __floordiv__(self, other):
        return self.__class__(self.one_a // other.one_a)

    def __mod__(self, other):
        return self.__class__(self.one_a % other.one_a)


class SharedClassTwo(SharedClass):
    """
    Second implementation of a shared class.

    Meant to have multiple modifiable variables and different access patterns
    """
    def copy(self):
        return self.__class__(
            two_a=self.two_a,
            two_b=dict(self.two_b),
            two_c=list(self.two_c),
            two_d=self.two_d.copy()
        )

    @staticmethod
    def class_name():
        return "SharedClassTwo"

    def __init__(self, two_a: str, two_b: dict, two_c: list, two_d: SharedClassOne):
        self.two_a = two_a
        self.two_b = two_b
        self.two_c = two_c
        self.two_d = two_d

    @property
    def a(self):
        return self.two_a

    @a.setter
    def a(self, a: str):
        self.two_a = a

    def get_a(self) -> str:
        return self.two_a

    def set_a(self, a: str):
        self.two_a = a

    @property
    def b(self):
        return self.two_b

    @b.setter
    def b(self, b: dict):
        self.two_b = b

    def get_b(self) -> dict:
        return self.two_b

    def set_b(self, b: dict):
        self.two_b = b

    @property
    def c(self):
        return self.two_c

    @c.setter
    def c(self, c: list):
        self.two_c = c

    def get_c(self) -> list:
        return self.two_c

    def set_c(self, c: list):
        self.two_c = c

    @property
    def d(self):
        return self.two_d

    @d.setter
    def d(self, d: SharedClassOne):
        self.two_d = d

    def get_d(self) -> SharedClassOne:
        return self.two_d

    def set_d(self, d: SharedClassOne):
        self.two_d = d

    def add_to_d(self, value):
        self.two_c.append(value)

    @staticmethod
    def static_method(*args, **kwargs):
        return STATIC_METHOD_TWO_VALUE

    @classmethod
    def class_method(cls, *args, **kwargs):
        return CLASS_METHOD_TWO_VALUE

    def instance_method(self, *args, **kwargs):
        return shared_class_two_instance_method_formula(self.a, self.b, self.c, self.d.a)

    def __getitem__(self, item):
        return self.two_c[item]

    def __setitem__(self, key, value):
        self.two_c[key] = value

    def __eq__(self, other):
        return self.get_a() == other.get_a() and self.get_b() == other.get_b() and self.get_c() == other.get_c()

    def __hash__(self):
        return hash((
            self.two_a,
            tuple(self.two_b.items()),
            tuple(self.two_c),
            self.two_d
        ))


context.DMODObjectManager.register_class(SharedClassOne)
context.DMODObjectManager.register_class(SharedClassTwo)


def is_member(obj: type, name: str) -> typing.Literal[True]:
    """
    Assert that there is a member by a given name within a given object

    Args:
        obj: An object to inspect
        name: The name of the member to look for

    Returns:
        True if the check passed

    Raises:
        AssertionError if the member does not exist
    """
    members = [name for name, _ in inspect.getmembers(obj)]
    assert name in members, f"{obj} has no member named {name}"
    return True


def evaluate_member(obj: typing.Any, member_name: typing.Union[str, typing.Sequence[str]], *args, **kwargs) -> typing.Any:
    """
    Perform an operation or investigate an item belonging to an object with the given arguments

    The member name may be chained via '.' or through a sequence. 'prop1.get_a.

    Args:
        obj: The object whose member to invoke or investigate
        member_name: The name of the member in question
        *args: Positional arguments to pass to a function
        **kwargs: Keyword arguments to pass to a function

    Returns:
        The resultant value
    """
    owner, obj = climb_member_chain(obj, member_name)

    if isinstance(obj, property):
        if args:
            result = obj.fset(owner, args[0])
        else:
            result = obj.fget(owner)
    elif not isinstance(obj, typing.Callable):
        result = obj
    elif args and kwargs:
        result = obj(*args, **kwargs)
    elif args:
        result = obj(*args)
    elif kwargs:
        result = obj(**kwargs)
    else:
        result = obj()

    return result


def climb_member_chain(
    obj: object,
    member_name: typing.Union[str, typing.Collection[str]]
) -> typing.Tuple[object, typing.Any]:
    """
    Climbs through a possibly chained list of member variables to retrieve a value

    'a' would retrieve the 'a' member from the passed obj. 'a.b.c' would climb through the 'a' member of obj to get
    the 'b' member, then to get the 'c' member

    Args:
        obj: The object that owns the member to find
        member_name: The path to the member

    Returns:
        The owner of the member and the member value
    """
    # We're going to iterate through parts of a string, so split it by our delimiters, i.e. '.' or '/'
    if isinstance(member_name, str):
        member_name = MEMBER_SPLIT_PATTERN.split(member_name)

    # We need to throw an exception if we don't have something to iterate through
    if not isinstance(member_name, typing.Collection):
        raise Exception(
            f"Cannot climb through the sequence of '{member_name}' names to find a member value because it needs to "
            f"be a sequence of names and is instance a '{type(member_name)}'"
        )

    # We need to throw an error if not all elements of the part are strings
    if not all(isinstance(part, str) for part in member_name):
        unique_types = {type(part).__name__ for part in member_name}
        raise Exception(
            f"Cannot climb through the sequence of '{member_name}' names to find a member value because it needs to "
            f"be a sequence of names but is instead a sequence of [{', '.join(unique_types)}]"
        )

    owner = obj
    for index, name in enumerate(member_name):  # type: int, str
        owner = obj

        if not hasattr(obj, name) and isinstance(obj, typing.Mapping) and name in obj.keys():
            obj = obj[name]
        elif not hasattr(obj, name) and isinstance(obj, typing.Sequence) and STRING_INTEGER_PATTERN.match(name):
            passed_index = int(name)
            obj = obj[passed_index]
        elif context.is_property(obj, name):
            obj: property = getattr(obj.__class__, name)
        else:
            obj = getattr(obj, name)

        if index < len(member_name) - 1 and isinstance(obj, typing.Callable):
            obj = obj()
        elif index < len(member_name) - 1 and isinstance(obj, property):
            obj = obj.fget(owner)

    return owner, obj


class TestObjectManager(unittest.TestCase):
    """
    Defines and runs tests to ensure that the DMODObjectManager behaves as expected in a multiprocessed environment
    """
    @classmethod
    def identifier(cls) -> str:
        """
        An identifier for what test this is and where it came from
        """
        return f"{__file__}:{cls.__name__}"

    def test_evaluate_member(self):
        """
        Checks to make sure that the 'evaluate_member' function used in tests acts correctly
        """
        class LayerOne:
            """
            An example class used as a descriptor in another
            """
            def __get__(self, instance, owner):
                return instance._layer_one_val

            def __set__(self, instance, value):
                instance._layer_one_val = value

            def __init__(self, *args):
                self.__value = list(args)

            def get_value(self):
                return self.__value

            @property
            def value(self):
                return self.__value

            def index(self, idx):
                return self.__value.index(idx)

            def __str__(self):
                return f"{self.__class__.__name__} #{id(self)}: {self.value}"

            def __repr__(self):
                return self.__str__()

            def __eq__(self, other):
                return self.__value == getattr(other, 'value', None)

            def __hash__(self):
                return hash(tuple(self.__value))

        class LayerTwo:
            """
            A class that references the first and is referenced by the following to provide nesting
            """
            def __init__(self, val, *args):
                self.__layer_two_a = val * 3
                self.__layer_two_b = LayerOne(*args)

            def __str__(self):
                return f"{self.__class__.__name__} #{id(self)}: a={self.__layer_two_a}, b={self.__layer_two_b}"

            def __repr__(self):
                return self.__str__()

            def __eq__(self, other: LayerTwo):
                return self.__layer_two_a == other.__layer_two_a and self.__layer_two_b == other.__layer_two_b

            def __hash__(self):
                return hash((self.__layer_two_a, self.__layer_two_b))

            def get_layer_two_a(self):
                return self.__layer_two_a

            def set_layer_two_a(self, val):
                self.__layer_two_a = val * 3

            def get_layer_two_b(self):
                return self.__layer_two_b

            def adjust(
                self,
                multiply_by: typing.Union[int, float],
                add_before: typing.Union[int, float] = None,
                add_after: typing.Union[int, float] = None
            ) -> typing.Union[int, float]:
                if add_before is None:
                    add_before = 0

                if add_after is None:
                    add_after = 0

                return ((self.__layer_two_a + add_before) * multiply_by) + add_after

        class LayerThree:
            layer_one = LayerOne()
            def __init__(self, *args):
                self.layer_three_a = 9
                self.__layer_three_b = LayerTwo(4, *args)
                self._layer_one_val = 2

            def __str__(self):
                return f"{self.__class__.__name__} #{id(self)}: a={self.layer_three_a}, b={self.__layer_three_b}"

            def __repr__(self):
                return self.__str__()

            @property
            def layer_three_b(self):
                return self.__layer_three_b

            @layer_three_b.setter
            def layer_three_b(self, val):
                self.__layer_three_b.set_layer_two_a(val)

        instances = {
            'layer_one': LayerOne(1, 2, 3, 4),
            'layer_two': LayerTwo(4, 1, 2, 3, 4),
            'layer_three': LayerThree(1, 2, 3, 4)
        }

        paths_to_expectations = {
            'layer_one': {
                ("value", ): [1, 2, 3, 4],
                ("get_value",): [1, 2, 3, 4],
                ("index", 4): 3
            },
            'layer_two': {
                ("get_layer_two_a",): 12,
                ("get_layer_two_b",): instances["layer_two"].get_layer_two_b(),
                ("get_layer_two_b.value",): [1, 2, 3, 4],
                ("get_layer_two_b.get_value",): [1, 2, 3, 4],
                ("get_layer_two_b.index", 4): 3,
                ("adjust", 2): 24,
                ("adjust", 2, 2): 28,
                ("adjust", 2, None, 2): 26,
                ("adjust", 2, 2, 2): 30
            },
            'layer_three': {
                ("layer_one",): 2,
                ("layer_three_b",): instances['layer_three'].layer_three_b,
                ("layer_three_b.get_layer_two_a",): 12,
                ("layer_three_b.get_layer_two_b",): instances["layer_two"].get_layer_two_b(),
                ("layer_three_b.get_layer_two_b.value",): [1, 2, 3, 4],
                ("layer_three_b.get_layer_two_b.get_value",): [1, 2, 3, 4],
                ("layer_three_b.get_layer_two_b.index", 4): 3,
                ("layer_three_b.adjust", 2): 24,
                ("layer_three_b.adjust", 2, 2): 28,
                ("layer_three_b.adjust", 2, None, 2): 26,
                ("layer_three_b.adjust", 2, 2, 2): 30
            }
        }

        for instance_name, expectations in paths_to_expectations.items():
            instance = instances[instance_name]
            for arguments, expectation in expectations.items():
                try:
                    evaluated_value = evaluate_member(instance, *arguments)
                except Exception as e:
                    self.fail(
                        f"Could not evaluate {instance_name}.{arguments[0]}"
                        f"{'(' + ', '.join(str(value) for value in arguments[1:]) + ')' if len(arguments) > 1 else ''}:"
                        f" {e}"
                    )
                self.assertEqual(
                    evaluated_value,
                    expectation,
                    f'Expected {instance_name}.{arguments[0]}'
                    f'{"(" + ", ".join(str(value) for value in arguments[1:]) + ")" if len(arguments) > 1 else ""} '
                    f'to be {expectation}, but got {evaluated_value}'
                )

    def test_shared_class_one(self):
        """
        Tests to ensure that operations upon SharedClassOne behave as expected with a local AND remote context
        """
        expected_class_one_members = [
            "a",
            "get_a",
            "set_a",
            "static_method",
            "class_method",
            "instance_method",
            "__eq__",
            "__hash__",
            "__ne__",
            "__lt__",
            "__le__",
            "__gt__",
            "__ge__",
            "__add__",
            "__sub__",
            "__mul__",
            "__truediv__",
            "__floordiv__",
            "__mod__",
            "copy",
            "class_name",
            "class_identifier"
        ]

        with context.DMODObjectManager() as object_manager:
            unshared_class_one: SharedClassOne = SharedClassOne(9)
            shared_class_one: SharedClassOne = object_manager.create_object("SharedClassOne", 9)

            steps = [
                TestStep(
                    operation_name=f"Unshared Class One Instance has '{member_name}'",
                    function=is_member,
                    args=(unshared_class_one, member_name),
                    expected_result=True
                )
                for member_name in expected_class_one_members
            ]
            steps.extend(
                TestStep(
                    operation_name=f"Shared Class One Instance has '{member_name}'",
                    function=is_member,
                    args=(shared_class_one, member_name),
                    expected_result=True
                )
                for member_name in expected_class_one_members
            )

            test = TestSteps(
                series_name="[Test SharedClassOne] Check for member existence",
                steps=steps
            )

            test.assert_success(self)

            test.clear()
            test.series_name = "[Test Proxy Creation] Test SharedClassOne"
            test.add(
                TestStep(
                    operation_name="'get_a()' for Shared Instance is 9",
                    function=evaluate_member,
                    args=(shared_class_one, 'get_a'),
                    expected_result=9
                ),
                TestStep(
                    operation_name="'a' for Shared Instance is 9",
                    function=evaluate_member,
                    args=(shared_class_one, 'a'),
                    expected_result=9
                ),
                TestStep(
                    operation_name="'get_a()' for Unshared Instance is 9",
                    function=evaluate_member,
                    args=(unshared_class_one, 'get_a'),
                    expected_result=9
                ),
                TestStep(
                    operation_name="'a' for Unshared Class One is 9",
                    function=evaluate_member,
                    args=(unshared_class_one, 'a'),
                    expected_result=9
                ),
                TestStep(
                    operation_name="Shared is equal to copy",
                    function=evaluate_member,
                    args=(shared_class_one, 'copy'),
                    expected_result=shared_class_one
                ),
                TestStep(
                    operation_name="Unshared is equal to copy",
                    function=evaluate_member,
                    args=(unshared_class_one, 'copy'),
                    expected_result=unshared_class_one
                ),
                TestStep(
                    operation_name="Shared Copy equal to Unshared",
                    function=evaluate_member,
                    args=(shared_class_one, 'copy'),
                    expected_result=unshared_class_one
                ),
                TestStep(
                    operation_name="Unshared Copy equal to shared",
                    function=evaluate_member,
                    args=(unshared_class_one, 'copy'),
                    expected_result=shared_class_one
                ),
                TestStep(
                    operation_name="Shared Copy equal to Unshared Copy",
                    function=evaluate_member,
                    args=(shared_class_one, 'copy'),
                    expected_result=unshared_class_one.copy()
                ),
                TestStep(
                    operation_name="Unshared Copy equal to shared copy",
                    function=evaluate_member,
                    args=(unshared_class_one, 'copy'),
                    expected_result=shared_class_one.copy()
                ),
                TestStep(
                    operation_name="Shared is equal to unshared",
                    function=evaluate_member,
                    args=(shared_class_one, '__eq__', unshared_class_one),
                    expected_result=True
                ),
                TestStep(
                    operation_name="Unshared is equal to Shared",
                    function=evaluate_member,
                    args=(unshared_class_one, '__eq__', shared_class_one),
                    expected_result=True
                ),
                TestStep(
                    operation_name="Unshared Static Method is Correct",
                    function=evaluate_member,
                    args=(unshared_class_one, 'static_method'),
                    expected_result=STATIC_METHOD_ONE_VALUE
                ),
                TestStep(
                    operation_name="Shared Static Method is Correct",
                    function=evaluate_member,
                    args=(shared_class_one, 'static_method'),
                    expected_result=STATIC_METHOD_ONE_VALUE
                ),
                TestStep(
                    operation_name="Unshared Class Method is Correct",
                    function=evaluate_member,
                    args=(unshared_class_one, 'class_method'),
                    expected_result=CLASS_METHOD_ONE_VALUE
                ),
                TestStep(
                    operation_name="Shared Class Method is Correct",
                    function=evaluate_member,
                    args=(shared_class_one, 'class_method'),
                    expected_result=CLASS_METHOD_ONE_VALUE
                ),
                TestStep(
                    operation_name="Shared Instance Method is Correct",
                    function=evaluate_member,
                    args=(shared_class_one, 'instance_method'),
                    expected_result=81
                ),
                TestStep(
                    operation_name="Unshared Instance Method is Correct",
                    function=evaluate_member,
                    args=(unshared_class_one, 'instance_method'),
                    expected_result=81
                ),
            )

            test.assert_success(self)

            test.clear()
            test.series_name = "[Test SharedClassOne] set_a Mutations are correct"
            test.add(
                TestStep(
                    operation_name="Change 'a' in Shared instance with 'set_a'",
                    function=evaluate_member,
                    args=(shared_class_one, 'set_a', 3),
                ),
                TestStep(
                    operation_name="Change 'a' in Unshared instance with 'set_a'",
                    function=evaluate_member,
                    args=(unshared_class_one, 'set_a', 3),
                ),
            )

            test.assert_success(self)

            self.assertEqual(shared_class_one.a, 3)
            self.assertEqual(unshared_class_one.a, 9)

            shared_class_one.set_a(9)
            self.assertEqual(shared_class_one.get_a(), 9)

            shared_class_one.a = 3
            self.assertEqual(shared_class_one.get_a(), 3)

            shared_class_one.set_a(9)

            test.clear()
            test.series_name = "[Test SharedClassOne] Property Mutations are correct"
            test.add(
                TestStep(
                    operation_name="Change 'a' in Shared instance with 'a'",
                    function=evaluate_member,
                    args=(shared_class_one, 'a', 3),
                ),
                TestStep(
                    operation_name="Change 'a' in Unshared instance with 'a'",
                    function=evaluate_member,
                    args=(unshared_class_one, 'a', 3),
                ),
            )

            test.assert_success(self)

            self.assertEqual(shared_class_one.a, 3)
            self.assertEqual(unshared_class_one.a, 9)
            self.assertEqual(shared_class_one.instance_method(), 27)

    def test_shared_class_two(self):
        """
        Tests to ensure that operations upon SharedClassTwo behave as expected with a local AND remote context
        """
        expected_members: typing.List[str] = [
            "class_name",
            "class_identifier",
            "static_method",
            "class_method",
            "instance_method",
            "copy",
            "a",
            "get_a",
            "set_a",
            "b",
            "get_b",
            "set_b",
            "c",
            "get_c",
            "set_c",
            "d",
            "get_d",
            "set_d",
            "add_to_d",
            "__getitem__",
            "__setitem__",
            "__eq__"
        ]
        """The list of all members expected to be on all instances or proxies of SharedClassTwo"""

        with context.DMODObjectManager() as object_manager:
            control_class_one = SharedClassOne(6)
            """An instance of SharedClassOne expected to serve as a concrete starting point"""

            shared_class_two = object_manager.create_object(
                "SharedClassTwo",
                "one",
                {"two": 2},
                [3, 4, 5],
                SharedClassOne(control_class_one.a)
            )

            fully_shared_class_two = object_manager.create_object(
                "SharedClassTwo",
                "one",
                {"two": 2},
                [3, 4, 5],
                object_manager.create_object("SharedClassOne", control_class_one.a)
            )

            partially_mixed_shared_class_two = SharedClassTwo(
                "one",
                {"two": 2},
                [3, 4, 5],
                object_manager.create_object("SharedClassOne", control_class_one.a)
            )

            unshared_class_two = SharedClassTwo(
                "one",
                {"two": 2},
                [3, 4, 5],
                SharedClassOne(control_class_one.a)
            )

            names_to_instances: typing.Dict[str, SharedClassTwo] = {
                "Shared Class Two": shared_class_two,
                "Unshared Class Two": unshared_class_two,
                "Partially Mixed Class Two": partially_mixed_shared_class_two,
                "Fully Mixed Class Two": fully_shared_class_two
            }

            test: TestSteps = TestSteps(
                series_name="[Test SharedClassTwo] Classes have expected members"
            )

            for name, instance in names_to_instances.items():
                test.add(
                    TestStep(
                        test_name=test.series_name,
                        operation_name=f"{name} has {member_name}",
                        function=is_member,
                        args=(instance, member_name),
                        expected_result=True
                    )
                    for member_name in expected_members
                )

            test.assert_success(self)

            test.clear()
            test.series_name = "[Test SharedClassTwo] Test Values"

            function_to_result: typing.Dict[str, typing.Any] = {
                "get_a": "one",
                "a": "one",
                "get_b": {'two': 2},
                'b': {'two': 2},
                "get_c": [3, 4, 5],
                'c': [3, 4, 5],
                'get_d': control_class_one,
                'd': control_class_one
            }

            for name, instance in names_to_instances.items():
                test.add(
                    TestStep(
                        test_name=test.series_name,
                        operation_name=f"'{function_name}' for {name} is '{expected_value}'",
                        function=evaluate_member,
                        args=(instance, function_name),
                        expected_result=expected_value
                    )
                    for function_name, expected_value in function_to_result.items()
                )

            test.assert_success(self)

            test.clear()
            test.series_name = "[Test SharedClassTwo] Test Equality"

            test.add(
                TestStep(
                    test_name=test.series_name,
                    operation_name=f"'{first_name}' is equal to '{second_name}'",
                    function=evaluate_member,
                    args=(first_instance, "__eq__", second_instance),
                    expected_result=True
                )
                for (first_name, first_instance), (second_name, second_instance) in permutations(names_to_instances.items(), 2)
            )

            test.assert_success(self)

            test.clear()

            self.evaluate_shared_class_two_mutations(names_to_instances=names_to_instances)
            self.evaluate_shared_class_two_mutations(names_to_instances=names_to_instances, use_properties=True)

            test.series_name = "[Test SharedClassTwo] Test Methods"

            test.add(
                TestStep(
                    operation_name=f"Test {type(test).__name__}.static_method for {instance_name}",
                    function=SharedClassTwo.static_method,
                    expected_result=STATIC_METHOD_TWO_VALUE
                )
                for instance_name, instance in names_to_instances.items()
            )

            test.add(
                TestStep(
                    operation_name=f"Test {type(test).__name__}.class_method for {instance_name}",
                    function=SharedClassTwo.class_method,
                    expected_result=CLASS_METHOD_TWO_VALUE,
                )
                for instance_name, instance in names_to_instances.items()
            )

            test.add(
                TestStep(
                    operation_name=f"Test {instance_name}.instance_method",
                    function=SharedClassTwo.instance_method,
                    args=(instance,),
                    expected_result=shared_class_two_instance_method_formula(instance.a, instance.b, instance.c, instance.d.a),
                )
                for instance_name, instance in names_to_instances.items()
            )

            test.assert_success(test_case=self)

    def evaluate_shared_class_two_mutations(
        self,
        names_to_instances: typing.Dict[str, SharedClassTwo],
        use_properties: bool = False
    ):
        """
        Tests mutations of a collection SharedClassTwo objects

        Args:
            names_to_instances: A mapping of names to instances of SharedClassTwo
            use_properties: Whether to use properties to mutate values
        """
        methodology_in_use = 'Properties' if use_properties else 'Setters'
        test = TestSteps(series_name=f"[Test SharedClassTwo] Test Mutations Using {methodology_in_use}")

        mutations: typing.Dict[str, typing.Dict[str, MutationTuple]] = {
            instance_name: {
                "a" if use_properties else "set_a": MutationTuple(
                    'a' if use_properties else 'get_a',
                    make_word(avoid=instance.get_a()),
                    isinstance(instance, managers.BaseProxy)
                ),
                'b' if use_properties else "set_b": MutationTuple(
                    'b' if use_properties else 'get_b',
                    make_numbers(avoid=instance.get_b()),
                    isinstance(instance, managers.BaseProxy)
                ),
                'c' if use_properties else "set_c": MutationTuple(
                    'c' if use_properties else 'get_c',
                    {
                        make_word(): make_number()
                        for _ in range(random.randint(3, 12))
                    },
                    isinstance(instance, managers.BaseProxy)
                ),
                'd.a' if use_properties else "d.set_a": MutationTuple(
                    'd.a' if use_properties else 'd.get_a',
                    make_number(avoid=instance.d.a),
                    isinstance(instance.d, managers.BaseProxy)
                ),
            }
            for instance_name, instance in names_to_instances.items()
        }

        for instance_name, instance in names_to_instances.items():
            test.add(
                TestStep(
                    operation_name=f"Use '{action}' to set '{field}' to '{value}' on {instance_name}",
                    function=evaluate_member,
                    args=(instance, action, value),
                    expected_result=None
                )
                for action, (field, value, _) in mutations[instance_name].items()
            )

        test.assert_success(self)

        for instance_name, mutation_operations in mutations.items():
            instance = names_to_instances[instance_name]
            for mutator, (field, value, should_be_equal) in mutation_operations.items():
                try:
                    evaluated_value = evaluate_member(instance, field)
                except Exception as e:
                    self.fail(f"Could not read the field '{field}' from '{instance_name}' - {e}")

                if should_be_equal:
                    self.assertEqual(
                        evaluated_value,
                        value,
                        f"The mutation for {instance_name}.{mutator}({value}) did not yield '{value}' as expected."
                    )
                else:
                    self.assertNotEqual(
                        evaluated_value,
                        value,
                        f"The mutation for {instance_name}.{mutator}({value}) should not have changed since it "
                        f"was not supposed to be a shared value"
                    )

if __name__ == '__main__':
    unittest.main()
