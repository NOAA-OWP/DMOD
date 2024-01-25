"""
Tools to help define and interpret value types
"""
from __future__ import annotations

import abc
import typing
from collections import defaultdict

from typing_extensions import Self

from ..enum import PydanticEnum

_T = typing.TypeVar("_T")


TEXT_VALUE_TUPLES = typing.List[
    typing.Union[
        typing.Tuple[_T, str],
        typing.Tuple[str, typing.Tuple[typing.Tuple[_T, str], ...]]
    ]
]
"""
Organized text-value pairs that can be used to build select boxes. Can be formatted as:

[
    ('Audio', (
            ('vinyl', 'Vinyl'),
            ('cd', 'CD'),
        )
    ),
    ('Video', (
            ('vhs', 'VHS Tape'),
            ('dvd', 'DVD'),
        )
    ),
    ('unknown', 'Unknown'),
]
"""

TEXT_VALUE_DICT = typing.Dict[typing.Literal["value", "text"], typing.Union[str, _T, None]]
TEXT_VALUE_DICT_LIST = typing.List[TEXT_VALUE_DICT]
TEXT_VALUE_GROUPS = typing.Dict[str, TEXT_VALUE_DICT_LIST]
TEXT_VALUE_COLLECTION = typing.Dict[
    typing.Literal["groups", "values"],
    typing.Union[TEXT_VALUE_DICT_LIST, TEXT_VALUE_GROUPS]
]


class TextValue(typing.Generic[_T]):
    def __init__(self, text: str, value: _T, *, group: str = None, index: int = None):
        if isinstance(text, bytes):
            text = text.decode()

        if text is None or not isinstance(text, str):
            raise ValueError(f"The text on a {self.__class__.__name__} must be a string")

        self.__text = text
        self.__value = value
        self.__index = index or -1
        self.__group = group

    @property
    def text(self) -> str:
        return self.__text

    @property
    def value(self) -> _T:
        return self.__value

    @property
    def index(self) -> int:
        return self.__index

    @property
    def group(self) -> typing.Optional[str]:
        return self.__group

    def __str__(self):
        if self.group:
            group = f"[{self.group}] "
        else:
            group = ''

        if self.index >= 0:
            index = f"{self.index}: "
        else:
            index = ''

        return f"{group}{index}{self.text} => {str(self.value)}"

    def __repr__(self):
        if self.group:
            group = f'"group": "{self.group}", '
        else:
            group = ''

        if self.index >= 0:
            index = f'"index": {self.index}, '
        else:
            index = ''

        return '{{group}{index}"text": "{text}", "value": {value}}'.format(
            group=group,
            index=index,
            text=self.text,
            value=f'"{self.value}"' if isinstance(self.value, str) else self.value
        )

    def __eq__(self, other: typing.Union[str, TextValue[_T]]) -> bool:
        if isinstance(other, TextValue):
            return self.group == other.group \
                and self.index == other.index \
                and self.text == other.text \
                and self.value == other.value
        elif isinstance(other, str):
            return self.text == other

        return self.value == other

    def __lt__(self, other: typing.Union[str, TextValue[_T]]) -> bool:
        if isinstance(other, TextValue):
            if self.group == other.group:
                return self.text < other.text if self.index == other.index else self.index < other.index
            elif self.group is None:
                return True
            elif other.group is None:
                return False
            return self.group < other.group
        elif isinstance(other, str):
            return self.text < other

        return self.value < other

    def __le__(self, other: typing.Union[str, TextValue[_T]]) -> bool:
        return self < other or self == other

    def __gt__(self, other: typing.Union[str, _T, TextValue[_T]]) -> bool:
        if isinstance(other, TextValue):
            if self.group == other.group:
                return self.text > other.text if self.index == other.index else self.index > other.index
            elif self.group is None:
                return True
            elif other.group is None:
                return False
            return self.group > other.group
        elif isinstance(other, str):
            return self.text > other

        return self.value > other


    def __ge__(self, other: typing.Union[str, TextValue[_T]]) -> bool:
        return self > other or self == other

    def __hash__(self):
        values_to_hash = list()

        if self.group:
            values_to_hash.append(self.group)

        if self.index >= 0:
            values_to_hash.append(self.index)

        values_to_hash.append(self.text)

        if isinstance(self.value, typing.Hashable):
            values_to_hash.append(self.value)
        else:
            values_to_hash.append(str(self.value))

        return hash(tuple(values_to_hash))

    @property
    def tuple(self) -> typing.Tuple[_T, str]:
        """
        Returns:
            A tuple representation of the two values, with the value first and the name second
        """
        return self.value, self.value

    @property
    def dict(self) -> TEXT_VALUE_DICT:
        """
        Returns:
            A dictionary representation of the value with the raw value, its text, and its group
        """
        return {
            "group": self.group,
            "value": self.value,
            "text": self.text
        }


class TextValues(typing.Generic[_T]):
    def __init__(self):
        self.__values: typing.List[TextValue[_T]] = list()

    def add_value(self, value: TextValue[_T]) -> TextValues[_T]:
        self.__values.append(value)
        self.__values = sorted(self.__values)
        return self

    def add(self, text: str, value: _T, *, group: str = None, index: int = None) -> TextValues[_T]:
        return self.add_value(
            TextValue(text=text, value=value, group=group, index=index)
        )

    @typing.overload
    def __getitem__(self, index: slice) -> TextValues[_T]:
        new_values = self.__class__()

        for member in self.__values[index]:
            new_values.add_value(member)

        return new_values

    def __getitem__(self, index: int) -> TextValue[_T]:
        return self.__values[index]

    @property
    def options(self) -> TEXT_VALUE_TUPLES:
        formed_options: TEXT_VALUE_TUPLES = list()
        values_to_add = [value for value in self.__values]

        for group_name in self.groups:
            group = list()
            for member in self.group(group_name):
                group.append(member.tuple)
                values_to_add.remove(member)
            formed_options.append((group_name, tuple(group)))

        values_to_add = sorted(values_to_add)

        for member in sorted(values_to_add, reverse=True):
            formed_options.insert(0, member.tuple)

        return formed_options

    @property
    def groups(self) -> typing.Sequence[str]:
        return sorted({
            value.group
            for value in self.__values
            if value.group is not None
        })

    def group(self, group_name: str) -> typing.Iterable[TextValue[_T]]:
        return sorted([
            value
            for value in self.__values
            if value.group == group_name
        ])

    @property
    def dict(self) -> TEXT_VALUE_COLLECTION:
        formed_options: TEXT_VALUE_COLLECTION = {
            "groups": defaultdict(list)
        }

        values_to_add = [value for value in self.__values]

        for group_name in self.groups:
            for member in self.group(group_name):
                formed_options['groups'][group_name].append(member.dict)
                values_to_add.remove(member)

        values_to_add = sorted(values_to_add)

        formed_options['values'] = [
            member.dict
            for member in values_to_add
        ]

        return formed_options

    def __iter__(self):
        return iter(self.__values)

    def __len__(self) -> int:
        return len(self.__values)

    def __str__(self):
        return str([value for value in self.__values])

    def __repr__(self):
        return str(self.options)


class CommonEnum(PydanticEnum):
    """
    Base enum class allowing for advanced
    """

    @classmethod
    def get(cls, value: typing.Union[Self, typing.SupportsInt, str] = None) -> Self:
        """
        Get the concrete value of the given value based on if it already is a member, whether the name was passed,
        or whether its value/index was passed

        Args:
            value: Either a member, index, value, or name to indicate the value of interest

        Returns:
            The interpretation of the value in the form of a concrete member
        """
        if value is None:
            return cls.default()
        elif isinstance(value, cls):
            return value
        elif isinstance(value, str):
            return cls.by_name(value)

        value = cls.by_value(value)

        if value is None:
            raise KeyError(f"No {cls.__name__} values can be found with a value or name of {str(value)}")

        return value

    @classmethod
    @abc.abstractmethod
    def default(cls) -> Self:
        """
        The default enum member
        """
        ...

    @classmethod
    def entry_to_index(cls) -> typing.Mapping[Self, int]:
        """
        Returns:
            A mapping between each entry of the enumeration to its index
        """
        return {
            member: index
            for index, member in enumerate(cls)
        }

    @classmethod
    def get_index(cls, member: typing.Union[Self, typing.SupportsInt, str]) -> typing.SupportsInt:
        """
        Get the index of the passed in value

        Args:
            member: Either a member, index, value, or name to indicate the value of interest

        Returns:
            The index of the given value
        """
        if not isinstance(member, cls):
            member = cls.get(member)

        index: typing.Optional[int] = cls.entry_to_index().get(member)

        if index is None:
            raise ValueError(f"'{str(member)}' is not a valid member of {cls.__name__}")

        return index

    @classmethod
    def by_name(cls, name: str) -> typing.Optional[Self]:
        """
        Find a value based off of its name

        Args:
            name: The name of the desired member to find

        Returns:
            A member matching the given name
        """
        for entry in cls:
            if entry.name.lower() == name.lower():
                return entry

        # The given string might actually be the value since it didn't match on the name of a member,
        # so check to see if it matches the value of a member
        return cls.by_value(name)

    @classmethod
    def by_value(cls, value: typing.Union[str, typing.SupportsInt]) -> typing.Optional[Self]:
        """
        Get the member matching the given value

        First attempts to find the member based off of the value then by its index

        Args:
            value: The value to find

        Returns:
            A member whose value or index matches the passed in value
        """
        # First loop through each member to see if its value matches what was asked for
        for entry in cls:
            # Return the entry if the values match
            if entry.value == value:
                return entry

        # If a member couldn't be found based on its value and the given value is like an int,
        # check to see if there's a member whose index matches what was passed
        if isinstance(value, typing.SupportsInt):
            for member, index in cls.entry_to_index().items():
                if index == int(value):
                    return member

        return None

    @classmethod
    def values(cls) -> TextValues[str]:
        values: TextValues[str] = TextValues()

        for index, member in enumerate(cls):
            text = member.name
            text = text.replace("_", " ")
            text = text.title()

            values.add(text=text, value=member.value, index=index)

        return values

    @classmethod
    def get_options(cls) -> TEXT_VALUE_TUPLES:
        return cls.values().options

    def __eq__(self, other: typing.Union[Self, typing.SupportsInt, str]) -> bool:
        """
        Determine whether this member matches the given member

        Performs a comparison based off of index in order to keep the logic in l ine with the other comparison functions

        Args:
            other: The other value to compare to

        Returns:
            Whether this member matches the other
        """
        if self == other:
            return True

        other_index = self.__class__.get_index(other)
        this_index = self.__class__.get_index(self)

        return this_index == other_index

    def __lt__(self, other: typing.Union[Self, typing.SupportsInt, str]) -> bool:
        """
        Determine if this member is less than the value in the other

        Args:
            other: Either the name, value, index, or member of the member to compare to

        Returns:

        """
        other_index = self.__class__.get_index(other)
        this_index = self.__class__.get_index(self)

        return this_index < other_index

    def __le__(self, other: typing.Union[Self, typing.SupportsInt, str]) -> bool:
        other_index = self.__class__.get_index(other)
        this_index = self.__class__.get_index(self)

        return this_index <= other_index

    def __gt__(self, other: typing.Union[Self, typing.SupportsInt, str]) -> bool:
        other_index = self.__class__.get_index(other)
        this_index = self.__class__.get_index(self)

        return this_index > other_index

    def __ge__(self, other: typing.Union[Self, typing.SupportsInt, str]) -> bool:

        other_index = self.__class__.get_index(other)
        this_index = self.__class__.get_index(self)

        return this_index >= other_index

    @classmethod
    def validate(cls, value: typing.Union[Self, typing.SupportsInt, str]) -> Self:
        """
        Method used by pydantic to validate and potentially coerce a `v` into a `cls` enum type.

        Coercion from a `str` into a `cls` enum instance is performed _case-insensitively_ based on
        the `cls` enum's `name` fields. For example, enum Foo with member `bar = 1` is coercible by
        providing `"bar"`, _not_ `1`.

        Example:
        ```python
        class Foo(PydanticEnum):
            bar = 1

        class Model(pydantic.BaseModel):
            foo: Foo

        Model(foo=Foo.bar) # valid
        Model(foo="bar") # valid
        Model(foo="BAR") # valid

        Model(foo=1) # invalid
        ```
        """
        return cls.get(value)


class TypeDefinition:
    """
    Defines a nested type tree used to aid with annotated type checking
    """
    @classmethod
    def from_type(cls, value_type: typing.Type) -> TypeDefinition:
        """
        Construct a TypeDefinition object based off of a type
        """
        origin = typing.get_origin(value_type)
        inner_types = typing.get_args(value_type)
        return cls(value_type, *inner_types, origin=origin)

    def __init__(
        self,
        primary_type: typing.Type,
        *inner_types: typing.Union[typing.Type, TypeDefinition],
        origin: typing.Type = None
    ):
        self.primary_type = primary_type
        self.origin = origin if origin else primary_type

        self.inner_types = [
            inner_type if isinstance(inner_type, TypeDefinition) else self.__class__.from_type(inner_type)
            for inner_type in inner_types
        ]

    def matches(self, value) -> bool:
        if isinstance(self.origin, typing._SpecialForm):
            # Check to see if the value matches one of the subtypes
            if len(self.inner_types) == 0:
                return True
            else:
                for inner_type in self.inner_types:
                    if inner_type.matches(value):
                        return True
                return False

        if not isinstance(value, self.origin):
            return False

        if len(self.inner_types) == 0:
            return True

        if issubclass(self.origin, typing.Mapping) and issubclass(type(value), self.origin):
            # Make sure all keys and values match
            key_type = self.inner_types[0]
            value_type = self.inner_types[1] if len(self.inner_types) > 1 else None

            for key, inner_value in value.items():
                if not key_type.matches(key):
                    return False
                if value_type is not None and not value_type.matches(inner_value):
                    return False
        elif issubclass(self.origin, typing.Iterable) and isinstance(value, self.origin):
            for item in value:
                value_matches = False
                for inner_type in self.inner_types:
                    if inner_type.matches(item):
                        value_matches = True
                        break
                if not value_matches:
                    return False

        return True

    def __contains__(self, item):
        return self.matches(item)

    def __eq__(self, other):
        if not isinstance(other, TypeDefinition):
            return False

        if self.origin != other.origin:
            return False

        if len(self.inner_types) != len(other.inner_types):
            return False

    def __str__(self):
        return str(self.primary_type)

    def __repr__(self):
        return str(self.primary_type)
