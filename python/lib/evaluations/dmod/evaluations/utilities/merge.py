"""
Defines facilities for merging data structure data
"""
from __future__ import annotations

import typing
from enum import Enum

from dmod.core.common.helper_functions import is_sequence_type
from dmod.core.common.helper_functions import get_common_type
from dmod.core.common.helper_functions import is_iterable_type

from dmod.core.common.protocols import KeyedObjectProtocol
from dmod.core.common.protocols import CombinableObjectProtocol

from .action import ActionConditionBuilder
from .action import ActionConditions
from .action import Performer


class ConflictStrategy(str, Enum):
    COMBINE = "COMBINE"
    FAIL = "FAIL"
    OVERWRITE = "OVERWRITE"


class MergeConditions(ActionConditions):
    """
    Hashable Metadata about the state of two different variables
    """
    @classmethod
    def from_values(cls, first: typing.Any, second: typing.Any, *args, **kwargs) -> MergeConditions:
        types_are_the_same = type(first) == type(second)
        both_are_none = first is None and second is None
        only_one_is_none = (first is None) ^ (second is None)

        first_is_hashable = first is not None and isinstance(first, typing.Hashable)
        first_is_keyed = isinstance(first, KeyedObjectProtocol)
        first_is_combinable = isinstance(first, CombinableObjectProtocol)
        first_is_an_array = is_sequence_type(first)
        first_is_a_map = isinstance(first, typing.Mapping)
        first_is_a_set = isinstance(first, typing.Set)
        first_is_a_scalar = first is not None and not (first_is_an_array or first_is_a_map or first_is_a_set)

        second_is_hashable = second is not None and isinstance(second, typing.Hashable)
        second_is_keyed = isinstance(second, KeyedObjectProtocol)
        second_is_combinable = isinstance(second, CombinableObjectProtocol)
        second_is_an_array = is_sequence_type(second)
        second_is_a_map = isinstance(second, typing.Mapping)
        second_is_a_set = isinstance(second, typing.Set)
        second_is_a_scalar = second is not None and not (second_is_an_array or second_is_a_map or second_is_a_set)

        keys_match = first.matches(second) if first_is_keyed else False
        maps_are_compatible = first_is_a_map \
                              and second_is_a_map \
                              and map_structure_is_compatible(first, second)

        return cls(
            types_are_the_same=types_are_the_same,
            both_are_none=both_are_none,
            only_one_is_none=only_one_is_none,
            keys_match=keys_match,
            maps_are_compatible=maps_are_compatible,
            first_is_scalar=first_is_a_scalar,
            first_is_hashable=first_is_hashable,
            first_is_keyed=first_is_keyed,
            first_is_combinable=first_is_combinable,
            first_is_an_array=first_is_an_array,
            first_is_a_map=first_is_a_map,
            first_is_a_set=first_is_a_set,
            second_is_scalar=second_is_a_scalar,
            second_is_hashable=second_is_hashable,
            second_is_keyed=second_is_keyed,
            second_is_combinable=second_is_combinable,
            second_is_an_array=second_is_an_array,
            second_is_a_map=second_is_a_map,
            second_is_a_set=second_is_a_set
        )

    def __init__(
        self,
        types_are_the_same: bool = None,
        both_are_none: bool = None,
        only_one_is_none: bool = None,
        keys_match: bool = None,
        maps_are_compatible: bool = None,
        first_is_scalar: bool = None,
        first_is_hashable: bool = None,
        first_is_keyed: bool = None,
        first_is_combinable: bool = None,
        first_is_an_array: bool = None,
        first_is_a_map: bool = None,
        first_is_a_set: bool = None,
        second_is_scalar: bool = None,
        second_is_hashable: bool = None,
        second_is_keyed: bool = None,
        second_is_combinable: bool = None,
        second_is_an_array: bool = None,
        second_is_a_map: bool = None,
        second_is_a_set: bool = None
    ):
        self.types_are_the_same = types_are_the_same
        """Both values have the same type"""

        self.both_are_none = both_are_none
        """Both values are none"""

        self.only_one_is_none = only_one_is_none
        """One out of the two values is None"""

        self.keys_match = keys_match
        """Both values are keyed and have values that match"""

        self.maps_are_compatible = maps_are_compatible
        """Both values are maps whose structures and key values match"""

        self.first_is_a_scalar = first_is_scalar
        """The first value is a singular value"""

        self.first_is_hashable = first_is_hashable
        """The first value is hashable"""

        self.first_is_keyed = first_is_keyed
        """The first value is keyed"""

        self.first_is_combinable = first_is_combinable
        """The first value may be combined with another value of the same type via the + operator"""

        self.first_is_an_array = first_is_an_array
        """The first value is an indexible collection"""

        self.first_is_a_map = first_is_a_map
        """The first value is a key-value mapping"""

        self.first_is_a_set = first_is_a_set
        """The first value is a collection of unique hashable objects"""

        self.second_is_a_scalar = second_is_scalar
        """The second value is a singular value"""

        self.second_is_hashable = second_is_hashable
        """The second value is hashable"""

        self.second_is_keyed = second_is_keyed
        """The second value is keyed"""

        self.second_is_combinable = second_is_combinable
        """The second value may be combined with another object of the same type via the + operator"""

        self.second_is_an_array = second_is_an_array
        """The second value is an indexible collection"""

        self.second_is_a_map = second_is_a_map
        """The second value is a collection of key-value pairs"""

        self.second_is_a_set = second_is_a_set
        """The second value is a collection of unique, hashable objects"""

    @property
    def both_are_combinable(self) -> bool:
        """
        Both values may be combinable with the + operator
        """
        return self.first_is_combinable and self.second_is_combinable

    @property
    def both_are_keyed(self) -> bool:
        """
        Both are keyed objects
        """
        return self.first_is_keyed and self.second_is_keyed

    def __str__(self):
        description = []

        for rule_name, rule_value in self.get_condition_map().items():
            rule_name_parts = [part.lower() for part in rule_name.split("_") if bool(part)]

            if not rule_value:
                continue

            if rule_value is False:
                not_index = 0
                not_word = "not"

                if "are" in rule_name_parts:
                    not_index = rule_name_parts.index("are") + 1
                elif "is" in rule_name_parts:
                    not_index = rule_name_parts.index("is") + 1
                elif len(rule_name_parts) == 2:
                    not_index = 1
                    not_word = "don't"

                if not_index >= len(rule_name_parts):
                    rule_name_parts.append(not_word)
                else:
                    rule_name_parts.insert(not_index, not_word)

            description.append(" ".join(rule_name_parts))

        if len(description) == 0:
            return "There are no rules for this set of conditions."
        elif len(description) == 1:
            description = description[0]
        elif len(description) == 2:
            description = " and ".join(description)
        else:
            description = f"{', '.join(description[:-1])}, and {description[-1]}"

        description = description[0].upper() + description[1:]
        description = description.strip()
        description += "."
        return description


class MergeActionBuilder(ActionConditionBuilder[MergeConditions]):
    """
    Allows The sequential creation of value conditions and a style of merging to perform when the conditions are true
    """
    conditions_type = MergeConditions

    @classmethod
    def create_performer(cls) -> Merger:
        return Merger()

    @property
    def both_are_none(self) -> MergeActionBuilder:
        self.conditions.both_are_none = True
        self.conditions.only_one_is_none = False
        return self

    @property
    def only_one_is_none(self) -> MergeActionBuilder:
        self.conditions.only_one_is_none = True
        self.conditions.both_are_none = False
        return self

    @property
    def types_are_the_same(self) -> MergeActionBuilder:
        self.conditions.types_are_the_same = True
        return self

    @property
    def keys_match(self) -> MergeActionBuilder:
        self.conditions.keys_match = True
        self.conditions.first_is_keyed = True
        self.conditions.second_is_keyed = True
        return self

    @property
    def maps_are_compatible(self) -> MergeActionBuilder:
        self.conditions.maps_are_compatible = True
        self.conditions.first_is_a_map = True
        self.conditions.second_is_a_map = True
        return self

    @property
    def first_is_a_scalar(self) -> MergeActionBuilder:
        self.conditions.first_is_a_scalar = True
        self.conditions.first_is_a_set = False
        self.conditions.first_is_an_array = False
        self.conditions.first_is_a_map = False
        return self

    @property
    def first_is_hashable(self) -> MergeActionBuilder:
        self.conditions.first_is_hashable = True
        return self

    @property
    def first_is_keyed(self) -> MergeActionBuilder:
        self.conditions.first_is_keyed = True
        self.conditions.first_is_an_array = False
        self.conditions.first_is_a_set = False
        self.conditions.first_is_a_map = False
        return self

    @property
    def first_is_combinable(self) -> MergeActionBuilder:
        self.conditions.first_is_combinable = True
        self.conditions.first_is_an_array = False
        self.conditions.first_is_a_set = False
        self.conditions.first_is_a_map = False
        return self

    @property
    def first_is_an_array(self) -> MergeActionBuilder:
        self.conditions.first_is_an_array = True
        self.conditions.first_is_a_map = False
        self.conditions.first_is_combinable = False
        self.conditions.first_is_keyed = False
        return self

    @property
    def first_is_a_map(self) -> MergeActionBuilder:
        self.conditions.first_is_a_map = True
        self.conditions.first_is_a_set = False
        self.conditions.first_is_an_array = False
        self.conditions.first_is_combinable = False
        self.conditions.first_is_keyed = False
        return self

    @property
    def first_is_a_set(self) -> MergeActionBuilder:
        self.conditions.first_is_a_set = True
        self.conditions.first_is_a_map = False
        self.conditions.first_is_combinable = False
        self.conditions.first_is_keyed = False
        return self

    @property
    def second_is_a_scalar(self) -> MergeActionBuilder:
        self.conditions.second_is_a_scalar = True
        self.conditions.second_is_a_map = False
        self.conditions.second_is_a_set = False
        self.conditions.second_is_an_array = False
        return self

    @property
    def second_is_hashable(self) -> MergeActionBuilder:
        self.conditions.second_is_hashable = True
        return self

    @property
    def second_is_keyed(self) -> MergeActionBuilder:
        self.conditions.second_is_keyed = True
        self.conditions.second_is_an_array = False
        self.conditions.second_is_a_set = False
        self.conditions.second_is_a_map = False
        return self

    @property
    def second_is_combinable(self) -> MergeActionBuilder:
        self.conditions.second_is_combinable = True
        self.conditions.second_is_an_array = False
        self.conditions.second_is_a_set = False
        self.conditions.second_is_a_map = False
        return self

    @property
    def second_is_an_array(self) -> MergeActionBuilder:
        self.conditions.second_is_an_array = True
        self.conditions.second_is_combinable = False
        self.conditions.second_is_keyed = False
        self.conditions.second_is_a_map = False
        return self

    @property
    def second_is_a_map(self) -> MergeActionBuilder:
        self.conditions.second_is_a_map = True
        self.conditions.second_is_combinable = False
        self.conditions.second_is_a_set = False
        self.conditions.second_is_keyed = False
        return self

    @property
    def second_is_a_set(self) -> MergeActionBuilder:
        self.conditions.second_is_a_set = True
        self.conditions.second_is_a_map = False
        self.conditions.second_is_keyed = False
        self.conditions.second_is_combinable = False
        return self


class MergePath:
    """
    Represents the path of traversal through two data structures
    """
    def __init__(self, first: typing.Union[str, int] = None, second: typing.Union[str, int] = None):
        self.__first = str(first) if first else ""
        self.__second = str(second) if second else self.__first

    def next(self, first_step: typing.Union[str, int] = None, second_step: typing.Union[str, int] = None) -> "MergePath":
        return MergePath(
            first=f"{self.__first}/{first_step}" if first_step is not None else self.__first,
            second=f"{self.__second}/{second_step}" if second_step is not None else self.__second
        )

    @property
    def first_path(self) -> str:
        return self.__first

    @property
    def second_path(self) -> str:
        return self.__second

    def values_are_incompatible(self):
        """
        Raise an exception detailing that both values are not compatible
        """
        raise ValueError(
            f"Data cannot be merged - the values at {self.first_path} aren't "
            f"compatible with the values at {self.second_path}"
        )

    def __str__(self):
        return ", ".join([self.__first, self.__second])

    def __repr__(self):
        return self.__str__()


def maps_conflict(first: typing.Mapping, second: typing.Mapping) -> bool:
    """
    Checks to see if the values within both maps have keys that overlap and values that conflict
    """
    primary_map = second if len(second.keys()) > len(first.keys()) else first
    secondary_map = second if primary_map is first else first

    for primary_key, primary_value in primary_map.items():
        if primary_key not in secondary_map.keys():
            continue

        secondary_value = secondary_map[primary_key]

        if not isinstance(secondary_value, type(primary_value)):
            return True

        both_are_maps = isinstance(primary_value, typing.Mapping) and isinstance(secondary_value, typing.Mapping)

        if both_are_maps:
            if maps_conflict(primary_value, secondary_value):
                return True
        elif not (primary_value == secondary_value or is_iterable_type(primary_value)):
            return True

    return False


def map_structure_is_compatible(first: typing.Mapping, second: typing.Mapping) -> bool:
    """
    Checks to see whether both maps have the same initial keys and primitive value types

    This is not fully recursive - it just checks whether each map describes a shared set of partial data

    This returns true if:
        - There is at least 1 common key
        - Both have at least 50% of their keys in common with the other
        - value types for all common keys are the same
        - Scalar values for all common keys are the same
        - Nested dictionaries don't conflict
        - If the value for both keys is a container, both have the same uniform data type if there is one

    Example:
        >>> first_map = {"a": 1, "b": 2, "c": [1, 2, 3], "d": {"e": 323, "f": 32423}}
        >>> second_map = {"a": 1, "b": 2, "c": [4, 5, 6], "d": {"g": 3242, "h": 23423}}
        >>> third_map = {"a": 1, "b": '2', "c": 'five', "d": {"e": 323, "f": 32423}}
        >>> fourth_map = {"a": 1, "b": 2, "c": [1, 2, 3], "d": {"e": 13235, "f": 32423}}
        >>> fifth_map = {"a": 1, "d": {"e": 13235, "f": 32423}}
        >>> sixth_map = {"a": 1, "b": 2, "c": [1, 2, 3], "q": "nine"}
        >>> map_structure_is_compatible(first_map, second_map)
        True
        >>> map_structure_is_compatible(first_map, third_map)
        False
        >>> map_structure_is_compatible(first_map, fourth_map)
        False
        >>> map_structure_is_compatible(fourth_map, fifth_map)
        False
        >>> map_structure_is_compatible(first_map, sixth_map)
        True

    Args:
        first: The first map to check
        second: The second map to check

    Returns:
        Whether the structure in both are considered equivalent
    """
    if not (isinstance(first, typing.Mapping) and isinstance(second, typing.Mapping)):
        return False

    if len(first) == 0 or len(second) == 0:
        return False

    common_keys = {key for key in first.keys()}.intersection({key for key in second.keys()})

    if len(common_keys) == 0:
        return False

    if len(common_keys) / len(first) < 0.5 or len(common_keys) / len(second) < 0.5:
        # Return false if one shares at most 50% of its total keys - that leaves too much room for variability
        return False

    for key in common_keys:
        first_value = first[key]
        second_value = second[key]

        if not (isinstance(first_value, type(second_value)) or isinstance(second_value, type(first_value))):
            return False

        both_are_containers = is_iterable_type(first_value) and is_iterable_type(second_value)
        both_are_maps = isinstance(first_value, typing.Mapping) and isinstance(second_value, typing.Mapping)

        if both_are_containers:
            first_common_type = get_common_type(first_value)
            second_common_type = get_common_type(second_value)

            # The first collection may have a 'common' type, but only having one entry doesn't mean it's
            # necessarily strongly typed. Having a list with a single string in it doesn't mean that it may only
            # ever hold strings
            first_has_reliable_type = first_common_type is not None and len(first_value) > 1

            # Same as above
            second_has_reliable_type = second_common_type is not None and len(second_value) > 1

            # If they are the same type - say a list of strings, we can consider them equivalent and move on
            if first_common_type == second_common_type:
                continue
            elif len(first_value) == 0 or len(second_value) == 0:
                # If one of them doesn't have any data, we can consider them reasonable enough - there's nothing
                # saying that the empty list doesn't comply
                continue
            elif first_common_type is None and not second_has_reliable_type:
                # If the first doesn't have a common type and the type for the second isn't reliable
                # (i.e. can't trust that its 'common' type is a constraint), we can consider this equivalent
                continue
            elif second_common_type is None and not first_has_reliable_type:
                # Same as above
                continue

            return False
        elif both_are_maps:
            if maps_conflict(first_value, second_value):
                return False
        elif first_value != second_value:
            return False

    return True


def nothing(
    merger: Merger,
    conditions: MergeConditions,
    first: typing.Any,
    second: typing.Any,
    strategy: ConflictStrategy,
    path: MergePath = None
):
    return None


def return_the_non_null(
    merger: Merger,
    conditions: MergeConditions,
    first: typing.Any,
    second: typing.Any,
    strategy: ConflictStrategy,
    path: MergePath = None
) -> typing.Any:
    return first if second is None else second


def return_the_combined_values(
    merger: Merger,
    _,
    first: CombinableObjectProtocol,
    second: CombinableObjectProtocol,
    conflict: ConflictStrategy,
    path: MergePath
) -> CombinableObjectProtocol:
    return first + second


def combine_sets(
    merger: Merger,
    _,
    first: typing.Set,
    second: typing.Set,
    strategy: ConflictStrategy,
    path,
    *args,
    **kwargs
) -> typing.Set:
    first_is_longest = len(second) < len(first)

    short_list = [value for value in second] if first_is_longest else [value for value in first]
    long_list = [value for value in first] if first_is_longest else [value for value in second]

    for short_index, short_value in enumerate(short_list):
        value_added = False
        short_value_is_keyed = isinstance(short_value, KeyedObjectProtocol)
        short_value_is_combinable = isinstance(short_value, CombinableObjectProtocol)

        for long_index, long_value in enumerate(long_list):
            if short_value == long_value:
                value_added = True
                break

            keys_match = short_value.matches(long_value) if short_value_is_keyed else False
            both_are_combinable = short_value_is_combinable and isinstance(long_value, CombinableObjectProtocol)

            first_value = long_value if first_is_longest else short_value
            second_value = short_value if first_is_longest else long_value

            first_index = long_index if first_is_longest else short_index
            second_index = short_index if first_is_longest else long_index

            if map_structure_is_compatible(short_value, long_value):
                long_list[long_index] = merger.merge(
                    first_value,
                    second_value,
                    path.next(
                        first_index,
                        second_index
                    )
                )
                value_added = True
                break
            elif keys_match and both_are_combinable:
                long_list[long_index] = first_value + second_value
                value_added = True
                break
            elif keys_match:
                long_list[long_index] = second_value
                value_added = True
                break

        if not value_added:
            long_list.append(short_value)

    return set(long_list)


def merge_maps(
    performer: Merger,
    conditions: MergeConditions,
    first: typing.Mapping,
    second: typing.Mapping,
    strategy: ConflictStrategy,
    path: MergePath,
    *args,
    **kwargs
) -> typing.Mapping:
    merged_data = dict()

    second_data = {key: value for key, value in second.items()}

    for key, value in first.items():
        if key in second_data:
            inner_data = performer.merge(
                value,
                second_data[key],
                strategy,
                path.next(key, key)
            )
            del second_data[key]
        else:
            inner_data = value

        merged_data[key] = inner_data

    for key, value in second_data.items():
        merged_data[key] = value

    return merged_data


def combine_when_first_is_a_set_second_is_hashable(
    performer: Merger,
    conditions: MergeConditions,
    first: typing.Set,
    second: typing.Union[typing.Hashable, KeyedObjectProtocol, CombinableObjectProtocol],
    strategy: ConflictStrategy,
    path: MergePath,
    *args,
    **kwargs
) -> typing.Union[typing.Set, typing.Hashable]:
    if strategy == ConflictStrategy.OVERWRITE:
        return second

    updated_values = [value for value in first]

    value_added = False

    for index, value_from_first in enumerate(updated_values):
        if conditions.second_is_keyed and second.matches(value_from_first):
            if conditions.second_is_combinable and isinstance(value_from_first, CombinableObjectProtocol):
                updated_values[index] = value_from_first + second
            else:
                updated_values[index] = second
            value_added = True
            break
        elif second == value_from_first:
            value_added = True
            break

    if not value_added and strategy == ConflictStrategy.FAIL:
        path.values_are_incompatible()
    elif not value_added:
        updated_values.append(second)

    return set(updated_values)


def combine_when_first_is_hashable_second_is_a_set(
    performer: Merger,
    conditions: MergeConditions,
    first: typing.Union[typing.Hashable, KeyedObjectProtocol, CombinableObjectProtocol],
    second: typing.Set,
    strategy: ConflictStrategy,
    path: MergePath,
    *args,
    **kwargs
) -> typing.Union[typing.Set, typing.Hashable]:
    if strategy == ConflictStrategy.OVERWRITE:
        return second

    value_found = False

    updated_values = [value for value in second]

    for index, second_value in enumerate(updated_values):
        if first == second_value:
            value_found = True
            break

        if conditions.first_is_keyed:
            keys_match = first.matches(second_value)
            both_can_be_combined = conditions.first_is_combinable and isinstance(second_value, CombinableObjectProtocol)

            if keys_match and both_can_be_combined:
                updated_values[index] = first + second_value
                value_found = True
                break

    if strategy == ConflictStrategy.FAIL and not value_found:
        path.values_are_incompatible()
    elif not value_found:
        updated_values.insert(0, first)

    return set(updated_values)


def combine_two_arrays(
    performer: Merger,
    conditions: MergeConditions,
    first: typing.Iterable[typing.Union[KeyedObjectProtocol, CombinableObjectProtocol, typing.Mapping, typing.Any]],
    second: typing.Iterable[typing.Union[KeyedObjectProtocol, CombinableObjectProtocol, typing.Mapping, typing.Any]],
    strategy: ConflictStrategy,
    path: MergePath,
    *args,
    **kwargs
) -> typing.Iterable[KeyedObjectProtocol, CombinableObjectProtocol, typing.Any]:
    if first == second:
        return second

    return_data = [value for value in first]
    second_data = [value for value in second]

    if len(return_data) == 0:
        return second
    elif len(second_data) == 0 and len(return_data) > 0:
        return return_data

    first_common_type = get_common_type(return_data)
    second_common_type = get_common_type(second_data)

    # If both iterables are a series of strings, there's a chance that ordering is extremely important.
    # If so, maintain it by just replacing it if this isn't supposed to outright combine as much as possible
    conserve_order = first_common_type == str and first_common_type == second_common_type

    if conserve_order and not strategy == ConflictStrategy.COMBINE:
        return second

    for second_index, second_value in enumerate(second_data):
        second_value_key = second_value.get_key_values() if isinstance(second_value, KeyedObjectProtocol) else None
        second_value_is_map = isinstance(second_value, typing.Mapping)
        second_value_is_combinable = isinstance(second_value, CombinableObjectProtocol)

        if second_value_key or second_value_is_map:
            overridden = False
            for first_index, first_value in enumerate(return_data):
                if isinstance(first_value, KeyedObjectProtocol):
                    first_value_key = first_value.get_key_values()
                else:
                    first_value_key = None

                first_value_is_map = isinstance(first_value, typing.Mapping)
                first_value_is_combinable = isinstance(first_value, CombinableObjectProtocol)

                both_are_combinable = first_value_is_combinable and second_value_is_combinable
                structure_is_equivalent = map_structure_is_compatible(first_value, second_value)
                maps_are_not_in_conflict = structure_is_equivalent and not maps_conflict(first_value, second_value)

                if first_value_key and first_value_key == second_value_key and both_are_combinable:
                    return_data[first_index] = first_value + second_value
                    overridden = True
                    break
                elif first_value_key is not None and first_value_key == second_value_key:
                    return_data[first_index] = second_value
                    overridden = True
                    break
                elif maps_are_not_in_conflict:
                    return_data[first_index] = performer.merge(
                        first_value,
                        second_value,
                        strategy,
                        path.next(first_index, second_index)
                    )
                    overridden = True
                    break

            if not overridden:
                return_data.append(second_value)
        else:
            return_data.append(second_value)

    return return_data


def combine_array_and_keyed_object(
    merger: Merger,
    conditions: MergeConditions,
    first: typing.Iterable[typing.Union[KeyedObjectProtocol, CombinableObjectProtocol, typing.Mapping, typing.Any]],
    second: typing.Union[KeyedObjectProtocol, CombinableObjectProtocol],
    strategy: ConflictStrategy,
    path: MergePath,
    *args,
    **kwargs
) -> typing.Union[typing.Iterable, KeyedObjectProtocol]:
    if strategy == ConflictStrategy.OVERWRITE:
        return second
    elif strategy == ConflictStrategy.FAIL:
        path.values_are_incompatible()

    matched_value = False
    return_data: typing.List[typing.Any] = [value for value in first]

    for first_index, first_value in enumerate(return_data):
        matched_value = second.matches(first_value)

        if not matched_value:
            continue

        if isinstance(first_value, CombinableObjectProtocol) and isinstance(second, CombinableObjectProtocol):
            return_data[first_index] = first_value + second
        elif matched_value:
            return_data[first_index] = second

        if matched_value:
            break

    if not matched_value:
        return_data.append(second)

    return return_data


def combine_array_and_non_array(
    performer: Merger,
    conditions: MergeConditions,
    first: typing.Iterable[typing.Union[typing.Mapping, KeyedObjectProtocol, CombinableObjectProtocol, typing.Any]],
    second: typing.Any,
    strategy: ConflictStrategy,
    path: MergePath
) -> typing.Any:
    if strategy == ConflictStrategy.FAIL:
        path.values_are_incompatible()
    elif strategy == ConflictStrategy.OVERWRITE:
        return second

    combined_value = [value for value in first]
    value_was_added = False

    if conditions.second_is_keyed or conditions.second_is_a_map:
        for index, first_value in enumerate(combined_value):
            first_value_is_combinable = isinstance(first_value, CombinableObjectProtocol)
            both_are_combinable = first_value_is_combinable and conditions.second_is_combinable

            first_value_matches = conditions.second_is_keyed and second.matches(first_value)

            if first_value_matches and both_are_combinable:
                combined_value[index] = first_value + second
                value_was_added = True
            elif first_value_matches:
                combined_value[index] = second
                value_was_added = True
            elif map_structure_is_compatible(first_value, second):
                combined_value[index] = performer.merge(
                    first_value,
                    second,
                    strategy=strategy,
                    path=path.next(index)
                )
                value_was_added = True

            if value_was_added:
                break

    if not value_was_added:
        combined_value.append(second)

    return combined_value


def combine_non_array_and_array(
    performer: Merger,
    conditions: MergeConditions,
    first: typing.Union[KeyedObjectProtocol, CombinableObjectProtocol, typing.Any],
    second: typing.Iterable[typing.Union[typing.Mapping, KeyedObjectProtocol, CombinableObjectProtocol, typing.Any]],
    strategy: ConflictStrategy,
    path: MergePath
) -> typing.Iterable[typing.Mapping, KeyedObjectProtocol, CombinableObjectProtocol, typing.Any]:
    """
    Combines an object that is not a series of values with an object that represents a series of values
    """

    # Start with a list of the second values since that will be the basis for what is returned
    return_values: typing.List[typing.Any] = [value for value in second]

    found = False
    is_keyed = isinstance(first, KeyedObjectProtocol)

    # Search for the 'first' value in the 'second' collection - if it is found the combination job is already done
    for index, second_value in enumerate(second):
        # The value is considered found if its key matches a key on the second if they are both keyed or if
        # they are considered to be the same
        found = first.matches(second_value) if is_keyed else first == second_value

        # The values may not be the same, but they might be compatible dictionaries. Check and merge them if that is
        # the case
        if not found and map_structure_is_compatible(first, second_value):
            found = True
            return_values[index] = performer.merge(
                first,
                second_value,
                strategy=strategy,
                path=path.next(second_step=index)
            )

        # If this is the matching value and the two are combinable, add them together.
        # Otherwise the combination is considered complete.
        if found and isinstance(first, CombinableObjectProtocol) and isinstance(second_value, CombinableObjectProtocol):
            return_values[index] = first + second_value

        if found:
            break

    # If the combination process is set to fail if a data type must change to accommodate new data, fail
    if strategy == ConflictStrategy.FAIL and not found:
        path.values_are_incompatible()

    # If the combination process is set to add data if a data type must change to accomomodate new data,
    # insert the first object's value at the beginning of the list like it always belonged there.
    if strategy == ConflictStrategy.COMBINE and not found:
        return_values.insert(0, first)

    return return_values


def combine_scalars(
    performer: Merger,
    conditions: MergeConditions,
    first: typing.Any,
    second: typing.Any,
    strategy: ConflictStrategy,
    path: MergePath
) -> typing.Union[typing.Set, typing.Any]:
    """
    Combine two single valued objects

    If the objects comply with the CombinableObjectProtocol, the returned value will be the result of first + second

    If the strategy is to combine values and first and second are not equal, the result will be the set of the first
    and second values

    Otherwise, the result will be the second value
    """
    if isinstance(first, CombinableObjectProtocol) and isinstance(second, CombinableObjectProtocol):
        return first + second

    if first != second and strategy == ConflictStrategy.COMBINE:
        return [first, second]

    if not conditions.types_are_the_same and strategy == ConflictStrategy.FAIL:
        path.values_are_incompatible()

    return second


class Merger(Performer[MergeActionBuilder]):
    """
    A performer whose purpose is to combine two objects
    """
    builder_type: typing.Type[MergeActionBuilder] = MergeActionBuilder

    def __init__(self, strategy: ConflictStrategy = None):
        super().__init__()
        self.__strategy = strategy or ConflictStrategy.FAIL

    @property
    def strategy(self) -> ConflictStrategy:
        """
        How the merger should react to conflicting data types
        """
        return self.__strategy

    def merge(self, first: typing.Any, second: typing.Any, strategy: ConflictStrategy = None, path: MergePath = None):
        """
        Combine two objects

        Args:
            first: The base object that will accept changes
            second: The object whose values will be laid over the first
            strategy: An optional strategy used to override the base strategy of the merger
            path: Where in the data structure for the first and second data that the data originate

        Returns:
            A structure representing the combination of both input values
        """
        if path is None:
            path = MergePath()

        if strategy is None:
            strategy = self.__strategy

        return self.perform(first=first, second=second, strategy=strategy, path=path)


MERGE_ACTION = typing.Callable[
    [Merger, MergeConditions, typing.Any, typing.Any, ConflictStrategy, typing.Optional[MergePath]],
    typing.Any
]
"""
An action used two merge two values based on metadata about both variables, how to react to conflicts,
and an optional path to the data in the data being merged
"""


def create_dictionary_merger(strategy: ConflictStrategy = None) -> Merger:
    merger = Merger(strategy=strategy)

    merger.when.both_are_none.then(nothing)
    merger.when.only_one_is_none.then(return_the_non_null)
    merger.when.types_are_the_same.first_is_combinable.second_is_combinable.then(return_the_combined_values)
    merger.when.first_is_a_set.second_is_a_set.then(combine_sets)
    merger.when.first_is_a_map.second_is_a_map.then(merge_maps)
    merger.when.first_is_a_set.second_is_a_scalar.second_is_hashable.then(combine_when_first_is_a_set_second_is_hashable)
    merger.when.first_is_a_scalar.first_is_hashable.second_is_a_set.then(combine_when_first_is_hashable_second_is_a_set)
    merger.when.first_is_an_array.second_is_an_array.then(combine_two_arrays)
    merger.when.first_is_an_array.second_is_a_scalar.second_is_keyed.then(combine_array_and_keyed_object)
    merger.when.first_is_an_array.second_is_a_scalar.then(combine_array_and_non_array)
    merger.when.first_is_a_scalar.second_is_an_array.then(combine_non_array_and_array)
    merger.when.first_is_a_scalar.second_is_a_scalar.then(combine_scalars)
    merger.when.first_is_a_scalar.second_is_a_map.then(combine_scalars)
    merger.when.first_is_a_map.second_is_a_scalar.then(combine_scalars)

    return merger


DictionaryMerger = create_dictionary_merger()
"""
Instance of a Merger specifically built to merge complex dictionaries.
Merging will fail if the dictionary schema will need to change to accommodate new values.
"""

merge_dictionaries = DictionaryMerger.merge
"""
The merge function from the shared dictionary merger
Merging will fail if the dictionary schema will need to change to accommodate new values.
"""