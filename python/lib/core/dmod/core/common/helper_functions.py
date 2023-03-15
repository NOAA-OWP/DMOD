"""
Provides simple helper functions
"""
import typing
import inspect
import math
import json
import numbers
import random
import string

from collections import OrderedDict


_CLASS_TYPE = typing.TypeVar('_CLASS_TYPE')
"""A type that points directly to a class. The _CLASS_TYPE of `6`, for example, is `<class 'int'>`"""


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


def merge_dictionaries(first: typing.Mapping = None, second: typing.Mapping = None) -> typing.Mapping:
    """
    Combines two dictionaries in a way that values aren't overridden

    Examples:
        >>> first_map = None
        >>> second_map = None
        >>> merge_dictionaries(first_map, second_map)
        >>> None
        >>> first_map = {"one": 1, "two": 2}
        >>> merge_dictionaries(first_map, second_map)
        {"one": 1, "two": 2}
        >>> second_map = {"two": 3, "three": 3}
        >>> merge_dictionaries(first_map, second_map)
        {"one": 1, "two": [2, 3], "three": 3}
        >>> first_map = {"one": 1, "two": 2, "three": {3, 5, 6}}
        >>> merge_dictionaries(first_map, second_map)
        {"one": 1, "two": [2, 3], "three": {3, 5, 6}}
        >>> second_map = {"one": {"a": "a", "b": "b"}, "two": 3, "three": 3}
        >>> merge_dictionaries(first_map, second_map)
        {"one": [1, {"a": "a", "b": "b"}], "two": [2, 3], "three": {3, 5, 6}}
        >>> first_map = {"one": {"a": 1, "c": "c"}, "two": 2}
        >>> merge_dictionaries(first_map, second_map)
        {"one": {"a": ["a", 1], "b": "b", "c": "c"}, "two": [2, 3], "three": {3, 5, 6}}

    Args:
        first: The first dictionary
        second: The second dictionary

    Returns:
        The two dictionaries combined
    """
    merged_dictionary = dict()

    # Return nothing if nothing was given to merge
    if first is None and second is None:
        return merged_dictionary
    elif first is None:
        # Return the second dictionary if the first was none (meaning there's nothing to merge)
        return second
    elif second is None:
        # Return the first dictionary if the second was none (meaning there's nothing to merge)
        return first

    # Iterate through all keys and values of the first dictionary to merge on all of its values
    for key_for_first, value_for_first in first.items():
        # If this key isn't in the second dictionary, we're in luck - it doesn't have to be merged and can be directly
        # inserted
        if key_for_first not in second:
            merged_dictionary[key_for_first] = value_for_first
        else:
            # Get the matching value from the second mapping
            value_for_second = second[key_for_first]

            # Determine if the first value is hashable - this is important if collections that require a hash are used
            first_is_hashable = isinstance(value_for_first, typing.Hashable)

            # Determine if the second value is hashable - this is important if collections that require a hash are used
            second_is_hashable = isinstance(value_for_second, typing.Hashable)

            # Nothing has to be merged if both values are deemed null
            if value_for_first is None and value_for_second is None:
                combined_value = None
            elif value_for_first is not None and value_for_second is None:
                # No merging is needed if the first has a value where the second is null
                combined_value = value_for_first
            elif value_for_second is not None and value_for_first is None:
                # No merging is needed if the second has a value where the first is null
                combined_value = value_for_second
            elif isinstance(value_for_first, set) and isinstance(value_for_second, set):
                # We want to combine the values via a union if they are both sets
                combined_value = value_for_first.union(value_for_second)
            elif isinstance(value_for_first, set) and second_is_hashable:
                # If the first value is a set and the second is hashable, we want to add the second value to the set
                # A copy is used just to make sure that the original is not modified
                combined_value = value_for_first.copy()
                combined_value.add(value_for_second)
            elif first_is_hashable and isinstance(value_for_second, set):
                # If the second value is a set and the first is hashable, we want to add the first value to the set
                # A copy is used just to make sure that the original is not modified
                combined_value = value_for_second.copy()
                combined_value.add(value_for_first)
            elif is_sequence_type(value_for_first) and is_sequence_type(value_for_second):
                # If both are sequences of different values (so not bytes or strings), we want to combine the two
                # into a new collection. A new collection is used to ensure that the originals don't get modified
                combined_value = [value for value in value_for_first] + [value for value in value_for_second]
            elif is_sequence_type(value_for_first):
                # If only the first value is a sequence, we want to add the second value to a copy so we end up with
                # a new sequence whose modification does not modify the original
                combined_value = [value for value in value_for_first]
                combined_value.append(value_for_second)
            elif is_sequence_type(value_for_second):
                # If only the second value is a sequence, we want to add the first value to a copy so we end up with
                # a new sequence whose modification does not modify the original
                combined_value = [value for value in value_for_second]
                combined_value.append(value_for_first)
            elif isinstance(value_for_first, typing.Mapping) and isinstance(value_for_second, typing.Mapping):
                # If both are maps, we want the resulting merge
                combined_value = merge_dictionaries(value_for_first, value_for_second)
            else:
                # Combine both values in a list if they can't both occupy the same key
                combined_value = [value_for_first, value_for_second]

            # Set the new value in the dictionary that will be returned
            merged_dictionary[key_for_first] = combined_value

    # Now just update the merged dictionary with the values from the second dictionary that weren't added.
    # Everything from the first and everything that overlapped will already be there
    merged_dictionary.update({
        key_for_second: value_for_second
        for key_for_second, value_for_second in second.keys()
        if key_for_second not in merged_dictionary
    })

    return merged_dictionary


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


def get_subclasses(base: typing.Type[_CLASS_TYPE]) -> typing.List[typing.Type[_CLASS_TYPE]]:
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
    func: typing.Callable[[_CLASS_TYPE], typing.Any],
    collection: typing.Iterable[_CLASS_TYPE]
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
    primitive_keys: typing.List[str] = list()
    array_keys: typing.List[str] = list()
    mapping_keys: typing.List[str] = list()
    object_keys: typing.List[str] = list()
    non_mro_keys: typing.List[str] = list()

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


def truncate_numbers_in_dictionary(dictionary: dict, places: int, copy: bool = False) -> typing.Mapping:
    if places is None or places <= 0:
        return dictionary

    dictionary = dictionary.copy() if copy else dictionary

    for key, value in dictionary.items():
        if isinstance(value, numbers.Number) and "." in str(key):
            dictionary[key] = truncate(value, places)
        elif isinstance(value, dict):
            dictionary[key] = truncate_numbers_in_dictionary(value, places, copy)

    return dictionary


def to_json(obj, encoder: json.JSONEncoder = None, indent: int = 4, truncate_digits: int = None) -> str:
    if indent is None or indent <= 0:
        indent = 4

    first_layer: str = json.dumps(obj, cls=encoder, indent=indent)

    dictionary_representation = json.loads(first_layer)
    dictionary_representation = truncate_numbers_in_dictionary(dictionary_representation, truncate_digits)

    ordered_dictionary = order_dictionary(dictionary_representation)

    second_layer: str = json.dumps(ordered_dictionary, cls=encoder, indent=indent)

    return second_layer