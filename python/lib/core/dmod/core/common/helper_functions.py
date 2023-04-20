"""
Provides simple helper functions
"""
import typing
import inspect
import math
import json
import numbers
import re
import collections.abc as abstract_collections
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


def contents_are_equivalent(first, second):
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
        first: The first object to compare
        second: The second object to compare

    Returns:
        Whether first and second are equivalent objects
    """
    if first is None and second is None:
        return True

    if (first is None) ^ (second is None):
        return False

    # You can't check length if one isn't sized, so default to standard equivalence
    if not isinstance(first, typing.Sized) or not isinstance(second, typing.Sized):
        return first == second

    # They aren't equal if they have different sizes
    if len(first) != len(second):
        return False

    # Proper mapping equivalence can't be performed if one is a map and the other isn't. Fall back to standard
    # equivalence if only one is a map
    if isinstance(first, typing.Mapping) ^ isinstance(second, typing.Mapping):
        return first == second

    # If they aren't iterable, go ahead and perform a standard equivalence
    if not isinstance(first, typing.Iterable) or not isinstance(second, typing.Iterable):
        return first == second

    # If the first element is a set of bytes, normalize the values by decoding
    if isinstance(first, bytes):
        first = first.decode()

    # If the second element is a set of bytes, normalize the values by decoding
    if isinstance(second, bytes):
        second = second.decode()

    # If one is a string, perform a standard equivalence
    if isinstance(first, str) or isinstance(second, str):
        return first == second
    elif isinstance(first, typing.Mapping) and isinstance(second, typing.Mapping):
        for key_in_first, value_in_first in first.items():
            if key_in_first not in second.keys():
                return False
            elif value_in_first != second[key_in_first]:
                return False
        return True
    elif isinstance(first, typing.Sequence) and isinstance(second, typing.Sequence):
        for element_index in range(len(first)):
            if first[element_index] != second[element_index]:
                return False
        return True

    # Create a copy of the second collection so that matched values may be removed
    second_copy = [element for element in second]

    # Loop through the first collection and remove anything in the second that matches.
    # Fail if a value couldn't be removed
    for element_in_first in first:
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
    first_copy = [element for element in first]

    for element_in_second in second:
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


def find(
    iterable: typing.Iterable[_CLASS_TYPE],
    predicate: typing.Callable[[_CLASS_TYPE], bool],
    default: _CLASS_TYPE = None
) -> typing.Optional[_CLASS_TYPE]:
    """
    Find the first value in an iterable that complies with the give predicate

    The pythonic approach to this is:

        >>> next(filter(lambda val: val == 999, range(1000000)), None)

    This results in lower cognitive overload and better performance

    Args:
        iterable: The collection to search
        predicate: A check to see if the encountered value matches the desired value
        default: The default value to return if the item is not found

    Returns:
        The first value matching the value, a default value (None) otherwise
    """
    if not iterable:
        return None
    
    return next(filter(predicate, iterable), default)


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
        exclude_phrases = list()
    elif isinstance(exclude_phrases, bytes):
        exclude_phrases = exclude_phrases.decode()

    if isinstance(exclude_phrases, str):
        exclude_phrases = [exclude_phrases]

    if isinstance(text, bytes):
        text = text.decode()

    # Since '_' is often a replacement for whitespace separators, convert '_' to ' ' to offer a consistent look
    text = text.replace("_", " ")

    text = text.strip()

    phrase_exclusion_patterns: typing.Dict[str, re.Pattern] = dict()

    # Loop through excluded phrases and remove anything that isn't supposed to be there
    for phrase in exclude_phrases or list():
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
            text = pattern.sub("", text)

    text = re.sub("  +", " ", text)

    text = text.strip()

    # Start out by putting the capitalized first character into the container for the string
    humanized_text: str = text[0].upper()

    # Loop through all but the last letter index to find what character to add next.
    # The range is to len(text) - 1 because index + 1 will be one of the most important values
    for letter_index in range(len(text) - 1):
        # Assign the current and next characters to make referencing cleared
        current_character = text[letter_index]
        next_character = text[letter_index + 1]
        further_character = text[letter_index + 2] if letter_index + 2 < len(text) else None

        # If the current character is whitespace we can just add the next one as an upper case,
        # marking a new phrase in the output text
        if current_character.isspace():
            humanized_text += next_character.upper()
            continue

        # If the next character is whitespace we can just add whitespace. Special whitespace won't be considered
        if next_character.isspace():
            humanized_text += " "
            continue

        # Store general information to be used in if clauses into more direct language to reduce cognitive complexity
        current_character_is_uppercase = current_character.isupper()
        current_character_is_lowercase = current_character.islower()
        current_character_is_digit = current_character.isdigit()
        current_character_is_letter = current_character_is_lowercase or current_character_is_uppercase

        next_character_is_uppercase = next_character.isupper()
        next_character_is_lowercase = next_character.islower()
        next_character_is_digit = next_character.isdigit()
        next_character_is_letter = next_character_is_lowercase or next_character_is_uppercase

        # Store general information to be used in if clauses into more direct language to reduce cognitive complexity
        further_character_is_uppercase = further_character.isupper() if further_character else False
        further_character_is_lowercase = further_character.islower() if further_character else False
        further_character_is_whitespace = further_character.isspace() if further_character else False
        further_character_is_digit = further_character.isdigit() if further_character else False

        if current_character_is_uppercase and next_character_is_uppercase and further_character_is_uppercase:
            # Insert the next character as-is if a pattern like "DDI" is detected, resulting in "DD",
            # which might result in "DDI" or "DD I"
            humanized_text += next_character
        elif not further_character and current_character_is_uppercase and next_character_is_uppercase:
            # Insert the next character as-is if a pattern like "DD" is detected and there are no letters after the
            # next, resulting in "DD"
            humanized_text += next_character
        elif further_character_is_lowercase and current_character_is_uppercase and next_character_is_uppercase:
            # Insert whitespace and the next character as is if a pattern like "ERe" is detected, resulting in "E R",
            # which will result in "E Re"
            humanized_text += " "
            humanized_text += next_character
        elif further_character_is_digit and current_character_is_uppercase and next_character_is_uppercase:
            # Insert the next character as-is if a pattern like "DB1", resulting in "DB", which will result in "DB 1"
            humanized_text += next_character
        elif further_character_is_whitespace and current_character_is_uppercase and next_character_is_uppercase:
            # Insert the next character as-is if a pattern like "BB " is detected, which will maintain why might be an
            # acronym
            humanized_text += next_character
        elif current_character_is_lowercase and next_character_is_uppercase:
            # Insert whitespace and the next character if a pattern like "dB" is detected, resulting in "d B"
            humanized_text += " "
            humanized_text += next_character
        elif current_character_is_letter and next_character_is_digit:
            # Insert whitespace and the next character if a pattern like "s4" or "B8" is detected,
            # resulting in "s 4" or "B 8"
            humanized_text += " "
            humanized_text += next_character
        elif current_character_is_digit and next_character_is_letter:
            # Insert whitespace and a capitalized next character if a pattern like "3s" or "8J" is detected,
            # resulting in "3 S" or "8 J"
            humanized_text += " "
            humanized_text += next_character.upper()
        else:
            # Just add a lower cased version of the next character if a new phrase isn't detected
            humanized_text += next_character.lower()

    # Loop through excluded phrases again and remove anything that isn't supposed to be there that might have
    # been inserted through the text manipulation process. If a phrase to exclude was "Remove This" and the original
    # text was "My removeThis Text", the humanization process will result in "My Remove This Text",
    # which should be "My Text"
    for phrase in exclude_phrases or list():
        # New patterns don't have to be formed since they would have been formed above
        pattern = phrase_exclusion_patterns.get(phrase.lower())

        # Remove all possible instances of the pattern
        # Loop to make sure that new instances that are created are also removed,
        # like for "My ReRemove Thismove This Text" which will first become "My Remove This Text" then "My  Text"
        # if the phrase to exclude was "Remove This"
        while pattern.search(humanized_text):
            humanized_text = pattern.sub("", humanized_text)

    # Remove any possible double spaces that were added as a result of string manipulation.
    # If fixing "My removeThis Text" yielded "My Remove This Text", then yielded "My  Text",
    # this replacement will result in "My Text"
    humanized_text = re.sub("  +", " ", humanized_text)
    humanized_text = humanized_text.strip()

    return humanized_text