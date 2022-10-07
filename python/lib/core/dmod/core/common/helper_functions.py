"""
Provides simple helper functions
"""
import typing
import inspect


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