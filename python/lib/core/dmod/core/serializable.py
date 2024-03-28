from abc import ABC
from numbers import Number
from enum import Enum
from typing import Any, Callable, ClassVar, Dict, List, Type, TypeVar, TYPE_CHECKING, Union, Optional
from typing_extensions import Self, TypeAlias
from pydantic import BaseModel, Field
from functools import lru_cache
import inspect
import json

from .decorators import deprecated

if TYPE_CHECKING:
    from pydantic.typing import (
        AbstractSetIntStr,
        MappingIntStrAny,
        DictStrAny
    )

M = TypeVar("M", bound="Serializable")
T = TypeVar("T")
R = Union[str, int, float, bool, None]

FnSerializer: TypeAlias = Callable[[T], R]
SelfFieldSerializer: TypeAlias = Callable[[M, T], R]
FieldSerializer = Union[SelfFieldSerializer[M, Any], FnSerializer[Any]]

SimpleData = Union[int, float, bool, str]


class Serializable(BaseModel, ABC):
    """
    An interface class for an object that can be serialized to a dictionary-like format (i.e., potentially a JSON
    object) and JSON string format based directly from dumping the aforementioned dictionary-like representation.

    Subtypes of `Serializable` should specify their fields following
    [`pydantic.BaseModel`](https://docs.pydantic.dev/usage/models/) semantics (see example below).
    Notably, `to_dict` and `to_json` will exclude `None` fields and serialize fields using any
    provided aliases (i.e.  `pydantic.Field(alias="some_alias")`). Also, enum subtypes are
    serialized using their member `name` property.

    Objects of this type will also used the JSON string format as their default string representation.

    While not strictly enforced (because this probably isn't possible), it is HIGHLY recommended that instance
    attribute members of implemented sub-types be of types that are either convertible to strings using the ``str()``
    built-in, or are themselves also implementations of ::class:`Serializable`.  The convenience class method
    ::method:`serialize` will handle serializing any such member objects appropriately, providing a clean interface for
    this.

    An exception to the aforementioned recommendation is the ::class:`datetime.datetime` type.  Subtype attributes of
    ::class:`datetime.datetime` type should be parsed and serialized using the pattern returned by the
    ::method:`get_datetime_str_format` class method.  A reasonable default is provided in the base interface class, but
    the pattern can be adjusted either by overriding the class method directly or by having a subtypes set/override
    its ::attribute:`_SERIAL_DATETIME_STR_FORMAT` class attribute.  Note that the actual parsing/serialization logic is
    left entirely to the subtypes, as many will not need it (and thus should not have to worry about implement another
    method or have their superclass bloated by importing the ``datetime`` package).

    Example:
    ```
    # specify field as class variable, specify final type using type hint.
    # pydantic will try to coerce a field into the specified type, if it can't, a
    # `pydantic.ValidationError` is raised.

    class User(Serializable):
        id: int
        username: str
        email: str # more appropriately, `pydantic.EmailStr`

    >>> user = User(id=1, username="uncle_sam", email="uncle_sam@fake.gov")
    >>> user.to_dict() # {"id": 1, "username": "uncle_sam", "email": "uncle_sam@fake.gov"}
    >>> user.to_json() # '{"id": 1, "username": "uncle_sam", "email": "uncle_sam@fake.gov"}'
    ```
    """

    _SERIAL_DATETIME_STR_FORMAT: ClassVar[str] = '%Y-%m-%d %H:%M:%S'

    # global pydantic options
    class Config:
        # fields can be populated using their given name or provided alias
        allow_population_by_field_name = True
        field_serializers: Dict[str, FieldSerializer[M]] = {}
        """
        Mapping of field name to callable that changes the default serialized form of a field.
        This is often helpful when a field requires a use case specific representation (i.e.
        datetime) or is not JSON serializable.

        Callables can be specified as either:
            (value: T) -> R or
            (self:  M, value: T) -> R
        where:
            T is the field type
            M is an instance of the Serializable subtype
            R is the, json serializable, return type of the transformation

        Example:

            class Observation(Serializable):
                value: float
                value_time: datetime.datetime
                value_unit: str

                class Config:
                    field_serializers = {
                        "value_time": lambda value_time: value_time.isoformat(timespec="seconds")
                    }

            o = Observation(value=42.0, value_time=datetime(2020, 1, 1), value_unit="m")
            expect = {"value": 42.0, "value_time": "2020-01-01T00:00:00", "value_unit": "m"}

            assert o.dict() == expect
        """

    @classmethod
    def _get_invalid_type_message(cls):
        invalid_type_msg = 'Invalid deserialized type for ' + cls.__name__ + ' property {}: expected {} but got {}'
        return invalid_type_msg

    @classmethod
    def factory_init_from_deserialized_json(cls: Type[Self], json_obj: dict) -> Optional[Self]:
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Parameters
        ----------
        json_obj

        Returns
        -------
        A new object of this type instantiated from the deserialize JSON object dictionary
        """
        try:
            return cls(**json_obj)
        except:
            return None

    @classmethod
    def get_datetime_str_format(cls):
        """
        Get the string representation of the datetime format pattern for serializing date and time objects used by this
        class.

        Returns
        -------
        str
            The string representation of the datetime format pattern for serializing date and time objects used by this
            class.
        """

        return cls._SERIAL_DATETIME_STR_FORMAT

    @classmethod
    @deprecated("In the future this will be removed. Use pydantic type hints, validators, or root validators instead.")
    def parse_simple_serialized(cls, json_obj: dict, key: str, expected_type: Type, required_present: bool = True,
                                converter: Callable = None):
        """
        Parse a value of a specified type out of a dictionary, possibly converting a present value to an equivalent of
        the expected type, and throw errors if a value of the expected type cannot be obtained.

        This method attempts to retrieve a value from the provided dictionary at the specified key.  If the given lookup
        key is not present in the dictionary, and thus no value can be retrieved, either ``None`` is returned or a
        ::class:`RuntimeError` is raised.  This depends on whether it is required the value be present, as controlled by
        the ``required_present`` param (which is ``True`` by default).

        If a value can be retrieved from the dictionary, it must be of the provided expected type.  A
        ::class:`RuntimeError` is raised if the method cannot (eventually) obtain a value of the expected type.  If a
        value of the expected type is either retrieved directly or obtained via conversion (without information loss),
        it is returned.

        A converter callable may optionally be passed to try to convert an "original" value of a different type to the
        expected type if necessary.  E.g., it is sensible when expecting a numeric value be able to handle getting a
        string representation like ``"5"``, so a function can be passed that accounts for this and converts the value.
        Note that errors during a conversion attempt are currently caught and obscured, with the aforementioned
        ::class:`RuntimeError` being raised after.

        Additionally, it is required that converted representations be truly equivalent, in particular for numeric
        types, which is not automatically the case after successful conversions.  As such, original and converted values
        are tested for equivalence IFF they are both some numeric type.  A ::class:`RuntimeError` is raised in such
        cases if the values are not equivalent.

        It is strongly recommended that conversion functions not process values through any intermediate types before
        returning the eventual converted value (e.g., going from string to float to int to handle an original value
        like ``"5.0"``), as this risks losing information in a way that is not possible to protect against generally
        (e.g., an original value of ``"5.1"`` would be converted to ``5.1`` and then to ``5``, but since the original
        value was non-numeric no equivalence check is performed, nor is it easy to introduce one).

        A ::class:`ValueError` is raised if a conversion takes place successfully but does not produce a converted value
        of the expected type (i.e. effectively an invalid conversion function).

        Parameters
        ----------
        json_obj: dict
            The containing serialize dictionary.
        key: str
            The key for the value of interest.
        expected_type: Type
            The expected type for the value.
        required_present: bool
            Whether the key not being present in the dictionary causes an error to be raised.
        converter: Callable
            A callable handle to potentially use to try to convert parsed values of non-expected types to expected type.

        Returns
        -------
        The parsed value of the expected type, possibly after conversion, or ``None`` the ``required`` parameter is
        ``False`` and the value's key is not present.

        Raises
        -------
        RuntimeError
            If either the value is required and not present; the value is not of the expected type and there is not
            provided conversion callable; the value is not of the expected type and attempting to convert fails; or
            the value is not of an expected numeric type, is of some other numeric type, has a converted value
            successfully obtained via the conversion callabl, and is not equal to the converted value.
        ValueError
            If, when the value is present and not of the expected type, an invalid conversion callable is used
            successfully to create a converted value that is still not of the expected type.
        """
        if key not in json_obj:
            if required_present:
                raise RuntimeError("Parsed value key '{}' not found while deserializing {}".format(key, cls.__name__))
            else:
                return None
        value = json_obj[key]
        # If the value read is the right type, finish here
        if isinstance(value, expected_type):
            return value
        # Otherwise, try converting if converter callable was supplied
        try:
            if value is None or converter is None:
                raise RuntimeError('caught and another thrown in except')
            converted_value = converter(value)
        except:
            raise RuntimeError(cls._get_invalid_type_message().format(key, expected_type, value.__class__.__name__))
        # Sanity check that the converted value is of the correct type
        if not isinstance(converted_value, expected_type):
            msg = 'Received and used converter callable for parsing serialized JSON that outputs wrong type - '
            msg += 'expected: {}, output: {}'.format(expected_type.__name__, converted_value.__class__.__name__)
            raise ValueError(msg)
        # Finally, be careful when dealing with both numeric values that converted is actually equal to original
        if isinstance(converted_value, Number) and isinstance(value, Number) and value != converted_value:
            msg = cls._get_invalid_type_message() + '(loss of precise value occurs in converting)'
            raise RuntimeError(msg.format(key, expected_type, value.__class__.__name__))
        # If we get this far, then return the converted value
        return converted_value

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        """
        Get the representation of this instance as a serialized dictionary or dictionary-like object (e.g., a JSON
        object). Field's are serialized using an alias, if provided. Field's that are `None` are
        excluded from serialization.

        Since the returned value must be serializable and JSON-like, key and value types are restricted.  In particular,
        the returned value type, which this docstring will call ``D``, must adhere to the criteria defined below:

        * ``D`` : a ``dict`` with ``str`` keys and with all values being of some type within the defined set ``T``
        * ``T`` : a set of types containing the following:
            * ``str``
            * ::class:``Number`
            * ``D``
            * ``list`` with all elements being some type within the defined set ``T``

        Returns
        -------
        Dict[str, Union[str, Number, dict, list]]
            The representation of this instance as a serialized dictionary or dictionary-like object, with valid types
            of keys and values.
        """
        return self.dict(exclude_none=True, by_alias=True)

    def dict(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = False,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> "DictStrAny":
        serial = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

        transformers = _collect_field_transformers(type(self))
        return _transform_fields(self, transformers, serial, by_alias=by_alias)

    def __str__(self):
        return str(self.to_json())

    def to_json(self) -> str:
        """
        Get the representation of this instance as a serialized JSON-formatted string.

        Returns
        -------
        json_string
            the serialized JSON string representation of this instance
        """
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def _get_value(
        cls,
        v: Any,
        to_dict: bool,
        by_alias: bool,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]],
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]],
        exclude_unset: bool,
        exclude_defaults: bool,
        exclude_none: bool,
    ) -> Any:
        """
        Method used by pydantic to serialize field values.

        Override how `enum.Enum` subclasses are serialized by pydantic. Enums are serialized using
        their member name, not their value.
        """
        # serialize enum's using their name property
        if isinstance(v, Enum) and not getattr(cls.Config, "use_enum_values", False):
            return v.name

        return super()._get_value(
            v,
            to_dict=to_dict,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            include=include,
            exclude=exclude,
            exclude_none=exclude_none,
        )


class ResultIndicator(Serializable, ABC):
    """
    A type extending from ::class:`Serializable` for encapsulating a status indication for a result of something.

    Parameters
    ----------
    success : bool
        Whether this indicates a successful result.
    reason : str
        A very short, high-level summary of the result.
    message : str
        An optional, more detailed explanation of the result, which by default is an empty string.

    Attributes
    ----------
    success : bool
        Whether this indicates a successful result.
    reason : str
        A very short, high-level summary of the result.
    message : str
        An optional, more detailed explanation of the result, which by default is an empty string.

    """
    success: bool = Field(description="Whether this indicates a successful result.")
    reason: str = Field(description="A very short, high-level summary of the result.")
    message: str = Field("", description="An optional, more detailed explanation of the result, which by default is an empty string.")

    def __bool__(self) -> bool:
        """
        Implementation of truth value testing for instances, which directly depends on the value of ``success``.

        Returns
        -------
        bool
            The current value of the instance's ::attribute:`success` attribute.
        """
        return self.success


class BasicResultIndicator(ResultIndicator):
    """
    Bare-bones, concrete implementation of ::class:`ResultIndicator` that also supports carrying simple data.
    """

    data: Optional[Union[SimpleData, Dict[str, SimpleData], List[SimpleData], Serializable]]

# NOTE: function below are intentionally not methods on `Serializable` to avoid subclasses
# overriding their behavior.

@lru_cache
def _collect_field_transformers(cls: Type[M]) -> Dict[str, FieldSerializer[M]]:
    transformers: Dict[str, FieldSerializer[M]] = {}

    # base case
    if cls == Serializable:
        return transformers

    super_classes = cls.__mro__
    base_class_index = super_classes.index(Serializable)

    # index 0 is the calling cls try and merge `field_serializers` from superclasses up until
    # Base class (stopping condition). merge in reverse order of mro so child class
    # `field_serializers` override superclasses `field_serializers`.
    for s in super_classes[1:base_class_index][::-1]:
        if not issubclass(s, Serializable):
            continue

        # doesn't have a Config class or Config.field_serializers
        if not hasattr(s, "Config") and not hasattr(s.Config, "field_serializers"):
            continue

        transformers.update(_collect_field_transformers(s))

    # has Config class and Config.field_serializers
    if hasattr(cls, "Config") and hasattr(cls.Config, "field_serializers"):
        transformers.update(cls.Config.field_serializers)

    return transformers


def _get_field_alias(cls: Type[M], field_name: str) -> str:
    # NOTE: KeyError will raise if field_name does not exist
    return cls.__fields__[field_name].alias


def _transform_fields(
    self: M,
    transformers: Dict[str, FieldSerializer[M]],
    serial: Dict[str, Any],
    by_alias: bool = False,
) -> Dict[str, Any]:
    for field, transform in transformers.items():
        if by_alias:
            field = _get_field_alias(type(self), field)

        if field not in serial:
            # TODO: field could have been excluded. need to consider what to do if invalid
            # serial key was provided.
            continue

        if not isinstance(transform, Callable):
            error_message = (
                f"non-callable field_transformer provided for field {field!r}."
                "\n\n"
                "field_transformers should be specified as either:"
                "\n"
                "\t(value: T) -> R\n"
                "\t(self:  M, value: T) -> R\n"
                "where:\n"
                "\tT is the field type\n"
                "\tM is an instance of the Serializable subtype\n"
                "\tR is the, json serializable, return type of the transformation"
            )
            raise ValueError(error_message)

        try:
            sig = inspect.signature(transform)

            if len(sig.parameters) == 1:
                serial[field] = transform(serial[field])

            elif len(sig.parameters) == 2:
                serial[field] = transform(self, serial[field])

            else:
                error_message = (
                        f"unsupported parameter length for field_transformer callable, {field!r}."
                        "\n\n"
                        "field_transformer's take either 1 or 2 parameters, (value: T) or (self, value: T),\n"
                        "where T is the type of the field."
                        )
                raise RuntimeError(error_message)

        # ValueError can be thrown by built-in functions (i.e. `str`) that are,
        # for example, implemented in C.
        except ValueError:
            # assume that build-in's that throw on `inspect.signature` only
            # take a single parameter.
            serial[field] = transform(serial[field])

    return serial
