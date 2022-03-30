import os
import typing
import abc
import json
import inspect
import logging
import io

import numpy

from dateutil.parser import parse as parse_date

from .. import util

logging.basicConfig(
    filename='evaluation.log',
    level=logging.getLevelName(os.environ.get('METRIC_LOG_LEVEL', os.environ.get("DEFAULT_LOG_LEVEL", "DEBUG"))),
    format=os.environ.get("LOG_FORMAT", "%(asctime)s,%(msecs)d %(levelname)s: %(message)s"),
    datefmt=os.environ.get("LOG_DATEFMT", "%H:%M:%S")
)


def get_specifications() -> typing.List[typing.Type]:
    """
    Returns:
        All implemented specifications
    """
    return [
        cls
        for cls in Specification.__subclasses__()
        if not inspect.isabstract(cls)
    ]


def value_matches_parameter_type(value, parameter: typing.Union[inspect.Parameter, typing.Type]) -> bool:
    """
    Checks to see if the given value matches that of the passed in parameter

    Since a parameter without an annotation is interpreted as `typing.Any`, `True` is returned if not type is indicated

    Args:
        value: The value to check
        parameter: The parameter to check

    Returns:
        Whether or not the given value conforms to the parameter
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

    if parameter_type in get_specifications():
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


def create_class(cls, data, decoder: json.JSONDecoder = None):
    """
    Dynamically creates a class based on the type of class and the given parameters

    Args:
        cls: The type of class to construct
        data: The data that provides construction arguments
        decoder: An optional json decoder that will help deserialize any json inputs

    Returns:
        An instance of the given `cls`
    """
    if isinstance(data, cls):
        return data

    if hasattr(data, "read"):
        data: typing.Dict[str, typing.Any] = json.load(data, cls=decoder)

    if isinstance(data, bytes):
        data: str = data.decode()

    if isinstance(data, str):
        data: typing.Dict[str, typing.Any] = json.loads(data, cls=decoder)

    # If data is a list of lists or objects, send each back to this function and return a list instead of a single value
    if isinstance(data, typing.Sequence):
        return [
            create_class(cls, input_value, decoder)
            for input_value in data
        ]

    if hasattr(data, "__dict__"):
        return cls(
            **data.__dict__
        )
    if hasattr(data, "__slots__"):
        return cls(
            **{key: getattr(data, key) for key in data.__slots__}
        )

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

        arguments['properties'].update({
            key: value
            for key, value in data.items()
            if key not in arguments
        })

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
        instance = create_class(cls, data, decoder)

        messages = list()

        if isinstance(instance, typing.Sequence):
            for member in instance:
                messages.extend(member.validate())
        else:
            messages.extend(instance.validate())

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

    def to_json(self, buffer: io.IOBase = None) -> typing.Optional[typing.Union[str, io.IOBase]]:
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
        return str({
            key.replace("__", ""): getattr(self, key)
            for key in self.__slots__
        })


class UnitDefinition(Specification):
    """
    A definition of what a measurement unit is or where to find it
    """
    def validate(self) -> typing.Sequence[str]:
        messages = list()

        if not self.__path and not self.__field:
            messages.append("Unit definition is missing both a field and a path; not unit data will be found.")
        elif self.__path and self.__field:
            messages.append("A unit definition may only have a field or a path defined, not both.")

        return messages

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        data = dict()

        if self.__field:
            data["field"] = self.__field
        else:
            data['path'] = self.__path

        return data

    __slots__ = ["__field", "__path"]

    def __init__(
            self,
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

    @property
    def field(self) -> typing.Optional[str]:
        return self.__field

    @property
    def path(self) -> typing.Optional[typing.Sequence[str]]:
        return self.__path

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
            "unit": self.__unit,
            "weight": self.__weight,
            "properties": self.__properties
        }

    __slots__ = ["__name", "__field", "__weight", "__unit"]

    def __init__(
            self,
            name: typing.Union[str, bytes],
            field: typing.Union[str, bytes, typing.Sequence[str]],
            weight: float,
            unit: UnitDefinition,
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
        return str({
            "name": self.__name,
            "weight": self.__weight,
            "field": self.__field
        })


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

            return raw_datetime

        if datatype in ('float', 'double', 'number') and str(value).isnumeric():
            return float(value)

        if datatype in ('int', 'integer') and str(value).isdigit():
            return int(value)

        if datatype in ('str', 'string', 'word', 'id', 'identifier'):
            return str(value)

        return value

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

        for index in self.index:
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
    def index(self) -> typing.Sequence[AssociatedField]:
        """
        Additional values to retrieve with selected values
        """
        return self.__associated_fields

    def __str__(self) -> str:
        description = f"{self.__name} => {self.__where}"

        if self.__path:
            description += f": {self.__path.join(os.linesep)}"

        if self.__associated_fields:
            description += f", indexed by [{','.join(self.__associated_fields)}]"

        return description


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


class DataSourceSpecification(Specification):
    """
    Specification for where to get the actual data for evaluation
    """
    def validate(self) -> typing.Sequence[str]:
        return list()

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "name": self.__name,
            "value_selectors": [selector.to_dict() for selector in self.__value_selectors],
            "backend": self.__backend.to_dict(),
            "locations": self.__locations.to_dict(),
            "field_mapping": [mapping.to_dict() for mapping in self.__field_mapping]
        }

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ["__name", "__backend", "__locations", "__field_mapping", "__value_selectors"]

    def __init__(
            self,
            backend: BackendSpecification,
            value_selectors: typing.Sequence[ValueSelector],
            name: str = None,
            locations: LocationSpecification = None,
            field_mapping: typing.List[FieldMappingSpecification] = None,
            properties: typing.Dict[str, typing.Any] = None,
            **kwargs
    ):
        super().__init__(properties, **kwargs)
        self.__backend = backend
        self.__name = name if name else str(backend)
        self.__locations = locations if locations else LocationSpecification(identify=False)
        self.__field_mapping = field_mapping if field_mapping else list()
        self.__value_selectors = value_selectors

    @property
    def name(self) -> str:
        return self.__name

    @property
    def backend(self) -> BackendSpecification:
        return self.__backend

    @property
    def locations(self) -> LocationSpecification:
        return self.__locations

    @property
    def field_mapping(self) -> typing.List[FieldMappingSpecification]:
        return [mapping for mapping in self.__field_mapping]

    @property
    def value_selectors(self) -> typing.Sequence[ValueSelector]:
        return [selector for selector in self.__value_selectors]

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
                elif util.is_arraytype(options[key]):
                    for entry in value:
                        if entry not in options[key]:
                            options[key].append(entry)

        return options

    def __str__(self) -> str:
        return f"{self.__name} ({str(self.__backend)})"


class CrosswalkSpecification(Specification):
    """
    Specifies how locations in the observations should be linked to locations in the predictions
    """
    def validate(self) -> typing.Sequence[str]:
        return list()

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "backend": self.__backend.to_dict(),
            "entity_path": self.entity_path,
            "fields": self.__fields.to_dict()
        }

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ['__backend', '__origin', "__fields"]

    def __init__(
            self,
            backend: BackendSpecification,
            fields: ValueSelector,
            origin: typing.Union[str, typing.Sequence[str]] = None,
            properties: typing.Dict[str, typing.Any] = None,
            **kwargs
    ):
        super().__init__(properties, **kwargs)
        if origin is None:
            origin = "$"

        self.__backend = backend
        self.__origin = origin.split(".") if isinstance(origin, str) else origin
        self.__fields = fields

    @property
    def backend(self) -> BackendSpecification:
        return self.__backend

    @property
    def fields(self) -> ValueSelector:
        return self.__fields

    @property
    def prediction_field(self) -> ValueSelector:
        return self.__prediction_field

    @property
    def entity_path(self) -> typing.Sequence[str]:
        return self.__origin

    def __str__(self) -> str:
        return f"Crosswalk from: {self.__backend} with observed values from " \
               f"{self.__fields} and predicted values from " \
               f"{self.__prediction_field} off of {os.pathsep.join(self.__origin)}"


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
    def metrics(self) -> typing.Sequence[MetricSpecification]:
        return [metric for metric in self.__metrics]

    def __str__(self) -> str:
        details = {
            "metrics": [str(metric) for metric in self.__metrics],
        }

        if self.__properties:
            details["properties"] = self.__properties

        return str(details)


class ThresholdSpecification(Specification):
    def validate(self) -> typing.Sequence[str]:
        messages = list()

        messages.extend(self.__backend.validate())
        messages.extend(self.__locations.validate())

        for definition in self.__definitions:
            messages.extend(definition.validate())

        return messages

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "backend": self.__backend.to_dict(),
            "locations": self.__locations.to_dict(),
            "definitions": [definition.to_dict() for definition in self.__definitions]
        }

        if self.__properties:
            dictionary['properties'] = self.__properties

        return dictionary

    __slots__ = ["__backend", "__locations", "__definitions", "__origin"]

    def __init__(
            self,
            backend: BackendSpecification,
            definitions: typing.Sequence[ThresholdDefinition],
            locations: LocationSpecification = None,
            properties: typing.Dict[str, typing.Any] = None,
            origin: typing.Union[str, typing.Sequence[str]] = None,
            **kwargs
    ):
        super().__init__(properties, **kwargs)

        self.__backend = backend
        self.__definitions = definitions
        self.__locations = locations

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
        return self.__backend

    @property
    def definitions(self) -> typing.Sequence[ThresholdDefinition]:
        return self.__definitions

    @property
    def locations(self) -> typing.Optional[LocationSpecification]:
        return self.__locations

    @property
    def origin(self) -> typing.Optional[typing.Sequence[str]]:
        return self.__origin


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

        messages.extend(self.__scheme)

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
        return self.__observations

    @property
    def predictions(self) -> typing.Sequence[DataSourceSpecification]:
        return self.__predictions

    @property
    def crosswalks(self) -> typing.Sequence[CrosswalkSpecification]:
        return self.__crosswalks

    @property
    def scheme(self) -> SchemeSpecification:
        return self.__scheme

    @property
    def thresholds(self) -> typing.Sequence[ThresholdSpecification]:
        return self.__thresholds
