"""
Defines the core classes for specifications and how to create them
"""
import typing
import json
import logging
import inspect
import abc
import os

import dmod.core.common as common
from dmod.core.common import get_subclasses
from dmod.core.common import humanize_text

from .template import TemplateManager

from .. import util

from .helpers import is_a_value

_CLASS_TYPE = typing.TypeVar("_CLASS_TYPE")


def get_constructor_parameters(cls: typing.Type[_CLASS_TYPE]) -> typing.Mapping[str, inspect.Parameter]:
    """
    Get a mapping for every constructor in a classes MRO chain

    Args:
        cls: The class whose entire MRO chain to get parameters for
    """
    try:
        classes = inspect.getmro(cls)
    except:
        classes = [cls]

    total_parameters: typing.List[typing.Mapping[str, inspect.Parameter]] = list()

    for constructor in classes:
        try:
            parameters = inspect.signature(constructor).parameters

            total_parameters.append(parameters)

            kwarg_parameter = common.find(
                parameters.values(),
                lambda constructor_parameter: constructor_parameter.kind == constructor_parameter.VAR_KEYWORD
            )

            if kwarg_parameter is None:
                # If a signature lacks a parameter for key-value pairs, all possible  arguments have passed
                # through. Break the loop and carry on in order to avoid a situation where a value might be given for
                # a parent class constructor but there is no way to get that parameter to the parameter constructor
                # through the class of interest's constructor
                break
        except:
            # Go ahead and try to use the next constructor if this call failed
            pass

    constructor_parameters: typing.Dict[str, inspect.Parameter] = dict()

    # Loop through the constructor parameters of each encountered class in the MRO chain and add firmly
    # named parameters to the final mapping of string to parameter
    for parameters in total_parameters:
        for parameter_key, parameter in parameters.items():
            if parameter.kind not in (parameter.VAR_KEYWORD, parameter.VAR_POSITIONAL):
                constructor_parameters[parameter_key] = parameter

    return constructor_parameters


def create_class_instance(
    cls: typing.Type[_CLASS_TYPE],
    data,
    template_manager: TemplateManager = None,
    decoder_type: typing.Type[json.JSONDecoder] = None
) -> _CLASS_TYPE:
    """
    Dynamically creates a class based on the type of class and the given parameters

    Args:
        cls: The type of class to construct
        data: The data that provides construction arguments
        template_manager: A template manager that can help apply templates to generated classes
        decoder_type: An optional type of json decoder that will help deserialize any json inputs

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
                data: typing.Dict[str, typing.Any] = json.loads(data, cls=decoder_type)
            except json.JSONDecodeError:
                # If the string can't be interpreted as JSON, try to interpret in another way later.
                logging.error(
                    "Tried to interpret string data as json, but it wasn't valid. "
                    "Continuing with attempted parsing."
                )

    # If data is a list of lists or objects, send each back to this function and return a list instead of a single value
    if not isinstance(data, str) and isinstance(data, typing.Sequence):
        return [
            create_class_instance(cls, input_value, template_manager, decoder_type)
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
        treat_as_template_configuration = cls in get_subclasses(TemplatedSpecification) and "template_name" in data

        overlay = None

        if treat_as_template_configuration:
            overlay = {key: value for key, value in data.items()}
            template_name = data['template_name']

            data: dict = template_manager.get_template(cls.__name__, name=template_name, decoder_type=decoder_type)

        constructor_parameters = get_constructor_parameters(cls)

        for parameter in constructor_parameters.values():  # type: inspect.Parameter
            if parameter.kind == parameter.VAR_KEYWORD:
                continue

            try:
                value = data[parameter.name]

                value = convert_value(
                    value=value,
                    parameter=parameter,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

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

        instance = cls(**arguments)

        if overlay and isinstance(instance, TemplatedSpecification):
            instance.overlay_configuration(
                configuration=overlay,
                template_manager=template_manager,
                decoder_type=decoder_type
            )

        return instance

    raise ValueError(f"Type '{type(data)}' cannot be read as JSON")


class Specification(abc.ABC):
    """
    Instructions for how different aspects of an evaluation should work
    """
    __slots__ = ['__properties', "_name"]

    @classmethod
    def get_specification_type(cls) -> str:
        """
        Shortcut method for getting the name for the specification class
        """
        return cls.__name__

    @classmethod
    def get_specification_description(cls) -> str:
        """
        Get a human friendly name for this type of specification
        """
        return humanize_text(cls.__name__, exclude_phrases=['Specification'])

    @classmethod
    def create(
        cls,
        data: typing.Union[str, dict, typing.IO, bytes, typing.Sequence],
        template_manager: TemplateManager = None,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        """
        A factory for the given specification

        Args:
            data: Parameters used to instantiate the specification
            template_manager: A manager for any template specifications that can help apply template values
            decoder_type: an optional type of json decoder used to deserialize the specification

        Returns:
            An instance of the specified specification class
        """
        instance = create_class_instance(
            cls=cls,
            data=data,
            template_manager=template_manager,
            decoder_type=decoder_type
        )

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
    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        """
        Returns:
            Specification specific fields that will fit within a final serialized representation
        """
        fields = {
            "properties": self.properties.copy() if self.properties else dict()
        }

        if self.name:
            fields['name'] = self.name

        return fields

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        """
        Returns:
            The specification converted into a dictionary
        """
        dictionary = dict()

        if self.name:
            dictionary['name'] = self.name

        if self.properties:
            dictionary['properties'] = self.properties.copy()

        field_data = self.extract_fields()

        dictionary.update(field_data)

        return dictionary

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

    def __init__(
        self,
        name: str = None,
        properties: typing.Union[typing.Dict[str, typing.Any], str, bytes] = None,
        **kwargs
    ):
        self._name = name

        if properties is None:
            properties = dict()
        elif isinstance(properties, str):
            properties = json.loads(properties)
        elif isinstance(properties, bytes):
            properties = json.loads(properties.decode())

        properties.update(kwargs)

        self.__properties = properties

    @property
    def name(self) -> str:
        return self._name

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

    def identities_match(self, configuration: typing.Union[dict, "Specification"]) -> bool:
        configuration_is_class = isinstance(configuration, self.__class__)
        configuration_is_dict = isinstance(configuration, dict)

        if not (configuration_is_class or configuration_is_dict):
            return False

        if configuration_is_class:
            return self.name == configuration.name
        else:
            return self.name is not None and self.name == configuration.get("name")

    def __getitem__(self, key: str) -> typing.Any:
        return self.__properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.__properties

    @abc.abstractmethod
    def __eq__(self, other) -> bool:
        if other is None or not hasattr(other, "properties"):
            return False

        return self.properties == other.properties

    def __repr__(self) -> str:
        return str(
            {
                key.replace("__", ""): getattr(self, key, getattr(self, key.replace("__", "")))
                for key in self.__slots__
            }
        )


class TemplatedSpecification(Specification, abc.ABC):
    __slots__ = ["__template_name"]

    def __init__(self, template_name: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__template_name = template_name

        if not self.name and self.template_name:
            self._name = self.template_name

    @classmethod
    def from_template(
        cls,
        template_name: str,
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        template = template_manager.get_template(
            specification_type=cls.__name__,
            name=template_name,
            decoder_type=decoder_type
        )

        if not template:
            raise Exception(
                f"The '[{cls.__name__}] {template_name}' template is missing. "
                f"A {cls.__name__} cannot be built."
            )

        return cls(**template)

    @property
    def template_name(self) -> typing.Optional[str]:
        return self.__template_name

    def overlay_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if 'properties' in configuration and isinstance(configuration['properties'], typing.Mapping):
            self.__properties.update(
                configuration['properties']
            )

        self.apply_configuration(
            configuration=configuration,
            template_manager=template_manager,
            decoder_type=decoder_type
        )

    @abc.abstractmethod
    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        """
        Overlay configured values from another configuration onto this
        """
        pass


def convert_value(
    value: typing.Any,
    parameter: typing.Union[inspect.Parameter, typing.Type],
    template_manager: TemplateManager,
    decoder_type: typing.Type[json.JSONDecoder] = None
) -> typing.Any:
    """
    Attempts to convert a given value to the type expected by the parameter

    Args:
        value: The value to convert
        parameter: The function parameter that may or may not dictate what to cast the value as
        template_manager: The manager responsible for finding templating information
        decoder_type: An optional type of decoder to use when deserializing a template

    Returns:
        An attempted conversion if a parameter type is given; just the original value otherwise
    """
    if isinstance(parameter, inspect.Parameter):
        parameter_type: typing.Type = None if parameter.annotation == parameter.empty else parameter.annotation
    else:
        parameter_type: typing.Union[typing.Type, typing.Type[Specification], typing.Type[TemplatedSpecification]] = parameter

    if parameter_type is None:
        return value

    if parameter_type in common.get_subclasses(Specification):
        return parameter_type.create(
            data=value,
            template_manager=template_manager,
            decoder_type=decoder_type
        )

    if isinstance(value, str) and util.value_is_number(value) and util.type_is_number(parameter_type):
        return float(value)
    elif isinstance(value, bytes) and util.value_is_number(value) and util.type_is_number(parameter_type):
        return float(value.decode())
    elif not (isinstance(value, str) or isinstance(value, bytes)) and isinstance(value, typing.Sequence):
        expected_type = typing.get_args(parameter_type)
        converted_values = [
            convert_value(
                value=member,
                parameter=expected_type[0],
                template_manager=template_manager,
                decoder_type=decoder_type
            )
            for member in value
        ]
        return converted_values

    return value
