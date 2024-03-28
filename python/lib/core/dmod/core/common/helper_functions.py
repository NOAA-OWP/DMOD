"""
Provides simple helper functions
"""
import logging
import pathlib
import shutil
import typing
import inspect
import math
import json
import numbers
import re
import random
import string

from collections import OrderedDict

try:
    import numpy
except ImportError:
    numpy = None

from .types import TypeDefinition

_CLASSTYPE = typing.TypeVar('_CLASSTYPE')
"""A type that points directly to a class. The _CLASSTYPE of `6`, for example, is `<class 'int'>`"""


_T = typing.TypeVar('_T')
"""A type used in conjunction with `_CLASS_TYPE`"""

_KT = typing.TypeVar('_KT')
"""A type used as a key for a map"""


def get_mro_names(value) -> typing.List[str]:
    """
    Get the names of all members of a value's MRO list

    Args:
        value: Any value that might have an MRO list

    Returns:
        The names of all entries in the value's mro list
    """
    if not isinstance(value, type):
        value = value.__class__

    if hasattr(value, "__mro__"):
        return [
            entry.__name__
            for entry in inspect.getmro(value)
        ]

    return []


def is_integer(value) -> bool:
    """
    Checks if a value is some strict numerical representation of an integer

    Args:
        value: The value to check

    Returns:
        True if the value is an int or numpy integer
    """
    return isinstance(value, (int, numpy.integer)) if numpy else isinstance(value, int)


def is_float(value) -> bool:
    """
    Checks if a value is some strict numerical representation of a floating point number

    Args:
        value: The value to check

    Returns:
        True if the value is a float or numpy floating point object
    """
    return isinstance(value, (float, numpy.floating)) if numpy else isinstance(value, float)


_PRIMITIVE_TYPE_IDENTIFIERS = [
    (is_integer, int),
    (is_float, float),
    (lambda x: isinstance(x, str), str),
    (lambda x: isinstance(x, bytes), bytes),
    (lambda x: isinstance(x, bool), bool),
    (lambda x: x is None, type(None))
]
"""Mapping between a function that indicates that a value is of a given type and an identifier for that type"""


def get_iterable_type(iterable: typing.Iterable) -> typing.Optional[typing.Type]:
    """
    Get the uniform type of each value in the iterable. Types are considered uniform if all values share a common
    subclass

    The check is shallow

    The check may not be performed on Generators since there is no guarantee that iteration won't mutate the object

    Args:
        iterable: An iterable object whose values may be checked

    Returns:
        The type that all values in the iterable adhere to.
        None if they aren't all the same type or if there are no values to check
    """
    if isinstance(iterable, typing.Generator):
        raise ValueError(
            f"Cannot check if all types of a {iterable.__class__.__name__} are of the same type. "
            f"Generators are not supported."
        )

    if not is_iterable_type(iterable):
        raise ValueError(
            f"'{get_current_function_name()}' cannot determine if a '{iterable.__class__.__name__}' "
            f"is of a uniform type. The object must be iterable and not a map or generator."
        )

    iterable_type = None
    iterable_is_integer = False
    iterable_is_float = False
    valid_values = []

    for value in iterable:
        if iterable_type is None:
            if is_float(value):
                iterable_type = float
            elif is_integer(value):
                iterable_type = int
            else:
                iterable_type = get_primitive_value_type(value) or value.__class__

            valid_values.append(value)
        elif isinstance(value, iterable_type):
            valid_values.append(value)
        elif is_integer(value) and iterable_is_integer:
            # Integer values have been reimplemented by several libraries, so check to see if the value is in the
            # same bucket as the preexisting type if they haven't matched up. int(8) and numpy.int16(8) are
            # functionally the same value, but aren't marked as the same type. Cast the value to make sure
            # it's the base int, set the type as the base int, and you're good to go
            valid_values.append(int(value))
            iterable_type = int
        elif is_float(value) and iterable_is_float:
            # float values have been reimplemented by several libraries, so check to see if the value is in the
            # same bucket as the preexisting type if they haven't matched up. float(8) and numpy.float16(8) are
            # functionally the same value, but aren't marked as the same type. Cast the value to make sure
            # it's the base float, set the type as the base float, and you're good to go
            valid_values.append(float(value))
            iterable_type = float
        else:
            branching_value_type = get_primitive_value_type(value) or value.__class__
            if len([entry for entry in valid_values if isinstance(entry, branching_value_type)]) == len(valid_values):
                # If the value isn't of the found type, but IS of a parent class of the found type, reset the found type
                # and add this value to the list. You might see this in a collection that holds both numpy floats and
                # python floats.
                valid_values.append(value)
                iterable_type = branching_value_type
            else:
                # There isn't a perfectly uniform type if a type has been defined, the current value isn't of that
                # type, and existing values aren't descendents of the current value's type. Operation may end
                return None

    if iterable_type == object:
        # 'object' is the lowest common denominator - consider there being no common ancestor if they are all
        # just generic 'object's
        return None

    return iterable_type


def sequence_is_uniform_primitives(sequence: typing.Sequence) -> bool:
    """
    Indicates if a given sequence is one of pure primitive values

    Args:
        sequence: A sequence of different values

    Returns:
        True if all the values within the sequence are of the same primitive type
    """
    types = set()

    for value in sequence:
        found_match = False
        for type_function, identifier in _PRIMITIVE_TYPE_IDENTIFIERS:
            if type_function(value):
                types.add(identifier)
                found_match = True
                break
        if not found_match:
            return False

    return len(types) == 1


def get_primitive_sequence_type(sequence: typing.Sequence) -> typing.Optional[typing.Type]:
    """
    Gets the primitive uniform type of a sequence of values if there is one

    Args:
         sequence: The sequence of values to check

    Returns:
        A 'primitive' value that all values match
    """
    types = set()

    for value in sequence:
        matching_type = get_primitive_value_type(value)
        if matching_type:
            types.add(matching_type)
        else:
            return None

    return types.pop() if len(types) == 1 else None


def get_primitive_value_type(value) -> typing.Optional[type]:
    """
    Get the python primitive analog type for a value if it exists.

    A numpy integer does not inherit from an int, but it IS an int for all intents and purposes. Anywhere an int is
    used, a numpy integer can be used and they are almost interchangeable. As a result, a numpy may as well be an int,
    but an isinstance check will fail. This will find the matching primitive type for the value if there is one

    Args:
        value: The value to find a primitive for

    Returns:
        A primitive type if there is one that matches the given value
    """
    for is_current_primitive_type, primitive_type in _PRIMITIVE_TYPE_IDENTIFIERS:
        if is_current_primitive_type(value):
            return primitive_type

    return None


def generate_identifier(length: int = None) -> str:
    """
    Generate a simple random identifier

    Example:
        >>> generate_identifier()
        a7Sf6SFs7A
        >>> generate_identifier(3)
        Di7

    Args:
        length: The number of characters in the identifier

    Returns:
        A random string identifier
    """
    if length is None:
        length = 10

    if not isinstance(length, typing.SupportsInt):
        raise TypeError(
            f"Only an integer-like object may be used as the length to generate an identifier. "
            f"Received '{length}' instead."
        )

    if not isinstance(length, int) and isinstance(length, typing.SupportsInt):
        length = int(length)

    if length <= 0:
        raise ValueError(
            f"Only positive, nonzero integers may be used to generate identifiers. Received '{length}' instead."
        )

    return "".join([random.choice(string.ascii_letters + string.digits) for _ in range(length)])


def generate_key(phrases: int = None, length: int = None) -> str:
    """
    Generate a simple key

    Example:
        >>> generate_key()
        s8Sfi-83kSn-SFSNI-a832H-932JS
        >>> generate_key(3)
        a9DSi-SF8Wk-SifS2
        >>> generate_key(length=2)
        s2-SD-c2-F9-sf
        >>> generate_key(phrases=2, length=2)
        f2-SF

    Args:
        phrases: The number of groups within the key
        length: The number of characters in each phrase

    Returns:
        A random key made of a number of phrases of a given length
    """
    if phrases is None:
        phrases = 5

    if length is None:
        length = 5

    if not isinstance(length, typing.SupportsInt):
        raise TypeError(
            f"Only an integer-like object may be used as the number of phrases to generate a key. "
            f"Received '{phrases}' instead."
        )

    if not isinstance(phrases, int) and isinstance(phrases, typing.SupportsInt):
        phrases = int(phrases)

    if phrases <= 0:
        raise ValueError(
            f"Only positive, nonzero integers may be used to generate keys. Received '{phrases}' instead."
        )

    if not isinstance(length, typing.SupportsInt):
        raise TypeError(
            f"Only an integer-like object may be used as the length to generate a key. "
            f"Received '{length}' instead."
        )

    if not isinstance(length, int) and isinstance(length, typing.SupportsInt):
        length = int(length)

    if length <= 0:
        raise ValueError(
            f"Only positive, nonzero integers may be used to generate identifiers. Received '{length}' instead."
        )

    return "-".join([generate_identifier(length) for _ in range(phrases)])


def get_current_function_name(parent_name: bool = None) -> str:
    """
    Gets the name of the current function (i.e. the function that calls `get_current_function_name`)

    Call with `parent_name` set to True to get the name of the caller's caller

    Examples:
        >>> def outer():
        >>>     def inner():
        >>>         print(get_current_function_name())
        >>>         print(get_current_function_name(parent_name=True))
        >>>     inner()
        inner
        outer

    Args:
        parent_name: Whether to get the caller of the caller that tried to get a name

    Returns:
        The name of the current function
    """
    stack: typing.List[inspect.FrameInfo] = inspect.stack()

    # Get the info for the second object in the stack - the first frame listed will be for THIS function
    # (`get_current_function_name`)
    if not parent_name:
        frame_index = 1
    else:
        # Get the info for the third object in the stack - the first frame listed will be for THIS function
        # (`get_current_function_name`) and the second will be the function that callled `get_current_function_name`
        frame_index = 2

    caller_info: inspect.FrameInfo = stack[frame_index]
    return caller_info.function


def contents_are_equivalent(first_content, second_content):
    """
    Checks to see whether two objects match based on rules for collections

    To access the specialized container equivalence, both first and second must be sized and iterable,
    and either both or neither are mappings, otherwise a standard equivalence check is used.

    If they are not both the same length, return False

    If either are bytes, they are converted to strings.

    If one is a string, a standard equivalence check is performed

    If they are mappings, check to make sure both have the same keys and values for those keys

    If they are sequences, check to make sure each has the same element in the same position

    Otherwise check to make sure all the elements in one are in the other the same number of times

    Why use this?:
        [1, 2, 3, 4] and (1, 2, 3, 4) may both be a sequence of the same values, but they won't pass equivalence testing

    Args:
        first_content: The first object to compare
        second_content: The second object to compare

    Returns:
        Whether first and second are equivalent objects
    """
    if first_content is None and second_content is None:
        return True

    if (first_content is None) ^ (second_content is None):
        return False

    # You can't check length if one isn't sized, so default to standard equivalence
    if not isinstance(first_content, typing.Sized) or not isinstance(second_content, typing.Sized):
        return first_content == second_content

    # They aren't equal if they have different sizes
    if len(first_content) != len(second_content):
        return False

    # Proper mapping equivalence can't be performed if one is a map and the other isn't. Fall back to standard
    # equivalence if only one is a map
    if isinstance(first_content, typing.Mapping) ^ isinstance(second_content, typing.Mapping):
        return first_content == second_content

    # If they aren't iterable, go ahead and perform a standard equivalence
    if not isinstance(first_content, typing.Iterable) or not isinstance(second_content, typing.Iterable):
        return first_content == second_content

    # If the first element is a set of bytes, normalize the values by decoding
    first_content = first_content.decode() if isinstance(first_content, bytes) else first_content

    # If the second element is a set of bytes, normalize the values by decoding
    second_content = second_content.decode() if isinstance(second_content, bytes) else second_content

    # If one is a string, perform a standard equivalence
    if isinstance(first_content, str) or isinstance(second_content, str):
        return first_content == second_content

    if isinstance(first_content, typing.Mapping) and isinstance(second_content, typing.Mapping):
        for key_in_first, value_in_first in first_content.items():
            if key_in_first not in second_content.keys():
                return False

            if value_in_first != second_content[key_in_first]:
                return False
        return True

    return sequences_are_equal(first_sequence=first_content, second_sequence=second_content)


def sequences_are_equal(first_sequence: typing.Iterable, second_sequence: typing.Iterable) -> bool:
    """
    Checks if two series of values are the same

    If the collections are both sequences, order will be considered, otherwise not

    Args:
        first_sequence: The first series to compare
        second_sequence: The second series to compare

    Returns:
        True if both collections are equivalent
    """
    if isinstance(first_sequence, typing.Sequence) and isinstance(second_sequence, typing.Sequence):
        if len(first_sequence) != len(second_sequence):
            return False

        for element_index, _ in enumerate(first_sequence):
            if first_sequence[element_index] != second_sequence[element_index]:
                return False
        return True
    return iterables_are_equivalent(first_values=first_sequence, second_values=second_sequence)


def iterables_are_equivalent(first_values: typing.Iterable, second_values: typing.Iterable) -> bool:
    """
    Checks if two iterable values have the same objects, disregarding order

    Examples:
        >>> iterables_are_equivalent([1, 2, 3, 4], [1, 2, 3, 4])
        True
        >>> iterables_are_equivalent([1, 2, 3, 4], [4, 3, 2, 1])
        True
        >>> iterables_are_equivalent([1, 2, 3, 4], [1, 2, 2, 3, 4])
        False

    Args:
        first_values: The first series of values
        second_values: The second series of values

    Returns:
        True if both iterables have the same contents
    """
    second_copy = list(second_values)

    for element_in_first in first_values:
        found_value = False
        for element_in_second in second_copy:
            if element_in_first == element_in_second:
                second_copy.remove(element_in_second)
                found_value = True
                break
        if not found_value:
            return False

    # Fail if not all values weren't removed from the copy of second
    if len(second_copy) > 0:
        return False

    # Repeat the above steps with the second collection to ensure that all possible edge cases are covered
    first_copy = list(first_values)

    for element_in_second in second_values:
        found_value = False
        for element_in_first in first_copy:
            if element_in_first == element_in_second:
                first_copy.remove(element_in_first)
                found_value = True
                break
        if not found_value:
            return False

    return True


def is_sequence_type(value: typing.Any) -> bool:
    """
    Checks to see if a value is one that can be interpretted as a collection of values

    Why not just use `isinstance(value, typing.Sequence)`? Strings, bytes, and maps ALL count as sequences

    Args:
        value: The value to check

    Returns:
        Whether the passed value is a sequence
    """
    is_collection = value is not None
    is_collection = is_collection and not isinstance(value, (str, bytes, typing.Mapping))
    is_collection = is_collection and isinstance(value, typing.Sequence)

    return is_collection


def is_iterable_type(value: typing.Any) -> bool:
    """
    Checks to see if a value is one that can be interpreted as a series of iterable values.

    Why not just use `isinstance(value, typing.Iterable)` or `is_sequence_type` from above? Strings, bytes, and
    maps all count as iterables and `is_sequence_type` leaves out sets.

    Use this when order doesn't matter. Use `is_sequence_type` when order DOES matter

    Args:
        value: The value to check

    Returns:
        Whether the passed value is an iterable collection of isolated values
    """
    is_collection = value is not None
    is_collection = is_collection and not isinstance(value, (str, bytes, typing.Mapping))
    is_collection = is_collection and isinstance(value, typing.Iterable)

    return is_collection


def get_common_type(value: typing.Any) -> typing.Optional[typing.Type]:
    """
    Get the common type across everything passed in. If the value passed in is iterable, it will look for a
    common type amongst all values. If the value is a scalar, it will return the type of that value. If more than one
    type is encountered within a collection, `None` is returned since there is no common type

    Args:
        value: A value whose type to inspect

    Returns:
        The type of value that applies to all entries or None if the types are not 100% common
    """
    return get_iterable_type(value) if is_iterable_type(value) else type(value)


def iterable_types_are_uniform(value: typing.Any) -> bool:
    """
    Checks to see if every item in an iterable is of the same type

    Args:
        value: The value to check

    Returns:
        True if the value was a collection whose values were all of the same type
    """
    if not is_iterable_type(value):
        return False

    encountered_type = None
    member_value = None

    for member in value:
        member_type = type(member)
        if encountered_type is None:
            encountered_type = member_type
            member_value = member
        elif not isinstance(member, encountered_type) and isinstance(member_value, member_type):
            encountered_type = member_type
            member_value = member
        elif not isinstance(member, encountered_type):
            return False

    return True


def truncate(number: typing.Union[numbers.Number, float], digits: int) -> typing.Union[numbers.Number, float]:
    """
    Truncate a float by the desired number of digits

    Example:
        >>> example_value = 10.1231244121235435
        >>> math.trunc(example_value)
        10
        >>> truncate(example_value, 3)
        10.123
        >>> truncate(example_value, 5)
        10.12312

    Args:
        number: The number to truncate
        digits: The number of desired digits

    Returns:
        The floating point number truncated to the specified number of digits
    """
    if digits <= 0:
        return number

    if not isinstance(digits, int):
        raise TypeError(
            f"The number {number} cannot be truncated - "
            f"the number of digits to truncate by must be an integer and received {type(digits)} instead"
        )

    # We'll use the number 10.23423523423 and the desired number of digits as 3 as an example

    # This gives us "10.23423523423"
    string_representation = str(number)

    if "." not in string_representation:
        return number

    # Find the number of current decimal points in order to avoid operations if necessary.
    # This will yield 11 for our example
    number_of_decimal_points = len(string_representation.split('.')[1])

    # If the current number of digits is less than or equal to the number of desired digits, we can move on
    # Our example has 11 decimal points, which is greater than the desired 3, so we continue
    if number_of_decimal_points <= digits:
        return number

    # Create a factor that will shift the desired number of decimal points
    # This will create 1000 for our example
    adjuster = 10.0 ** digits

    # This will shift the number by the desired number of decimal points
    # This yields 10234.23523423 for our example
    adjusted_value = adjuster * number

    # This will get rid of the extra digits
    # Our example value now becomes 10234.0
    adjusted_value = math.trunc(adjusted_value)

    # This will shift the value back to the desired number of decimal points
    # Our example value now becomes 10.324
    return adjusted_value / adjuster


def get_subclasses(base: typing.Type[_CLASSTYPE]) -> typing.List[typing.Type[_CLASSTYPE]]:
    """
    Gets a collection of all concrete subclasses of the given class in memory

    A subclass that has not been imported will not be returned

    Example:
        >>> import numpy
        >>> get_subclasses(float)
        [numpy.float64]

    Args:
        base: The base class to get subclasses from

    Returns:
        All implemented subclasses of a specified types
    """
    concrete_classes = [
        subclass
        for subclass in base.__subclasses__()
        if not inspect.isabstract(subclass)
    ]

    for subclass in base.__subclasses__():
        concrete_classes.extend([
            cls
            for cls in get_subclasses(subclass)
            if cls not in concrete_classes
               and not inspect.isabstract(cls)
        ])

    return concrete_classes


def on_each(
    func: typing.Callable[[_CLASSTYPE], typing.Any],
    collection: typing.Iterable[_CLASSTYPE]
) -> typing.NoReturn:
    """
    Calls the passed in function on every item in the collection. The input collection is not mutated

    Why use this instead of the builtin map function(s)? The builtin functions create generators rather than actually
    performing the requested actions, meaning you have to iterate over the generated map, rather than the call just
    running.

        >>> def p(obj) -> typing.NoReturn:
        >>>     print(obj)
        >>> example_collection = [1, 2, 3]
        >>> map(p, example_collection) # Doesn't actually do anything; just creates a collection and throws it away
        >>> operation = None
        >>> # Calls print on every element in the collection and assigns the results to the `results` collection
        >>> map_results = [operation for operation in map(p, example_collection)]
        1
        2
        3
        >>> on_each(p, example_collection) # Just calls print on every element in the collection
        1
        2
        3

    Args:
        collection: The items to use as arguments for each function
        func: The function to call on each element
    """
    for element in collection:
        func(element)


def flat(collection: typing.Iterable[typing.Iterable[_CLASSTYPE]]) -> typing.Sequence[_CLASSTYPE]:
    """
    Flatten a collection of collections

    Examples:
        >>> example_values = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        >>> flat(example_values)
        [1, 2, 3, 4, 5, 6, 7, 8, 9]
        >>> second_example_values = {
        ...     "one": [1, 2, 3],
        ...     "two": [4, 5, 6],
        ...     "three": 7,
        ...     "four": 8,
        ...     "five": 9
        ... }
        >>> flat(second_example_values)
        [1, 2, 3, 4, 5, 6, 7, 8, 9]

    Args:
        collection: The collection of collections to flatten

    Returns:
        A flattened representation of the given values
    """
    flattened_list: typing.MutableSequence[_CLASSTYPE] = []

    if isinstance(collection, typing.Mapping):
        for mapped_value in collection.values():
            if is_iterable_type(mapped_value):
                flattened_list.extend(mapped_value)
            else:
                flattened_list.append(mapped_value)
    else:
        for inner_collection in collection:
            flattened_list.extend(inner_collection)

    return flattened_list


def flatmap(
    function: typing.Callable[[_CLASSTYPE], _T],
    collection: typing.Union[
        typing.Iterable[typing.Iterable[_CLASSTYPE]],
        typing.Mapping[_KT, typing.Iterable[_CLASSTYPE]]
    ]
) -> typing.Sequence[_T]:
    """
    Call a mapping function on each element of either a collection of collections or a map of collections

    Examples:
        >>> dict_example = {'first': [1, 2, 3], 'second': [4, 5, 6]}
        >>> list_example = [[7, 8, 9], [10, 11, 12]]
        >>> def mutate_value(value: int) -> str:
        ...     return str(value * 2)
        >>> flatmap(mutate_value, dict_example)
        ['2', '4', '6', '8', '10', '12']
        >>> flatmap(mutate_value, list_example)
        ['14', '16', '18', '20', '22', '24']

    Args:
        collection: The collection of collections
        function: A transformative function to call on each value within the collection of collections

    Returns:
        A single collection of all mapped values
    """
    if isinstance(collection, typing.Mapping):
        data_to_flatten: typing.Iterable[typing.Iterable[_CLASSTYPE]] = collection.values()
    else:
        data_to_flatten: typing.Iterable[typing.Iterable[_CLASSTYPE]] = collection

    # Flatten the data
    flattened_data = flat(data_to_flatten)

    # Now map the data
    return [function(entry) for entry in flattened_data]


def find(
    iterable: typing.Iterable[_CLASSTYPE],
    predicate: typing.Callable[[_CLASSTYPE], bool],
    default: _CLASSTYPE = None
) -> typing.Optional[_CLASSTYPE]:
    """
    Find the first value in an iterable that complies with the give predicate

    The pythonic approach to this is:

        >>> next(filter(lambda val: val == 999, range(1000000)), None)

    This results in lower cognitive overload

    Examples:
        >>> class ExampleClass:
        ...     def __init__(self, value1: int, value2: str, value3: bool):
        ...         self.value1 = value1
        ...         self.value2 = value2
        ...         self.value3 = value3
        ...     def __repr__(self):
        ...         return f'[value1: {self.value1}, value2: {self.value2}, value3: {self.value3}]'
        >>> example_collection = [
        ...     ExampleClass(8, "example", False)
        ...     ExampleClass(9, "example", True)
        ...     ExampleClass(10, "other", True)
        ...     ExampleClass(11, "other", False)
        ...     ExampleClass(27, "Found it", False)
        ... ]
        >>> find(example_collection, lambda entry: entry.value1 % 9 == 0 and not entry.value3)
        value1: 27

    Args:
        iterable: The collection to search
        predicate: A check to see if the encountered value matches the desired value
        default: The default value to return if the value isn't found

    Returns:
        The first value matching the value, the default if a matching value isn't found.
    """
    if not iterable:
        return None

    return next(filter(predicate, iterable), default)


def first(values: typing.Iterable[_CLASSTYPE]) -> typing.Optional[_CLASSTYPE]:
    """
    Return the first item in an iterable object

    Args:
        values: A collection of values that may be iterable over

    Returns:
        The first item in the collection if there are any items in the collection
    """
    for value in values:
        return value
    return None


def true_for_all(
    collection: typing.Iterable[_CLASSTYPE],
    condition: typing.Callable[[_CLASSTYPE], bool] = None
) -> bool:
    """
    Checks to see if all items in the given collection match the given condition. Equivalent to `all(collection)`
    if no condition is passed

    Args:
        collection: The values to check
        condition: A condition to check across all. The default is 'is not None'

    Returns:
        True if the condition is true across all values in the collection
    """
    if collection is None:
        raise ValueError("Cannot tell if all values meet the condition - none were passed")

    if isinstance(collection, typing.Generator):
        raise ValueError(
            f"'{get_current_function_name()}' is not valid for '{collection.__name__}' objects since there is no"
            f" guarantee that the collection won't be modified"
        )

    if isinstance(collection, (str, bytes, typing.Mapping)):
        raise ValueError(f"The passed '{collection.__class__}' object is not a valid collection type")

    if condition is None:
        def condition(value: _CLASSTYPE) -> bool:
            return bool(value)

    for collection_value in collection:
        if not condition(collection_value):
            return False

    return True


def is_true(value) -> bool:
    """
    Check to see what the boolean value of a value is

    The `bool` function does not adequately check if a value is true or false in all cases so this covers some of
    those that don't fit by default

    The following strings (case and whitespace insensitive) evaluate to true:
        - "True"
        - "Yes"
        - "Y"
        - "On"
        - "T"
        - "1"

    Example:
        >>> bool("True")
        True
        >>> bool("False")
        True
        >>> bool("0")
        True
        >>> bool(0)
        False
        >>> is_true("True")
        True
        >>> is_true("False")
        False
        >>> is_true("0")
        False
        >>> is_true("1")
        True

    Arguments:
        value: Some value to check

    Returns:
        Whether the value to equivalent to `True`
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, bytes):
        value = value.decode()

    if isinstance(value, str):
        value = value.lower().strip()
        return value in ('true', 'y', 'yes', '1', 't', 'on')

    try:
        return bool(value)
    except ValueError:
        return value is not None


def order_dictionary(dictionary: typing.Mapping) -> dict:
    """
    Order a given dictionary so that primitive-like values appear in name ordering first, then values without an mro,
    __slots__, or __dict__ sorted by name, then array-like items sorted by name, then basic object-like items sorted
    by name, then finally mappings ordered by name.

    Nested dictionaries are also ordered.

    Example:
        >>> example = {
            "two": 2.0,
            "three": False,
            "one": 1,
            "four": b"bytes",
            "five": [1, 2, 3, 4, 5],
            "six": datetime.now(),
            "seven": SomeClass(),
            "eight": {
                "z": b'z',
                "a": {
                    "q": 99,
                     "f": None
                },
                "y": 9
            }
        }
        >>> order_dictionary(example)
        {
            "four": b"bytes",
            "one": 1,
            "three": False,
            "two": 2.0,
            "six": <class datetime>,
            "seven": <class SomeClass>,
            "five": [1, 2, 3, 4, 5],
            "eight": {
                "y": 9,
                "z": b'z',
                "a": {
                    "f": None,
                    "q": 99
                }
            }
        }

    Arguments:
         dictionary: The mapping to order

    Returns:
        An reording of the dictionary from least complex to theoretically most complex values
    """
    primitive_keys: typing.List[str] = []
    array_keys: typing.List[str] = []
    mapping_keys: typing.List[str] = []
    object_keys: typing.List[str] = []
    non_mro_keys: typing.List[str] = []

    for key, value in dictionary.items():
        if isinstance(key, (str, bytes, bool, numbers.Number)) or value is None:
            primitive_keys.append(key)
        elif isinstance(value, typing.Mapping):
            mapping_keys.append(key)
        elif isinstance(value, typing.Collection):
            array_keys.append(key)
        elif not (hasattr(value, "__mro__") or hasattr(value, "__dict__") or hasattr(value, "__slots__")):
            non_mro_keys.append(key)
        else:
            object_keys.append(key)

    ordered_dictionary = OrderedDict()

    for key in sorted(primitive_keys):
        ordered_dictionary[key] = dictionary[key]

    for key in sorted(non_mro_keys):
        ordered_dictionary[key] = dictionary[key]

    for key in sorted(array_keys):
        ordered_dictionary[key] = dictionary[key]

    for key in sorted(object_keys):
        ordered_dictionary[key] = dictionary[key]

    for key in sorted(mapping_keys):
        ordered_dictionary[key] = order_dictionary(dictionary[key])

    return ordered_dictionary


def truncate_numbers_in_dictionary(
    dictionary: typing.MutableMapping,
    places: int,
    copy: bool = False
) -> typing.MutableMapping:
    """
    Walks a mapping and replaces all floating point values with values truncated to the given number of
    significant digits

    Args:
        dictionary: The dictionary to iterate through
        places: The maximum decimal places to use for floating-point numbers
        copy: Whether to create a whole new copy of the dictionary

    Returns:
        A dictionary where all floating point values have been truncated
    """
    if places is None or places <= 0:
        return dictionary

    dictionary = dict(dictionary.items()) if copy else dictionary

    for key, value in dictionary.items():
        if isinstance(value, numbers.Number) and "." in str(key):
            dictionary[key] = truncate(value, places)
        elif isinstance(value, typing.MutableMapping):
            dictionary[key] = truncate_numbers_in_dictionary(value, places, copy)

    return dictionary


def to_json(obj, encoder: json.JSONEncoder = None, indent: int = 4, truncate_digits: int = None) -> str:
    """
    Convert an object into a regularly ordered JSON string. This ordering is more human-readable

    Examples:
        >>> to_json({"one": [1, 2, 3], "two": 2.0122311312412, "three": False})
        '{
            "three": false,
            "two": 2.0122311312412,
            "one": [1, 2, 3]
        }'
        >>> to_json({"one": [1, 2, 3], "two": 2.0122311312412, "three": False}, truncate_digits=2)
        '{
            "three": false,
            "two": 2.01,
            "one": [1, 2, 3]
        }'
        >>> to_json({"two": 2.0122311312412, "one": [1, 2, 3], "three": False}, truncate_digits=2)
        '{
            "three": false
            "two": 2.01,
            "one": [1, 2, 3]
        }'

    Args:
        obj: The object to be converted to json
        encoder: An optional encoder to use instead of the default JSONEncoder
        indent: The number of spaces to indent after keys
        truncate_digits: The number of digits to truncate off of floating point values if present or needed

    Returns:
        A regularly ordered json string
    """
    if indent is None or indent < 0:
        indent = 4

    first_layer: str = json.dumps(obj, cls=encoder, indent=indent)

    dictionary_representation = json.loads(first_layer)
    dictionary_representation = truncate_numbers_in_dictionary(dictionary_representation, truncate_digits)

    ordered_dictionary = order_dictionary(dictionary_representation)

    second_layer: str = json.dumps(ordered_dictionary, cls=encoder, indent=indent)

    return second_layer


def humanize_text(
    text: typing.Union[str, bytes],
    exclude_phrases: typing.Union[typing.Iterable[str], str, bytes] = None
) -> typing.Optional[str]:
    """
    Reformat text to be more visually informative for people

    Example:
        >>> word_to_fix = "word1NWC nationalWeather\tservice "
        >>> fixed_word = humanize_text(word_to_fix)
        >>> print(fixed_word)
        Word 1 NWC National Weather Service
        >>> word_to_fix = "DataSourceSpecification"
        >>> fixed_word = humanize_text(word_to_fix, exclude_phrases=["spEcIfIcAtiOn"])
        >>> print(fixed_word)
        Data Source
        >>> word_to_fix = "iNeedAAABatteriesNotAA"
        >>> fixed_word = humanize_text(word_to_fix)
        >>> print(fixed_word)
        I Need AAA Batteries Not AA
        >>> word_to_fix = "  my   removeRemoveThis This text  "
        >>> fixed_word = humanize_text(word_to_fix, exclude_phrases=["Remove This"])
        >>> print(fixed_word)
        My Text

    Note:
        Special whitespace characters are not maintained and will just be replaces by a single space

    Args:
        text: The text to make friendlier for people
        exclude_phrases: Phrases to remove from the given text. Removals are case-insensitive.
            Regex patterns will yield unpredictable results

    Returns:
        A reformatted string that appeals more to people
    """
    if not text:
        return text

    if exclude_phrases is None:
        exclude_phrases = []

    if isinstance(exclude_phrases, bytes):
        exclude_phrases = exclude_phrases.decode()

    if isinstance(exclude_phrases, str):
        exclude_phrases = [exclude_phrases]

    if isinstance(text, bytes):
        text = text.decode()

    # Since '_' is often a replacement for whitespace separators, convert '_' to ' ' to offer a consistent look
    text = text.replace("_", " ")
    text = text.strip()

    text = remove_phrases_from_text(text=text, phrases_to_exclude=exclude_phrases)

    text = re.sub("  +", " ", text)
    text = text.strip()

    humanized_text: str = ""

    for letter_index, current_character in enumerate(text):
        previous_character = text[letter_index - 1] if letter_index > 0 else None
        next_character = text[letter_index + 1] if letter_index < len(text) - 1 else None

        humanized_text += convert_character_to_humanized_case(
            current_character=current_character,
            previous_character=previous_character,
            next_character=next_character
        )

    humanized_text = remove_phrases_from_text(text=humanized_text, phrases_to_exclude=exclude_phrases)

    # Remove any possible double spaces that were added as a result of string manipulation.
    # If fixing "My removeThis Text" yielded "My Remove This Text", then yielded "My  Text",
    # this replacement will result in "My Text"
    humanized_text = re.sub("  +", " ", humanized_text)
    humanized_text = humanized_text.strip()

    return humanized_text


def remove_phrases_from_text(
    text: typing.Union[str, bytes],
    phrases_to_exclude: typing.Sequence[str] = None
) -> str:
    """
    Remove all passed phrases from a text string

    Args:
        text: Text to clean up
        phrases_to_exclude: Phrases to remove from the text

    Returns:
        The cleaned up text
    """
    text = text.decode() if isinstance(text, bytes) else str(text)

    if not phrases_to_exclude:
        return text

    extra_space_pattern = re.compile(r"\s\s+")

    phrase_exclusion_patterns: typing.Dict[str, re.Pattern] = {}

    # Loop through excluded phrases and remove anything that isn't supposed to be there
    for phrase in phrases_to_exclude or []:
        pattern = phrase_exclusion_patterns.get(phrase.lower())

        if not pattern:
            # Create a regex pattern that will match on characters, case-insensitive
            # The pattern is case-insensitive so instances are still removed even if a prior attempt removed it
            finder_string = ""

            # Loop through each individual character to make sure different cases of alphabetical
            # characters are identified
            for character in phrase:
                # If an alphabetical character is identified, add it to the finder string in a pattern that covers
                # both the upper and lower case. "s" will be added to the finder string as "[Ss]"
                if character in string.ascii_letters:
                    finder_string += f"[{character.upper()}{character.lower()}]"
                elif character in ".+?$^*(){}[]":
                    # Escape any characters that might form a regex expression
                    finder_string += f"\\{character}"
                else:
                    # Otherwise just add the character since case is not a concern
                    finder_string += character

            # If the phrase was "Phrase + Other Phrase (Explanation for Phrase 55)*", the pattern will be
            # "[Pp][Hh][Rr][Aa][Ss][Ee] \+ [Oo][Tt][Hh][Ee][Rr] [Pp][Hh][Rr][Aa][Ss][Ee] \([Ee][Xx][Pp][Ll][Aa][Nn][Aa][Tt][Ii][Oo][Nn] [Ff][Oo][Rr] [Pp][Hh][Rr][Aa][Ss][Ee] 55\)\*"
            pattern = re.compile(finder_string)

            phrase_exclusion_patterns[phrase.lower()] = pattern

        # Remove all possible instances of the pattern
        # Loop to make sure that new instances that are created are also removed,
        # like for "My ReRemove Thismove This Text" which will first become "My Remove This Text" then "My Text"
        # if the phrase to exclude was "Remove This"
        while pattern.search(text):
            had_extra_spaces = extra_space_pattern.search(text)
            text = pattern.sub("", text)

            while not had_extra_spaces and extra_space_pattern.search(text):
                text = extra_space_pattern.sub(" ", text)

    return text


def convert_character_to_humanized_case(
    current_character: str,
    previous_character: str = None,
    next_character: str = None
) -> str:
    """
    Converts a character to the proper casing based on the previous and following letters

    Examples:
        >>> convert_character_to_humanized_case("W", "O", "o")
        " W"
        >>> convert_character_to_humanized_case("W", "N", "S")
        "W"
        >>> convert_character_to_humanized_case("H", None, "e")
        "H"
        >>> convert_character_to_humanized_case(" ", None, None)
        " "
        >>> convert_character_to_humanized_case(" ", "A", "l")
        " "
        >>> convert_character_to_humanized_case("c", " ", "1")
        "C"
        >>> convert_character_to_humanized_case("1", "d", "N")
        " 1"
        >>> convert_character_to_humanized_case("S", "a", "o")
        " S"
        >>> convert_character_to_humanized_case("i", None, "N")
        "I"

    Args:
        current_character: The character whose casing is to be converted
        previous_character: The character that came previously within a larger string
        next_character: The character that comes next within a larger string

    Returns:
        The proper casing for the current character
    """

    if previous_character is None:
        return current_character.upper()

    # If the current character is whitespace we can just add the next one as an upper case,
    # marking a new phrase in the output text
    if previous_character.isspace():
        return current_character.upper()

    # If the next character is whitespace we can just add whitespace. Special whitespace won't be considered
    if current_character.isspace():
        return " "

    # Store general information to be used in if clauses into more direct language to reduce cognitive complexity
    previous_character_is_uppercase = previous_character.isupper()
    previous_character_is_lowercase = previous_character.islower()
    previous_character_is_digit = previous_character.isdigit()
    previous_character_is_letter = previous_character_is_lowercase or previous_character_is_uppercase

    current_character_is_uppercase = current_character.isupper()
    current_character_is_lowercase = current_character.islower()
    current_character_is_digit = current_character.isdigit()
    current_character_is_letter = current_character_is_lowercase or current_character_is_uppercase

    # Store general information to be used in if clauses into more direct language to reduce cognitive complexity
    next_character_is_uppercase = next_character.isupper() if next_character else False
    next_character_is_lowercase = next_character.islower() if next_character else False
    next_character_is_whitespace = next_character.isspace() if next_character else False
    next_character_is_digit = next_character.isdigit() if next_character else False

    if previous_character_is_uppercase and current_character_is_uppercase and next_character_is_uppercase:
        # Insert the next character as-is if a pattern like "DDI" is detected, resulting in "DD",
        # which might result in "DDI" or "DD I"
        return current_character

    if not next_character and previous_character_is_uppercase and current_character_is_uppercase:
        # Insert the next character as-is if a pattern like "DD" is detected and there are no letters after the
        # next, resulting in "DD"
        return current_character

    if next_character_is_lowercase and previous_character_is_uppercase and current_character_is_uppercase:
        # Insert whitespace and the next character as is if a pattern like "ERe" is detected, resulting in "E R",
        # which will result in "E Re"
        return " " + current_character

    if next_character_is_digit and previous_character_is_uppercase and current_character_is_uppercase:
        # Insert the next character as-is if a pattern like "DB1", resulting in "DB", which will result in "DB 1"
        return current_character

    if next_character_is_whitespace and previous_character_is_uppercase and current_character_is_uppercase:
        # Insert the next character as-is if a pattern like "BB " is detected, which will maintain why might be an
        # acronym
        return current_character

    if previous_character_is_lowercase and current_character_is_uppercase:
        # Insert whitespace and the next character if a pattern like "dB" is detected, resulting in "d B"
        return " " + current_character

    if previous_character_is_letter and current_character_is_digit:
        # Insert whitespace and the next character if a pattern like "s4" or "B8" is detected,
        # resulting in "s 4" or "B 8"
        return " " + current_character

    if previous_character_is_digit and current_character_is_letter:
        # Insert whitespace and a capitalized next character if a pattern like "3s" or "8J" is detected,
        # resulting in "3 S" or "8 J"
        return " " + current_character.upper()

    # Just add a lower cased version of the next character if a new phrase isn't detected
    return current_character.lower()


def instanceof(obj: object, *object_type: type) -> bool:
    """
    Check if the given object is an instance of one of the given types. Works on most generic types

    Args:
        obj: The object to check
        *object_type: The types to check

    Returns:
        True if the object is one of the given types
    """
    if not object_type:
        return False

    try:
        return isinstance(obj, object_type)
    except:
        pass

    # TODO: Add handling for functions

    type_definitions = [TypeDefinition.from_type(otype) for otype in object_type]

    for definition in type_definitions:
        if definition.matches(value=obj):
            return True

    return False


def package_directory(directory_to_archive: pathlib.Path, output_path: typing.Union[pathlib.Path, str]) -> pathlib.Path:
    if isinstance(output_path, pathlib.Path):
        output_path = str(output_path)

    archive_format = "zip"

    archive_pattern = re.compile(r"\.(zip|tar|gz|gztar|bztar|xztar)$")
    non_zip_pattern = re.compile(r"\.(tar|gz|gztar|bztar|xztar)$")

    while archive_pattern.search(output_path) is not None:
        non_zip_extension = non_zip_pattern.search(output_path)

        if non_zip_extension is not None:
            desired_archive_type = non_zip_extension.group()
            logging.warning(
                f"A request to archive templates to a {desired_archive_type} file was given - "
                f"all template archives are saved as zip files to maintain near-universal compatibility. "
                f"The desired {desired_archive_type} archive type will not be used."
            )

        output_path = archive_pattern.sub("", output_path)

    archive_path = shutil.make_archive(
        output_path,
        format=archive_format,
        root_dir=directory_to_archive,
        base_dir="./",
        verbose=True
    )

    return pathlib.Path(archive_path)


def intersects(collection: typing.Sequence, *expected_values, condition: typing.Callable[[typing.Any], bool] = None) -> bool:
    """
    Check to see if a collection has one or more identified values

    Examples:
        >>> intersects([1, 2, 3, 4], "one", "two", 8, 2)
        True
        >>> intersects([1, 2, 3, 4], "one", "two", 8, 5)
        False
        >>> dict_to_check = {"one": 9, "two": None}
        >>> intersects(dict_to_check, "two", "three")
        True
        >>> intersects(dict_to_check, "two", "three", condition=lambda value: dict_to_check[value] is not None)
        False

    Args:
        collection: The collection to check against
        *expected_values: Values to check for existence
        condition: a conditional value to run upon the intersection to further check if the intersecting value counts

    Returns:
        True if at least one expected value is in the collection
    """
    if not expected_values:
        return False
    elif len(expected_values) == 1 and condition is None:
        return expected_values[0] in collection

    for entry in collection:
        if entry in expected_values:
            return True if condition is None else condition(entry)

    return False