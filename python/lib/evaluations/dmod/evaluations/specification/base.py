"""
Defines the core classes for specifications and how to create them
"""
import typing
import json
import logging
import inspect
import abc
import os
import re
import traceback

import dmod.core.common as common
from dmod.core.common import get_subclasses
from dmod.core.common import humanize_text

from .template import TemplateManager

from .. import util

from .helpers import is_a_value

_CLASS_TYPE = typing.TypeVar("_CLASS_TYPE")

CLASS_MODULE_COLLECTION_PATTERN = re.compile("(?<=\[).+\.(?=.+\])")
"""
Pattern to find all portions of a complete class description prior to the class name from within a collection description

CLASS_MODULE_COLLECTION_PATTERN.sub('', "Sequence[dmod.evaluations.specification.threshold.ThresholdDefinition]") yields
Sequence[ThresholdDefinition]
"""

CLASS_MODULE_PATTERN = re.compile(".+\.(?=.+)")


def get_constructor_parameters(cls: typing.Type[_CLASS_TYPE]) -> typing.Mapping[str, inspect.Parameter]:
    """
    Get a mapping for every constructor in a classes MRO chain

    Example:
        >>> class A:
        >>>     def __init__(self, a: int):
        >>>         self.a = a
        >>> class B(A):
        >>>     def __init__(self, a: int, b: bool):
        >>>         super().__init__(a)
        >>>         self.b = b
        >>> class C(B):
        >>>     def __init__(self, c: str, **kwargs):
        >>>         super().__init__(**kwargs)
        >>>         self.c = c
        >>>
        >>> params: typing.Mapping[str, inspect.Parameter] = get_constructor_parameters(C)
        >>> for param, param_type in params.items():
        >>>     print(f"{param}: {param_type}")
        a: <a: int>
        b: <b: bool>
        c: <c: str>

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

            # A variable keyword parameter means that just about any key-value pair other than what is noted should
            # fly and that there may be variables that need to be covered further up the MRO chain
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
    # This is done in reverse order so that child variables aren't overwritten by their parents
    for parameters in reversed(total_parameters):
        for parameter_key, parameter in parameters.items():
            if parameter.kind not in (parameter.VAR_KEYWORD, parameter.VAR_POSITIONAL):
                constructor_parameters[parameter_key] = parameter

    return constructor_parameters


def create_class_instance(
    cls: typing.Type["Specification"],
    data,
    template_manager: TemplateManager = None,
    decoder_type: typing.Type[json.JSONDecoder] = None,
    messages: typing.List[str] = None,
    validate: bool = None
) -> typing.Optional["Specification"]:
    """
    Dynamically creates a class based on the type of class and the given parameters

    Args:
        cls: The type of class to construct
        data: The data that provides construction arguments
        template_manager: A template manager that can help apply templates to generated classes
        decoder_type: An optional type of json decoder that will help deserialize any json inputs
        messages: A container for any possible messages to use if errors are encountered
        validate: Indicates taht the system is just trying to see if items can be built - pass back messages instead of throwing them if true
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
    if not isinstance(data, (bytes, str, typing.Mapping)) and isinstance(data, typing.Iterable):
        sub_items: typing.List = list()

        # This data could be several instances of 'cls', so iterate through the data and try to
        for input_value in data:
            if is_a_value(input_value):
                try:
                    sub_item = create_class_instance(
                        cls=cls,
                        data=input_value,
                        template_manager=template_manager,
                        decoder_type=decoder_type,
                        messages=messages,
                        validate=validate
                    )

                    # A null sub_item indicates that construction failed. The reason for the failure should have
                    # been expressed within the messages collection, so all that needs to be done is adding any
                    # non-null items here so they may be validated against later
                    if sub_item is not None:
                        sub_items.append(sub_item)
                except Exception as exception:
                    # If it is determined that we WANT to encounter errors, record them and move on.
                    # Throw the error otherwise
                    if validate and messages is not None:
                        logging.error(traceback.format_exc())
                        messages.append(str(exception))
                    else:
                        raise

        return sub_items

    # If it doesn't have some sort of '__getitem__' or is a string, we can assume that this is a singular value
    # and we can just send that as a parameter
    if isinstance(data, str) or not hasattr(data, "__getitem__"):
        try:
            return cls(data)
        except Exception as exception:
            messages.append(str(exception))
            return None

    # Start to deconstruct the signature for the __init__ function for the class. We're going to look for
    # required parameters and make sure everything is present before calling the constructor
    constructor_signature: inspect.Signature = inspect.signature(cls)

    arguments: typing.Dict[str, typing.Any] = dict()

    # A required parameter is everything in the signature that doesn't have a default value and isn't a dynamic value,
    # like *args or **kwargs, both of which are optional in their own context.
    required_parameters = [
        parameter
        for parameter in constructor_signature.parameters.values()
        if parameter.default == parameter.empty
           and parameter.kind != parameter.VAR_KEYWORD
           and parameter.kind != parameter.VAR_POSITIONAL
    ]

    # Maintain a list of required parameters that aren't provided
    missing_parameters = list()

    if hasattr(data, "__getitem__") and not isinstance(data, typing.Sequence):
        # If it is determined that the object to construct supports templates and a template is defined, we want to
        # default all values to that of the template and override those values by what was given by the caller
        has_template_name = "template_name" in data or "template" in data
        has_multiple_templates = 'templates' in data and common.is_iterable_type(data['templates'])
        template_is_indicated = has_template_name or has_multiple_templates

        templates_are_supported = cls in get_subclasses(TemplatedSpecification)
        treat_as_template_configuration = templates_are_supported and template_is_indicated

        # We want to shift that values from the input into this overlay variable to be applied later if need be
        overlay = {key: value for key, value in data.items()} if treat_as_template_configuration else None

        # Start setting variable values to those of a template if the caller specified that it's needed
        if treat_as_template_configuration and has_multiple_templates:
            combined_template = dict()

            # Iterate through all defined templates and combine all into one template,
            # with the last templates taking precedence over the first
            for template_name in data['templates']:
                found_template = template_manager.get_template(
                    cls.__name__,
                    name=template_name,
                    decoder_type=decoder_type
                )

                if found_template is not None:
                    combined_template = common.merge_dictionaries(combined_template, found_template, expand=False)
                elif validate and messages is not None:
                    error_message = f"No template could be found with the name of '{template_name}'"
                    messages.append(error_message)

            data = combined_template
        elif treat_as_template_configuration:
            template_name = data['template_name'] if 'template_name' in data else data['template']

            # Find a template based on given information
            data: dict = template_manager.get_template(cls.__name__, name=template_name, decoder_type=decoder_type)

            error_message = None if data else f"No template could be found with a name of {template_name}"

            # record or throw an error if a template could not be found
            if error_message and validate and messages is not None:
                messages.append(error_message)
            elif error_message:
                raise ValueError(error_message)

        # Now get a list of all constructor parameters for this class
        constructor_parameters = get_constructor_parameters(cls)

        # Iterate through every parameter in the constructor parameters and fill out key-value pairs that will be
        # sent to the constructor
        for parameter in constructor_parameters.values():  # type: inspect.Parameter
            # kwargs are non-specific, so skip over this - a proper mapping won't be determined for this parameter
            if parameter.kind == parameter.VAR_KEYWORD:
                continue

            try:
                # Pick a name directly out of the data that matches the parameter
                if isinstance(data, typing.Mapping):
                    value = data[parameter.name]
                else:
                    value = getattr(data, parameter.name)

                # Attempt to convert the encountered value into the expected type
                value = convert_value(
                    value=value,
                    parameter=parameter,
                    template_manager=template_manager,
                    decoder_type=decoder_type,
                    messages=messages,
                    validate=validate
                )

                # A null value indicates that something went awry during construction. Avoiding this assignment
                # prevents extra validation steps from occurring, so it's added here. 'convert_value' should record
                # any possible issues.
                arguments[parameter.name] = value
            except (KeyError, AttributeError):
                # If the value could not be pulled off the input object but it wasn't required,
                # there is a default value that may be put in instead
                if parameter not in required_parameters:
                    arguments[parameter.name] = parameter.default
                else:
                    # A required parameter couldn't be found, so clean it up to make it more human readable and
                    # add it to the list of missing parameters
                    parameter_description = str(parameter)
                    parameter_description = CLASS_MODULE_COLLECTION_PATTERN.sub("", parameter_description)

                    missing_parameters.append(parameter_description)
            except TypeError:
                if treat_as_template_configuration and data is None and validate and messages:
                    message = f"There is not enough information aside from an invalid template name provided " \
                              f"to construct a(n) '{cls.get_specification_description()}'"
                    messages.append(message)
                    logging.error(message)
                else:
                    raise

        if missing_parameters:
            # This operation has errored if parameters are missing. Record it or throw an error when appropriate
            message = f"'{cls.get_specification_description()}' can't be constructed - " \
                      f"required parameters are missing: {', '.join(missing_parameters)}"

            # If the system is validating, we don't necessarily want to fail here, so record the issue and continue
            if validate and messages is not None:
                messages.append(message)
                logging.error(message)
            else:
                raise ValueError(message)
        else:
            if 'properties' not in arguments or arguments['properties'] is None:
                arguments['properties'] = dict()

            # Add all unaccounted for values from the input into a properties map so input data isn't
            # necessarily lost and anything that might need it may use it later
            arguments['properties'].update(
                {
                    key: value
                    for key, value in data.items()
                    if key not in arguments
                }
            )

            try:
                instance = cls(**arguments)
            except Exception as exception:
                # If an exception is encountered, record if validating, otherwise bubble up the error
                if validate and messages is not None:
                    logging.error(traceback.format_exc())
                    messages.append(str(exception))

                    # An instance couldn't be created, so return the None so operations may continue
                    return None
                else:
                    raise

            if overlay and isinstance(instance, TemplatedSpecification):
                # If a template was used, apply the overridding provided by the caller here
                instance.overlay_configuration(
                    configuration=overlay,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

            return instance

        # If parameters were missing, but this is validating, return None so validation may continue
        return None

    # We only reach this part if the input data couldn't be interpreted, so record or throw an error as appropriate
    message = f"Type '{type(data)}' cannot be read as JSON"

    if messages is not None:
        messages.append(message)
        return None
    else:
        raise ValueError(message)


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
        decoder_type: typing.Type[json.JSONDecoder] = None,
        validate: bool = False,
        messages: typing.List[str] = None
    ):
        """
        A factory for the given specification

        Args:
            data: Parameters used to instantiate the specification
            template_manager: A manager for any template specifications that can help apply template values
            decoder_type: an optional type of json decoder used to deserialize the specification
            validate: Only return messages instead of the constructed instance
            messages: an optional list of messages to pass error data into

        Returns:
            An instance of the specified specification class
        """
        if messages is None:
            messages = list()

        # Attempt to instantiate an instance of this class
        instance = create_class_instance(
            cls=cls,
            data=data,
            template_manager=template_manager,
            decoder_type=decoder_type,
            messages=messages,
            validate=validate
        )

        # If the instance is not none, construction of this instance was 'successful',
        # but that doesn't mean its children were.
        if instance is not None:
            # Go through every created object and determine all possibly failed validations
            if isinstance(instance, typing.Sequence):
                for member in instance:
                    try:
                        messages.extend(member.validate())
                    except Exception as exception:
                        logging.error(traceback.format_exc())
                        messages.append(str(exception))
            else:
                try:
                    validation_messages = instance.validate()
                    if validation_messages:
                        messages.extend(validation_messages)
                except Exception as exception:
                    logging.error(traceback.format_exc())
                    messages.append(str(exception))

        if messages and not validate:
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
    decoder_type: typing.Type[json.JSONDecoder] = None,
    messages: typing.List[str] = None,
    validate: bool = None
) -> typing.Any:
    """
    Attempts to convert a given value to the type expected by the parameter

    Args:
        value: The value to convert
        parameter: The function parameter that may or may not dictate what to cast the value as
        template_manager: The manager responsible for finding templating information
        decoder_type: An optional type of decoder to use when deserializing a template
        messages: An optional list for errors that might crop up
        validate: Whether this is just trying to see if values can be created - don't outright throw errors if true
    Returns:
        An attempted conversion if a parameter type is given; just the original value otherwise
    """
    if validate is None:
        validate = False

    # We can get direct information on what the parameter is really supposed to be by inspecting the parameter itself
    if isinstance(parameter, inspect.Parameter):
        parameter_type: typing.Type = None if parameter.annotation == parameter.empty else parameter.annotation
    else:
        # If the type wasn't a parameter, we'll need to take the type on faith, with two different scenarios -
        # a specification, or some other, fairly standard type
        parameter_type: typing.Union[typing.Type, typing.Type[Specification]] = parameter

    # Just return the value in this instance - there's nothing that may be deduced by it, so there's no fancy
    # handling that may be employed
    if parameter_type is None:
        return value

    # Check to see if the item is supposed to be a specification. If so, call that specification's create function
    if parameter_type in common.get_subclasses(Specification):
        return parameter_type.create(
            data=value,
            template_manager=template_manager,
            decoder_type=decoder_type,
            messages=messages,
            validate=validate
        )

    # Start processing the given value as a more standard type
    if isinstance(value, str) and util.value_is_number(value) and util.type_is_number(parameter_type):
        return float(value)
    elif isinstance(value, bytes) and util.value_is_number(value) and util.type_is_number(parameter_type):
        return float(value.decode())
    elif not isinstance(value, (bytes, str, typing.Mapping)) and isinstance(value, typing.Iterable):
        # If we can detect that the given values is some sort of collection we can iterate through,
        # step through and convert each
        converted_values = list()

        # If the given type is something like "typing.Sequence[int]", this will give us (int,)
        expected_type = typing.get_args(parameter_type)

        for member in value:
            # Try to convert every member
            try:
                converted_member = convert_value(
                    value=member,
                    parameter=expected_type[0],
                    template_manager=template_manager,
                    decoder_type=decoder_type,
                    messages=messages,
                    validate=validate
                )

                # A failure might indicate result in a null value. Only pass non-nulls or risk encountering errors
                # when validating later
                if converted_member is not None:
                    converted_values.append(converted_member)
            except Exception as exception:
                # If it's noticed that we are trying to record errors for validation,
                # record the error to both the messages and through the logs.
                # Neglecting to record to the log will hide errors.
                if validate and messages is not None:
                    messages.append(str(exception))
                    logging.error(traceback.format_exc())
                else:
                    raise

        return converted_values

    # Return the raw value if special handling could not be decided upon
    return value
