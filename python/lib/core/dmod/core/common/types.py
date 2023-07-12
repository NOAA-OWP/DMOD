"""
@TODO: Put a module wide description here
"""
from __future__ import annotations

import typing


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

    @classmethod
    def from_value(cls, value) -> TypeDefinition:
        """
        Construct a TypeDefinition based off of a value

        Example:
            >>> sample = {"one": [1, 2, 3, 4], "two": "2"}
            >>> expected_type = typing.MutableMapping[str, typing.Union[str, typing.MutableSequence[int]]]
            >>> type_definition = TypeDefinition.from_type(expected_type)
            >>> TypeDefinition.from_value(sample) == type_definition
            True

        Args:
            value: The value to base the new TypeDefinition off of

        Returns:
            A new TypeDefinition based off of the given value
        """
        raise NotImplementedError("A type definition may not be created from a value yet")

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
