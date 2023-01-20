import os
import typing
import abc
import json
import inspect
import logging
import collections
import math

from datetime import datetime
from datetime import date
from datetime import time

import pandas
import numpy
import pytz

from dateutil.parser import parse as parse_date

import dmod.metrics as metrics
import dmod.metrics.metric as metric_functions

import dmod.core.common as common

from .. import util

logging.basicConfig(
    filename='evaluation.log',
    level=logging.getLevelName(os.environ.get('METRIC_LOG_LEVEL', os.environ.get("DEFAULT_LOG_LEVEL", "DEBUG"))),
    format=os.environ.get("LOG_FORMAT", "%(asctime)s,%(msecs)d %(levelname)s: %(message)s"),
    datefmt=os.environ.get("LOG_DATEFMT", "%H:%M:%S")
)


def get_specifications(base_specification: typing.Type = None) -> typing.List[typing.Type]:
    """
    Returns:
        All implemented specifications
    """
    if base_specification is None:
        base_specification = Specification

    subclasses = [
        cls
        for cls in base_specification.__subclasses__()
        if not inspect.isabstract(cls)
    ]

    abstract_subclasses = [
        cls
        for cls in base_specification.__subclasses__()
        if inspect.isabstract(cls)
    ]

    for abstract_class in abstract_subclasses:
        subclasses.extend(get_specifications(abstract_class))

    return subclasses


def is_a_value(o) -> bool:
    """
    Whether the passed object is a value and not some method or module or something

    Args:
        o:
            The object to be tested
    Returns:
        Whether the passed object is a value and not some method or module or something
    """
    # This will exclude methods, code, stuff like __get__, __set__, __add__, async objects, etc
    return not (
            inspect.iscode(o)
            or inspect.isdatadescriptor(o)
            or inspect.ismethoddescriptor(o)
            or inspect.ismemberdescriptor(o)
            or inspect.ismodule(o)
            or inspect.isgenerator(o)
            or inspect.isgeneratorfunction(o)
            or inspect.ismethod(o)
            or inspect.isawaitable(o)
            or inspect.isabstract(o)
    )


def value_matches_parameter_type(value, parameter: typing.Union[inspect.Parameter, typing.Type]) -> bool:
    """
    Checks to see if the given value matches that of the passed in parameter

    Since a parameter without an annotation is interpreted as `typing.Any`, `True` is returned if not type is indicated

    Args:
        value: The value to check
        parameter: The parameter to check

    Returns:
        Whether the given value conforms to the parameter
    """
    if isinstance(parameter, inspect.Parameter) and parameter.annotation == parameter.empty:
        return True

    if isinstance(parameter, inspect.Parameter):
        parameter = parameter.annotation

    is_typing_class = isinstance(parameter, typing._GenericAlias)
    is_union = is_typing_class and isinstance(parameter, typing._UnionGenericAlias)
    parameter_is_number = util.type_is_number(parameter)

    if parameter_is_number:
        return util.value_is_number(value)
    if is_union:
        return True in [
            value_matches_parameter_type(value, t)
            for t in typing.get_args(parameter)
        ]
    if is_typing_class:
        return isinstance(value, typing.__dict__[parameter._name])

    try:
        return isinstance(value, parameter)
    except TypeError:
        return False


def convert_value(value: typing.Any, parameter: typing.Union[inspect.Parameter, typing.Type]) -> typing.Any:
    """
    Attempts to convert a given value to the type expected by the parameter

    Args:
        value: The value to convert
        parameter: The function parameter that may or may not dictate what to cast the value as

    Returns:
        An attempted conversion if a parameter type is given; just the original value otherwise
    """
    if isinstance(parameter, inspect.Parameter):
        parameter_type: typing.Type = None if parameter.annotation == parameter.empty else parameter.annotation
    else:
        parameter_type: typing.Union[typing.Type, typing.Type[Specification]] = parameter

    if parameter_type is None:
        return value

    if parameter_type in common.get_subclasses(Specification):
        return parameter_type.create(value)
    if isinstance(value, str) and util.value_is_number(value) and util.type_is_number(parameter_type):
        return float(value)
    elif isinstance(value, bytes) and util.value_is_number(value) and util.type_is_number(parameter_type):
        return float(value.decode())
    elif not (isinstance(value, str) or isinstance(value, bytes)) and isinstance(value, typing.Sequence):
        expected_type = typing.get_args(parameter_type)
        converted_values = [
            convert_value(member, expected_type[0])
            for member in value
        ]
        return converted_values

    return value


def create_class_instance(cls, data, decoder: json.JSONDecoder = None):
    """
    Dynamically creates a class based on the type of class and the given parameters

    Args:
        cls: The type of class to construct
        data: The data that provides construction arguments
        decoder: An optional json decoder that will help deserialize any json inputs

    Returns:
        An instance of the given `cls`
    """
    # If the object is already the intended class, you're done!
    if isinstance(data, cls):
        return data

    # If the object is some sort of buffer, go ahead and read in the data for later interpretation
    if hasattr(data, "read"):
        data = data.read()

    # If the data is a series of bytes, convert that into a string for later interpretation
    if isinstance(data, bytes):
        data: str = data.decode()

    # If the data is a string AND it looks like it can be valid json, try to convert it into a dictionary
    if isinstance(data, str):
        stripped_data = data.strip()
        is_possible_json_object = stripped_data.startswith("{") and stripped_data.endswith("}")
        is_possible_json_array = stripped_data.startswith("[") and stripped_data.endswith("]")
        if is_possible_json_object or is_possible_json_array:
            try:
                data: typing.Dict[str, typing.Any] = json.loads(data, cls=decoder)
            except json.JSONDecodeError:
                # If the string can't be interpreted as JSON, try to interpret in another way later.
                logging.error(
                    "Tried to interpret string data as json, but it wasn't valid. "
                    "Continuing with attempted parsing."
                )

    # If data is a list of lists or objects, send each back to this function and return a list instead of a single value
    if not isinstance(data, str) and isinstance(data, typing.Sequence):
        return [
            create_class_instance(cls, input_value, decoder)
            for input_value in data
            if is_a_value(input_value)
        ]

    # If it doesn't have some sort of '__getitem__' or is a string, we can assume that this is a singular value
    # and we can just send that as a parameter
    if isinstance(data, str) or not hasattr(data, "__getitem__"):
        return cls(data)

    constructor_signature: inspect.Signature = inspect.signature(cls)

    arguments: typing.Dict[str, typing.Any] = dict()

    required_parameters = [
        parameter
        for parameter in constructor_signature.parameters.values()
        if parameter.default == parameter.empty
           and parameter.kind != parameter.VAR_KEYWORD
           and parameter.kind != parameter.VAR_POSITIONAL
    ]

    missing_parameters = list()

    if hasattr(data, "__getitem__") and not isinstance(data, typing.Sequence):
        for parameter in constructor_signature.parameters.values():  # type: inspect.Parameter
            if parameter.kind == parameter.VAR_KEYWORD:
                continue

            try:
                value = data[parameter.name]

                value = convert_value(value, parameter)

                arguments[parameter.name] = value
            except KeyError:
                if parameter not in required_parameters:
                    arguments[parameter.name] = parameter.default
                else:
                    missing_parameters.append(str(parameter))

        if missing_parameters:
            raise ValueError(f"'{cls} can't be constructed - arguments are missing: {', '.join(missing_parameters)}")

        if 'properties' not in arguments or arguments['properties'] is None:
            arguments['properties'] = dict()

        arguments['properties'].update(
            {
                key: value
                for key, value in data.items()
                if key not in arguments
            }
        )

        return cls(**arguments)

    raise ValueError(f"Type '{type(data)}' cannot be read as JSON")


class Specification(abc.ABC):
    """
    Instructions for how different aspects of an evaluation should work
    """
    __slots__ = ['__properties']

    @classmethod
    def create(cls, data: typing.Union[str, dict, typing.IO, bytes, typing.Sequence], decoder: json.JSONDecoder = None):
        """
        A factory for the given specification

        Args:
            data: Parameters used to instantiate the specification
            decoder: an optional json decoder used to deserialize the specification

        Returns:
            An instance of the specified specification class
        """
        instance = create_class_instance(cls, data, decoder)

        messages = list()

        if isinstance(instance, typing.Sequence):
            for member in instance:
                messages.extend(member.validate())
        else:
            validation_messages = instance.validate()
            if validation_messages:
                messages.extend(validation_messages)

        if messages:
            message = f"{cls.__name__} could not be properly created:{os.linesep}{os.linesep.join(messages)}"
            raise ValueError(message)

        return instance

    @abc.abstractmethod
    def validate(self) -> typing.Sequence[str]:
        """
        Returns:
            Any messages indicating a problem with the specification
        """
        pass

    @abc.abstractmethod
    def to_dict(self) -> typing.Dict[str, typing.Any]:
        """
        Returns:
            The specification converted into a dictionary
        """
        pass

    def to_json(self, buffer: typing.IO = None) -> typing.Optional[typing.Union[str, typing.IO]]:
        """
        Either converts the instance into a json string or writes that json string into the given buffer

        Args:
            buffer: An optional buffer to feed the json into

        Returns:
            The updated buffer if a buffer is passed, otherwise the json string
        """
        dict_representation = self.to_dict()

        if buffer:
            json.dump(dict_representation, buffer, indent=4)
            return buffer

        return json.dumps(dict_representation, indent=4)

    def __init__(self, properties: typing.Union[typing.Dict[str, typing.Any], str, bytes] = None, **kwargs):
        if properties is None:
            properties = dict()
        elif isinstance(properties, str):
            properties = json.loads(properties)
        elif isinstance(properties, bytes):
            properties = json.loads(properties.decode())

        properties.update(kwargs)

        self.__properties = properties

    @property
    def properties(self) -> typing.Dict[str, typing.Any]:
        """
        Returns:
            A dictionary of arbitrary properties passed into the specification that don't match direct members
        """
        return self.__properties.copy()

    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        """
        Retrieve either the property with the given key or the default

        Args:
            key: The key to the value to retrieve
            default: The value to return if the key is not present

        Returns:
            The property value matching the key if present, `None` otherwise
        """
        return self.__properties.get(key, default)

    def __getitem__(self, key: str) -> typing.Any:
        return self.__properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.__properties

    def __repr__(self) -> str:
        return str(
            {
                key.replace("__", ""): getattr(self, key)
                for key in self.__slots__
            }
        )


class UnitDefinition(Specification):
    """
    A definition of what a measurement unit is or where to find it
    """

    def validate(self) -> typing.Sequence[str]:
        messages = list()

        if not self.__value and not self.__path and not self.__field:
            messages.append("Unit definition is missing a field, a path, and a value; no unit data will be found.")

        fields_and_values = {
            "value": bool(self.__value),
            "path": bool(self.__path),
            "field": bool(self.__field)
        }

        marked_fields = [
            name
            for name, exists in fields_and_values.items()
            if exists
        ]

        if len(marked_fields) > 1:
            messages.append(f"Values for {' and '.join(marked_fields)} have all been set - only one is valid")

        return messages

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        data = dict()

        if self.__field:
            data["field"] = self.__field
        elif self.__path:
            data['path'] = self.__path
        elif self.__value:
            data['value'] = self.__value

        return data

    __slots__ = ["__field", "__path", "__value"]

    def __init__(
        self,
        value: typing.Union[str, bytes] = None,
        field: str = None,
        path: typing.Union[str, typing.Sequence[str]] = None,
        properties: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        super(UnitDefinition, self).__init__(properties, **kwargs)

        self.__field = field

        path_starts_at_root = False

        if isinstance(path, str):
            path_starts_at_root = path.startswith("/")
            self.__path = path.split("/")
        else:
            self.__path = path

        if path_starts_at_root:
            self.__path.insert(0, "$")

        if isinstance(value, bytes):
            value = value.decode()

        self.__value = value

    @property
    def field(self) -> typing.Optional[str]:
        return self.__field

    @property
    def path(self) -> typing.Optional[typing.Sequence[str]]:
        return self.__path

    @property
    def value(self) -> typing.Optional[str]:
        return self.__value

    def __str__(self):
        if self.__field:
            return self.__field

        return ".".join(self.__path)


class ThresholdDefinition(Specification):
    """
    A definition of a single threshold, the field that it comes from, and its significance
    """

    def validate(self) -> typing.Sequence[str]:
        return list()

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "name": self.__name,
            "field": self.__field,
            "unit": self.__unit.to_dict(),
            "weight": self.__weight,
            "properties": self.__properties
        }

    __slots__ = ["__name", "__field", "__weight", "__unit"]

    def __init__(
        self,
        name: typing.Union[str, bytes],
        field: typing.Union[str, bytes, typing.Sequence[str]],
        weight: typing.Union[str, float],
        unit: typing.Union[UnitDefinition, str, dict],
        properties: typing.Union[typing.Dict[str, typing.Any], str] = None,
        **kwargs
    ):
        super().__init__(properties, **kwargs)

        self.__name = name.decode() if isinstance(name, bytes) else name

        if isinstance(field, bytes):
            field = field.decode()

        if isinstance(field, str):
            self.__field = field.split("/")
        else:
            self.__field = field

        self.__weight = weight

        if isinstance(unit, str):
            unit = UnitDefinition(value=unit)
        elif isinstance(unit, dict):
            unit = UnitDefinition.create(unit)

        self.__unit = unit

    @property
    def name(self) -> str:
        """
        Returns:
            The name of the threshold. This should appear as the name of the threshold in the output and doesn't
            have to match the field it came from
        """
        return self.__name

    @property
    def field(self) -> typing.Sequence[str]:
        """
        Returns:
            The name of the field in the datasource where these values are supposed to come from
        """
        return self.__field

    @property
    def weight(self) -> float:
        """
        Returns:
            The significance of the threshold
        """
        return self.__weight

    @property
    def unit(self) -> UnitDefinition:
        return self.__unit

    def __str__(self) -> str:
        return f"{self.__name}, weighing {self.__weight}, from the '{self.__field}' field."

    def __repr__(self) -> str:
        return str(self.to_dict())


class BackendSpecification(Specification):
    """
    A specification of how data should be loaded
    """

    def validate(self) -> typing.Sequence[str]:
        return list()

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "backend_type": self.__backend_type,
            "address": self.__address,
            "data_format": self.__format
        }

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ["__backend_type", "__address", "__format"]

    def __init__(
        self,
        backend_type: str,
        data_format: str,
        address: str = None,
        properties: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        super().__init__(properties, **kwargs)

        self.__backend_type = backend_type
        self.__format = data_format
        self.__address = address

    @property
    def type(self) -> str:
        """
        The type of backend that should be used
        """
        return self.__backend_type

    @property
    def format(self) -> str:
        """
        The type of data to be interpretted

        A single backend type may have more than one format. A `file` may be json, csv, netcdf, etc
        """
        return self.__format

    @property
    def address(self) -> typing.Optional[str]:
        """
        Where the data for the backend to interpret lies
        """
        return self.__address

    def __str__(self) -> str:
        description = self.__backend_type
        if self.__address:
            description += f": {self.__address}"
        else:
            description += f"=> {self.__format}"

        return description


class LoaderSpecification(Specification, abc.ABC):
    """
    Represents a class that uses a backend to load data
    """
    __slots__ = ['_backend']

    @property
    @abc.abstractmethod
    def backend(self) -> BackendSpecification:
        ...


class FieldMappingSpecification(Specification):
    """
    Details on how a field should be aliased
    """

    def validate(self) -> typing.Sequence[str]:
        return list()

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "field": self.__field,
            "map_type": self.__map_type,
            "value": self.__value
        }

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ["__field", "__map_type", "__value"]

    def __init__(
        self,
        field: str,
        map_type: str,
        value: str,
        properties: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        super().__init__(properties, **kwargs)
        self.__field = field
        self.__map_type = map_type
        self.__value = value

    @property
    def field(self) -> str:
        """
        The field to be aliased
        """
        return self.__field

    @property
    def map_type(self) -> str:
        """
        Where the field to be aliased lies (is it a key? Is it a dictionary value? Is it a column?)
        """
        return self.__map_type

    @property
    def value(self) -> str:
        """
        What the field should end up being called
        """
        return self.__value

    def __str__(self) -> str:
        return f"{self.__map_type}: {self.__field} comes from {self.__value}"


class AssociatedField(Specification):
    """
    A specification for additional data that should accompany selected data
    (retrieved measurements? Also get their dates)
    """

    def validate(self) -> typing.Sequence[str]:
        messages = list()
        if self.__name is None or self.__name == '':
            messages.append(f"An index is missing a proper name")

        return messages

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "name": self.__name,
            "datatype": self.__datatype,
            "path": self.__path
        }

        if self.__properties:
            dictionary['properties'] = self.__properties.copy()

        return dictionary

    __slots__ = ["__name", "__datatype", "__path"]

    def __init__(
        self,
        name: str,
        path: typing.Union[str, typing.Sequence[str]] = None,
        datatype: typing.Union[str, typing.Sequence[str]] = None,
        properties: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        super().__init__(properties, **kwargs)

        self.__name = name

        path_starts_at_root = False

        if path is None:
            self.__path = [name]
        elif isinstance(path, str):
            path_starts_at_root = path.startswith("/")
            self.__path = path.split("/")
        else:
            self.__path = path

        if path_starts_at_root:
            self.__path.insert(0, "$")

        self.__datatype = datatype.lower() if datatype else None

    @property
    def name(self) -> str:
        return self.__name

    @property
    def path(self) -> typing.Sequence[str]:
        """
        The path to the data in the source
        """
        return self.__path

    @property
    def datatype(self) -> str:
        """
        The type that the value should be parsed as

        A date may come in as a string - `"2022-01-22T15:33:14-0600"`, for example, but we need to actually use that
        as a date and time. If this isn't converted, it won't match up to `"2022-01-22T16:33:14-0500"`
        """
        return self.__datatype

    def to_datatype(self, value):
        """
        Attempt to convert the given value to the required datatype

        Args:
            value: The value to convert

        Returns:
            The converted value, if specified
        """
        if not self.__datatype or value is None:
            return value

        datatype = self.__datatype.lower()

        if datatype in ("datetime", "date", "time"):
            raw_datetime = parse_date(value)

            if datatype == 'date':
                return raw_datetime.date()
            elif datatype == 'time':
                return raw_datetime.time()
            elif raw_datetime.tzinfo is not None:
                raw_datetime = raw_datetime.astimezone(pytz.utc)

            return raw_datetime

        if datatype in ('float', 'double', 'number') and str(value).isnumeric():
            return float(value)

        if datatype in ('int', 'integer') and str(value).isdigit():
            return int(value)

        if datatype in ('str', 'string', 'word', 'id', 'identifier'):
            return str(value)

        if datatype in ('day',):
            return util.Day(value)

        return value

    def get_concrete_datatype(self) -> typing.Type:
        datatype = self.__datatype.lower()
        if datatype == 'datetime':
            return datetime
        if datatype == 'date':
            return date
        if datatype == 'time':
            return time
        if datatype in ('float', 'double', 'number'):
            return float
        if datatype in ('int', 'integer'):
            return int
        if datatype in ('day',):
            return util.Day

        return str

    def __str__(self):
        return f"{self.__name}: {self.__datatype}"


class ValueSelector(Specification):
    """
    Instructions for how to retrieve values from a data source
    """

    def validate(self) -> typing.Sequence[str]:
        return list()

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "where": self.__where,
            "path": self.__path,
            "origin": self.__origin,
            "datatype": self.__datatype,
            "name": self.__name
        }

        if self.__associated_fields:
            dictionary['associated_fields'] = [
                field.to_dict()
                for field in self.__associated_fields
            ]

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ["__name", "__where", "__path", "__associated_fields", "__datatype", "__origin"]

    def __init__(
        self,
        name: str,
        where: str,
        origin: typing.Union[str, bytes, typing.Sequence[str]] = None,
        path: typing.Union[str, bytes, typing.Sequence[str]] = None,
        associated_fields: typing.Sequence[AssociatedField] = None,
        datatype: str = None,
        properties: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        super().__init__(properties, **kwargs)

        origin_starts_at_root = False

        if isinstance(origin, str):
            origin_starts_at_root = origin.startswith("/")
            origin = origin.split("/")
        elif isinstance(origin, bytes):
            origin = origin.decode()
            origin_starts_at_root = origin.startswith("/")
            origin = origin.split("/")
        elif not origin:
            origin = ["$"]

        if origin_starts_at_root and origin[0] != '$':
            origin.insert(0, "$")

        if origin:
            origin = [
                part
                for part in origin
                if bool(part)
            ]

        path_starts_at_root = False
        if isinstance(path, str):
            path_starts_at_root = path.startswith("/")
            path = path.split("/")
        elif isinstance(path, bytes):
            path = path.decode()
            path_starts_at_root = path.startswith("/")
            path = path.split("/")

        if path_starts_at_root:
            path.insert(0, '$')

        if path:
            path = [
                part
                for part in path
                if bool(part)
            ]

        self.__where = where
        self.__origin = origin
        self.__path = path
        self.__name = name

        if associated_fields is None:
            associated_fields = list()

        self.__associated_fields = associated_fields
        self.__datatype = datatype.lower() if datatype is not None else None

    def get_column_types(self) -> typing.Dict[str, typing.Union[typing.Dict[str, typing.Any], typing.List[str]]]:
        """
        Gets a list of columns and their required parsing types

        This should only be necessary for constructors that require extra notification for fields, such as pandas

        Returns:
            A dictionary mapping columns to their parsing types and an optional list of columns that are dates
        """
        column_options = dict()

        if self.__datatype in ["datetime", "date"]:
            column_options['parse_dates'] = [self.__name]
        else:
            dtype = util.type_name_to_dtype(self.__datatype)

            if dtype is not None:
                column_options['dtype'] = {self.__name: dtype}

        for index in self.associated_fields:
            if index.datatype in ["datetime", "date"]:
                if 'parse_dates' not in column_options:
                    column_options['parse_dates'] = list()

                if index.name not in column_options['parse_dates']:
                    column_options['parse_dates'].append(index.name)
            else:
                dtype = util.type_name_to_dtype(index.datatype)

                if dtype is not None:
                    if 'dtype' not in column_options:
                        column_options['dtype'] = dict()

                    column_options['dtype'][index.name] = dtype

        return column_options

    def to_datatype(self, value):
        """
        Attempt to convert the given value to the required datatype

        Args:
            value: The value to convert

        Returns:
            The converted value, if specified
        """
        if not self.__datatype:
            return value

        datatype = self.__datatype.lower()

        if datatype in ("datetime", "date", "time"):
            raw_datetime = parse_date(value)

            if datatype == 'date':
                return raw_datetime.date()
            elif datatype == 'time':
                return raw_datetime.time()

            return raw_datetime

        if datatype in ('str', 'string', 'word', 'id', 'identifier'):
            return str(value)

        if datatype in ('int', 'integer') and str(value).isdigit():
            return int(value)

        if datatype in ('float', 'double', 'number') and util.str_is_float(value):
            return float(value)

        if datatype in ('day',):
            return util.Day(value)

        return value

    @property
    def where(self) -> str:
        """
        Where the value may be found (Dict key? Dict value? Column?)
        """
        return self.__where

    @property
    def origin(self) -> typing.Optional[typing.Sequence[str]]:
        """
        The path from which to look

        The value should be `""` or `"/"` if searching from the root.
        """
        return self.__origin

    @property
    def path(self) -> typing.Optional[typing.Sequence[str]]:
        """
        The path from which to look from the origin
        """
        return self.__path

    @property
    def name(self) -> str:
        return self.__name

    @property
    def associated_fields(self) -> typing.Sequence[AssociatedField]:
        """
        Additional values to retrieve with selected values
        """
        return self.__associated_fields

    def __str__(self) -> str:
        description = f"{self.__name} => {self.__where}"

        if self.__path:
            description += f": {os.linesep.join(self.__path)}"

        if self.__associated_fields:
            description += f", indexed by [{','.join([str(field) for field in self.__associated_fields])}]"

        return description


class ThresholdApplicationRules(Specification):
    """
    Added rules for how thresholds should be applied
    """

    __slots__ = ['__threshold_field', '__observation_field', '__prediction_field']

    def validate(self) -> typing.Sequence[str]:
        messages = list()

        return messages

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        pass

    def __init__(
        self,
        threshold_field: AssociatedField,
        observation_field: AssociatedField = None,
        prediction_field: AssociatedField = None,
        properties: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        super().__init__(properties=properties, **kwargs)
        self.__threshold_field = threshold_field
        self.__observation_field = observation_field
        self.__prediction_field = prediction_field

    @property
    def threshold_field(self) -> AssociatedField:
        return self.__threshold_field

    @property
    def observation_field(self) -> typing.Optional[AssociatedField]:
        return self.__observation_field

    @property
    def prediction_field(self) -> typing.Optional[AssociatedField]:
        return self.__prediction_field

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        representation = f"The threshold built around {self.__threshold_field}"

        if self.__observation_field and self.__prediction_field:
            representation += f" is applied to the observations aligned by {self.__observation_field} " \
                              f"and the predictions aligned by {self.__prediction_field}"
        elif self.__observation_field:
            representation += f" is applied to the observations aligned by {self.__observation_field}"
        else:
            representation += f" is applied to the predictions aligned by {self.__prediction_field}"

        return representation


class LocationSpecification(Specification):
    """
    A specification for where location data should be found
    """

    def validate(self) -> typing.Sequence[str]:
        return list()

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "identify": self.__identify,
            "from_field": self.__from_field,
            "pattern": self.__pattern,
            "ids": self.__ids
        }

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ["__identify", "__from_field", "__pattern", "__ids"]

    def __init__(
        self,
        identify: bool = None,
        from_field: str = None,
        pattern: typing.Union[str, typing.Sequence[str]] = None,
        ids: typing.List[str] = None,
        properties: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        super().__init__(properties, **kwargs)

        if isinstance(ids, str):
            ids = list(ids)
        elif ids is None:
            ids = list()

        if identify and not (from_field or pattern or ids):
            raise ValueError(
                "A from_field, a pattern, or a list of ids are required if locations are supposed to be identified"
            )

        if pattern and not from_field:
            raise ValueError(
                "A from_field is required if a location is to be found from a pattern"
            )
        elif from_field and ids:
            raise ValueError(
                "Locations may be discovered from a static list or a field, but not both"
            )

        if from_field or ids:
            identify = True

        if identify is None:
            identify = False

        if from_field != 'filename' and isinstance(pattern, str):
            pattern_starts_at_root = pattern.startswith("/")
            pattern = pattern.split("/")

            if pattern_starts_at_root:
                pattern.insert(0, "$")

        self.__identify = identify
        self.__from_field = from_field
        self.__pattern = pattern
        self.__ids = ids

    @property
    def ids(self) -> typing.List[str]:
        """
        A list of specific ids to use for locations
        """
        return self.__ids

    @property
    def from_field(self) -> str:
        """
        A field from which to retrieve location names from a source

        This would be where you'd indicate that the location name came from the filename, for example
        """
        return self.__from_field

    @property
    def pattern(self) -> typing.Sequence[str]:
        """
        An optional regex for how to retrieve the name

        If the data are in files like `cat-67.json`, a regex like `^[A-Za-z]+-\d+` would indicate that the name
        should be interpreted as `cat-67` and not `cat-67.json`
        """
        return self.__pattern

    @property
    def should_identify(self) -> bool:
        """
        Whether locations should even be attempted to be identified

        Location identification isn't really necessary for single location evaluations, for example
        """
        return self.__identify

    def __str__(self) -> str:
        if self.__from_field and self.__pattern:
            return f"Identify locations matching '{self.__pattern}' from the '{self.__from_field}'"
        elif self.__from_field:
            return f"Identify locations from the '{self.__from_field}'"
        elif self.__ids:
            return f"Use the ids with the names: {', '.join(self.__ids)}"
        return "Don't identify locations"


class DataSourceSpecification(LoaderSpecification):
    """
    Specification for where to get the actual data for evaluation
    """

    def validate(self) -> typing.Sequence[str]:
        return list()

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "name": self.__name,
            "value_selectors": [selector.to_dict() for selector in self.__value_selectors],
            "backend": self._backend.to_dict(),
            "locations": self.__locations.to_dict(),
            "field_mapping": [mapping.to_dict() for mapping in self.__field_mapping],
            "unit": self.__unit.to_dict(),
            "x_axis": self.__x_axis
        }

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ["__name", "__value_field", "__locations", "__field_mapping", "__value_selectors", "__unit", "__x_axis"]

    def __init__(
        self,
        value_field: str,
        backend: BackendSpecification,
        value_selectors: typing.Sequence[ValueSelector],
        unit: UnitDefinition,
        name: str = None,
        x_axis: str = None,
        locations: LocationSpecification = None,
        field_mapping: typing.List[FieldMappingSpecification] = None,
        properties: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        super().__init__(properties, **kwargs)
        self._backend = backend
        self.__name = name if name else value_field
        self.__value_field = value_field
        self.__locations = locations if locations else LocationSpecification(identify=False)
        self.__field_mapping = field_mapping if field_mapping else list()
        self.__value_selectors = value_selectors
        self.__unit = unit
        self.__x_axis = x_axis or "value_date"

    @property
    def name(self) -> str:
        return self.__name

    @property
    def value_field(self) -> str:
        return self.__value_field

    @property
    def backend(self) -> BackendSpecification:
        return self._backend

    @property
    def locations(self) -> LocationSpecification:
        return self.__locations

    @property
    def field_mapping(self) -> typing.List[FieldMappingSpecification]:
        return [mapping for mapping in self.__field_mapping]

    @property
    def value_selectors(self) -> typing.Sequence[ValueSelector]:
        return [selector for selector in self.__value_selectors]

    @property
    def field_names(self) -> typing.Sequence[str]:
        names: typing.List[str] = list()

        return names

    @property
    def unit(self) -> UnitDefinition:
        return self.__unit

    @property
    def x_axis(self) -> str:
        return self.__x_axis

    def get_column_options(self) -> typing.Dict[str, typing.Union[typing.Dict[str, typing.Any], typing.List[str]]]:
        """
        Gets options that may be required for loading data into a table

        Returns:

        """
        options = dict()

        for selector in self.__value_selectors:
            selector_options = selector.get_column_types()

            for key, value in selector_options.items():
                if key not in options:
                    options[key] = value
                elif isinstance(options[key], dict):
                    options[key].update(value)
                elif common.is_sequence_type(options[key]):
                    for entry in value:
                        if entry not in options[key]:
                            options[key].append(entry)

        return options

    def __str__(self) -> str:
        return f"{self.__name} ({str(self._backend)})"


class CrosswalkSpecification(LoaderSpecification):
    """
    Specifies how locations in the observations should be linked to locations in the predictions
    """

    def validate(self) -> typing.Sequence[str]:
        return list()

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "backend": self._backend.to_dict(),
            "entity_path": self.entity_path,
            "field": self.__field.to_dict(),
            "prediction_field_name": self.__prediction_field_name,
            "observation_field_name": self.__observation_field_name
        }

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ['__origin', "__field", '__prediction_field_name', '__observation_field_name']

    def __init__(
        self,
        backend: BackendSpecification,
        field: ValueSelector,
        observation_field_name: str,
        prediction_field_name: str = None,
        origin: typing.Union[str, typing.Sequence[str]] = None,
        properties: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        super().__init__(properties, **kwargs)
        if origin is None:
            origin = "$"

        self._backend = backend
        self.__origin = origin.split(".") if isinstance(origin, str) else origin
        self.__field = field
        self.__observation_field_name = observation_field_name
        self.__prediction_field_name = prediction_field_name if prediction_field_name else observation_field_name

    @property
    def backend(self) -> BackendSpecification:
        return self._backend

    @property
    def field(self) -> ValueSelector:
        return self.__field

    @property
    def prediction_field_name(self) -> str:
        return self.__prediction_field_name

    @property
    def observation_field_name(self) -> str:
        return self.__observation_field_name

    @property
    def entity_path(self) -> typing.Sequence[str]:
        return self.__origin

    def __str__(self) -> str:
        return f"Crosswalk from: {str(self._backend)} with observed values from {str(self.__field)}"


class MetricSpecification(Specification):
    def validate(self) -> typing.Sequence[str]:
        return list()

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "name": self.__name,
            "weight": self.__weight
        }

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ["__name", "__weight"]

    def __init__(
        self,
        name: str,
        weight: float,
        properties: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        super().__init__(properties, **kwargs)

        self.__name = name
        self.__weight = weight

    @property
    def name(self) -> str:
        return self.__name

    @property
    def weight(self) -> float:
        return self.__weight

    def __str__(self) -> str:
        description = f"{self.__name} = {self.__weight}"

        if self.__properties:
            description += f" ({str(self.__properties)}"")"

        return description


class SchemeSpecification(Specification):
    def validate(self) -> typing.Sequence[str]:
        messages = list()

        for metric in self.__metrics:
            messages.extend(metric.validate())

        return messages

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "metrics": [metric.to_dict() for metric in self.__metrics]
        }

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ["__metrics"]

    def __init__(
        self,
        metrics: typing.Sequence[MetricSpecification],
        properties: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        super().__init__(properties, **kwargs)

        self.__metrics = metrics

    @property
    def metric_functions(self) -> typing.Sequence[MetricSpecification]:
        return [metric for metric in self.__metrics]

    @property
    def total_weight(self) -> float:
        return sum([metric.weight for metric in self.__metrics])

    def generate_scheme(self, communicators: metrics.CommunicatorGroup = None) -> metrics.ScoringScheme:
        generated_metrics: typing.List[metrics.Metric] = [
            metric_functions.get_metric(metric.name, metric.weight)
            for metric in self.__metrics
        ]
        return metrics.ScoringScheme(
            metrics=generated_metrics,
            communicators=communicators
        )

    def __str__(self) -> str:
        details = {
            "metrics": [str(metric) for metric in self.__metrics],
        }

        if self.__properties:
            details["properties"] = self.__properties

        return str(details)


class ThresholdSpecification(LoaderSpecification):
    def validate(self) -> typing.Sequence[str]:
        messages = list()

        messages.extend(self._backend.validate())
        messages.extend(self.__locations.validate())

        if len(self.__definitions) == 0:
            messages.append("There are no threshold definitions defined within a threshold specification")

        for definition in self.__definitions:
            messages.extend(definition.validate())

        return messages

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "backend": self._backend.to_dict(),
            "locations": self.__locations.to_dict(),
            "origin": self.__origin,
            "definitions": [definition.to_dict() for definition in self.__definitions],
            "application_rules": self.__application_rules.to_dict()
        }

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ["__locations", "__definitions", "__origin", "__application_rules"]

    def __init__(
        self,
        backend: BackendSpecification,
        definitions: typing.Sequence[ThresholdDefinition],
        locations: LocationSpecification = None,
        application_rules: ThresholdApplicationRules = None,
        properties: typing.Dict[str, typing.Any] = None,
        origin: typing.Union[str, typing.Sequence[str]] = None,
        **kwargs
    ):
        super().__init__(properties, **kwargs)

        self._backend = backend
        self.__definitions = definitions
        self.__locations = locations
        self.__application_rules = application_rules

        origin_starts_at_root = False

        if isinstance(origin, str):
            origin_starts_at_root = origin.startswith("/")
            origin = origin.split("/")
        elif isinstance(origin, bytes):
            origin = origin.decode()
            origin_starts_at_root = origin.startswith("/")
            origin = origin.split("/")
        elif not origin:
            origin = ["$"]

        if origin_starts_at_root and origin[0] != '$':
            origin.insert(0, "$")

        self.__origin = origin

    @property
    def backend(self) -> BackendSpecification:
        return self._backend

    @property
    def definitions(self) -> typing.Sequence[ThresholdDefinition]:
        return self.__definitions

    @property
    def locations(self) -> typing.Optional[LocationSpecification]:
        return self.__locations

    @property
    def origin(self) -> typing.Optional[typing.Sequence[str]]:
        return self.__origin

    @property
    def application_rules(self) -> ThresholdApplicationRules:
        return self.__application_rules

    @property
    def total_weight(self) -> float:
        """
        The weight of all defined thresholds
        """
        return sum([definition.weight for definition in self.__definitions])

    def __contains__(self, definition_name) -> bool:
        matching_definitions = [
            definition
            for definition in self.__definitions
            if definition.name.lower() == definition_name.lower()
        ]

        if matching_definitions:
            return True

        matching_definitions = [
            definition
            for definition in self.__definitions
            if definition.field[-1].lower() == definition_name.lower()
        ]

        if matching_definitions:
            return True

        return False

    def __getitem__(self, definition_name) -> typing.Optional[ThresholdDefinition]:
        matching_definitions = [
            definition
            for definition in self.__definitions
            if definition.name.lower() == definition_name.lower()
        ]

        if matching_definitions:
            return matching_definitions[0]

        matching_definitions = [
            definition
            for definition in self.__definitions
            if definition.field[-1].lower() == definition_name.lower()
        ]

        if matching_definitions:
            return matching_definitions[0]

        return None


class EvaluationSpecification(Specification):
    def validate(self) -> typing.Sequence[str]:
        messages = list()

        for observation_source in self.__observations:
            messages.extend(observation_source.validate())

        for prediction_source in self.__predictions:
            messages.extend(prediction_source.validate())

        for crosswalk_source in self.__crosswalks:
            messages.extend(crosswalk_source.validate())

        for threshold_source in self.__thresholds:
            messages.extend(threshold_source.validate())

        messages.extend(self.__scheme.validate())

        return messages

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "observations": [specification.to_dict() for specification in self.__observations],
            "predictions": [specification.to_dict() for specification in self.__predictions],
            "crosswalks": [crosswalk.to_dict() for crosswalk in self.__crosswalks],
            "thresholds": [thresholds.to_dict() for thresholds in self.__thresholds],
            "scheme": self.__scheme.to_dict()
        }

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ["__observations", "__predictions", "__crosswalks", "__thresholds", "__scheme"]

    def __init__(
        self,
        observations: typing.Sequence[DataSourceSpecification],
        predictions: typing.Sequence[DataSourceSpecification],
        crosswalks: typing.Sequence[CrosswalkSpecification],
        thresholds: typing.Sequence[ThresholdSpecification],
        scheme: SchemeSpecification,
        properties: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        super().__init__(properties, **kwargs)

        self.__observations = observations
        self.__predictions = predictions
        self.__crosswalks = crosswalks
        self.__thresholds = thresholds
        self.__scheme = scheme

    @property
    def observations(self) -> typing.Sequence[DataSourceSpecification]:
        """
        All specifications for where observation data should come from
        """
        return self.__observations

    @property
    def predictions(self) -> typing.Sequence[DataSourceSpecification]:
        """
        All specifications for where prediction data should come from
        """
        return self.__predictions

    @property
    def crosswalks(self) -> typing.Sequence[CrosswalkSpecification]:
        """
        All specifcations for where to get data detailing how to tie observation locations to prediction locations
        """
        return self.__crosswalks

    @property
    def scheme(self) -> SchemeSpecification:
        """
        The specification for what metrics to apply and how they relate to one another
        """
        return self.__scheme

    @property
    def thresholds(self) -> typing.Sequence[ThresholdSpecification]:
        """
        All specifications for what thresholds should be applied to observations and predictions
        """
        return self.__thresholds

    @property
    def weight_per_location(self) -> float:
        """
        The maximum value each location can have
        """
        total_threshold_weight = sum([threshold.total_weight for threshold in self.__thresholds])

        return total_threshold_weight + self.__scheme.total_weight


class EvaluationResults:
    def __init__(
        self,
        instructions: EvaluationSpecification,
        raw_results: typing.Dict[typing.Tuple[str, str], metrics.MetricResults]
    ):
        self._instructions = instructions
        self._original_results = raw_results.copy()
        self._location_map: typing.Dict[str, typing.Dict[str, metrics.MetricResults]] = collections.defaultdict(dict)

        self._total = sum(
            [
                metric_result.scaled_value
                for metric_result in raw_results.values()
                if not numpy.isnan(metric_result.scaled_value)
            ]
        )

        self._maximum_value = sum(
            [
                metric_result.weight
                for metric_result in raw_results.values()
                if not numpy.isnan(metric_result.weight)
            ]
        )

        for (observed_location, predicted_location), metric_result in self._original_results.items():
            self._location_map[observed_location][predicted_location] = metric_result
            self._location_map[predicted_location][observed_location] = metric_result

    def __getitem__(self, item: str) -> typing.Dict[str, metrics.MetricResults]:
        return self._location_map[item]

    def __iter__(self):
        return iter(self._original_results.items())

    def __len__(self):
        return len(self._original_results)

    def __str__(self):
        locations_in_calculations = [
            f"{observation_location} vs. {prediction_location}"
            for (observation_location, prediction_location) in self._original_results.keys()
        ]
        return f"{', '.join(locations_in_calculations)}: {self._total}"

    def to_frames(self, include_metadata: bool = None) -> typing.Dict[str, pandas.DataFrame]:
        """
        Converts two or more dimensional results into a DataFrame

        NOTE: Scalar values, such as the final results, will not be included

        Returns:
            A DataFrame describing the results of all scores, across all thresholds, across all location pairings
        """
        if include_metadata is None:
            include_metadata = False

        frames: typing.Dict[str, pandas.DataFrame] = dict()

        for (observation_location, prediction_location), results in self._original_results.items():
            results_frame = results.to_dataframe(include_metadata=include_metadata)
            results_frame['observed_location'] = observation_location
            results_frame['predicted_location'] = prediction_location
            frames[f"{observation_location} vs. {prediction_location}"] = results_frame

        return frames

    @property
    def performance(self) -> float:
        """
        Returns an aggregate value demonstrating the performance of each location within the evaluation

            n
            Σ   self._original_results.values()[i].scaled_value
          i = 0
        """
        return self._total / self._maximum_value if self._maximum_value else 0.0

    def to_dict(self, include_specification: bool = None) -> typing.Dict[str, typing.Any]:
        """
        Converts the results into a dictionary

        Σ

        Args:
            include_specification: Whether to include the specifications for how to conduct the evaluation

        Returns:
            The evaluation results in the form of a nested dictionary
        """
        data = dict()

        data['total'] = self._total
        data['performance'] = self.performance
        data['grade'] = self.grade
        data['max_possible_total'] = self.max_possible_value
        data['mean'] = self.mean
        data['median'] = self.median
        data['standard_deviation'] = self.standard_deviation

        data['results'] = list()

        include_specification = bool(include_specification)

        if include_specification:
            data['specification'] = self._instructions.to_dict()

        included_metrics: typing.List[dict] = list()

        for result in self._original_results.values():  # type: metrics.MetricResults
            for _, scores in result:
                for score in scores:
                    if not [metric for metric in included_metrics if metric['name'] == score.metric.name]:
                        included_metrics.append(
                            {
                                "name": score.metric.name,
                                "weight": score.metric.weight,
                                "description": score.metric.get_descriptions()
                            }
                        )

        data['metrics'] = included_metrics

        for (observation_location, prediction_location), results in self._original_results.items():
            result_data = {
                "observation_location": observation_location,
                "prediction_location": prediction_location,
            }

            result_data.update(results.to_dict())

            data['results'].append(result_data)

        return data

    @property
    def value(self) -> float:
        """
        The resulting value for the evaluation over all location pairings
        """
        return self._total

    @property
    def instructions(self) -> EvaluationSpecification:
        """
        The specifications that told the system how to evaluate
        """
        return self._instructions

    @property
    def max_possible_value(self) -> float:
        """
        The highest possible value that can be achieved with the given instructions
        """
        return self._maximum_value

    @property
    def grade(self) -> float:
        """
        The total weighted grade percentage result across all location pairings. Scales from 0.0 to 100.0
        """
        return common.truncate(self.performance * 100.0, 2)

    @property
    def mean(self) -> float:
        """
        The mean total value across all evaluated location pairings
        """
        return float(
            numpy.mean(
                [
                    result.scaled_value / result.weight
                    for result in self._original_results.values()
                ]
            )
        )

    @property
    def median(self) -> float:
        """
        The median total value across all evaluated location pairings
        """
        return float(
            numpy.median(
                [
                    result.scaled_value / result.weight
                    for result in self._original_results.values()
                ]
            )
        )

    @property
    def standard_deviation(self) -> float:
        """
        The standard deviation for result values across all location pairings
        """
        return float(
            numpy.std(
                [
                    result.scaled_value / result.weight
                    for result in self._original_results.values()
                ]
            )
        )
