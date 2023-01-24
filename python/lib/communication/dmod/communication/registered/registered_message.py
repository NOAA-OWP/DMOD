"""
Defines a common base class that may be used to fully describe forms of communication via just a few function
implementations
"""
import abc
import typing
from numbers import Number
from typing import ClassVar, Dict, Union

from ..message import AbstractInitRequest
from ..message import MessageEventType
from .exceptions import RegistrationError


class Field:
    """
    A description of a class member variable dictated by its name, the key that should designate its value from
    another source (like JSON), whether it is a required value, an optional function to generate a default value,
    an optional validation, and an optional data type.
    """
    def __init__(
        self,
        member: str,
        key: str = None,
        required: bool = False,
        default: typing.Callable[[], typing.Any] = None,
        validation: typing.Callable[[typing.Any], bool] = None,
        options: typing.Sequence[str] = None,
        data_type: typing.Type = None,
        description: str = None,
        *args,
        **kwargs
    ):
        """
        Constructs a field

        Args:
            member: The name that the field should be on a class instance
            key: The name of the field in another source that dictates where the data that should populate this field is
            required: Whether this field has to have a value in order to be valid
            default: A function to create a default value
            validation: A function to dictate if a passed value is valid
            options: Values that might be appropriate for this field - only used for examples
            data_type: What type that this field should hold
            description: Optional text used to indicate the use case for the field
            *args:
            **kwargs:
        """
        self.__key = key or member
        self.__member = member
        self.__required = bool(required)
        self.__default = default
        self.__data_type = data_type
        self.__description = description or ""

        options_are_a_collection = isinstance(options, typing.Sequence) and not isinstance(options, str)
        if options_are_a_collection or options is None:
            self.__options = options
        else:
            self.__options = [options]

        if validation:
            self.__validation = validation
        else:
            self.__validation = lambda _: True

    @property
    def key(self):
        """
        The name of the field in another source that dictates where the data that should populate this field is

        The name of the member variable will be used if a specific key is not given
        """
        return self.__key or self.__member

    @property
    def member(self):
        """
        The name of the member variable that serves as this field
        """
        return self.__member

    @property
    def required(self):
        """
        Whether a value for this field is required on the class it describes
        """
        return bool(self.__required)

    @property
    def description(self) -> str:
        """
        A description for what this field is for
        """
        return self.__description

    @property
    def options(self):
        """
        Discrete values that are valid for this field
        """
        options_are_a_collection = isinstance(self.__options, typing.Sequence) and not isinstance(self.__options, str)
        if options_are_a_collection or self.__options is None:
            options = self.__options
        else:
            options = [self.__options]
        return options

    def get_default(self):
        """
        Returns:
            A default value for this function
        """
        if self.__default:
            return self.__default()
        return None

    @property
    def field_format(self) -> dict:
        """
        Data about how this field should be represented in a message
        """
        if not self.__data_type:
            datatype = "Any"
        elif issubclass(self.__data_type, typing.Mapping):
            datatype = "{}"
        elif issubclass(self.__data_type, str):
            datatype = "String"
        elif issubclass(self.__data_type, bytes):
            datatype = "Binary"
        elif issubclass(self.__data_type, typing.Collection):
            datatype = "[]"
        elif issubclass(self.__data_type, Number):
            datatype = "Number"
        elif issubclass(self.__data_type, bool):
            datatype = "Boolean"
        else:
            datatype = str(self.__data_type)

        if not self.__options:
            options = None
        elif len(self.__options) == 1 and self.__options[0] in ["*", "ALL", "ANY"]:
            options = str(self.__options[0])
        elif len(self.__options) == 1:
            return {
                self.key: str(self.__options[0])
            }
        else:
            options = [
                "Any" if isinstance(option, str) and option.upper() in ["*", "ALL", "ANY"] else option
                for option in self.__options
            ]

        return {
            self.key: {
                "type": datatype,
                "required": self.required,
                "description": self.description,
                "has_default": self.__default is not None,
                "maps_to": self.member,
                "options": options
            }
        }

    def value_is_valid(self, value: typing.Any) -> bool:
        """
        Checks to see if the passed value is valid for this field

        Args:
            value: The value to check

        Returns:
            Whether the pass value may fit this field
        """
        if self.__required and value is None:
            return False

        if value is not None and self.__data_type and not isinstance(value, self.__data_type):
            return False

        return self.__validation(value)

    def __str__(self):
        if self.__key is None or self.__key == self.__member:
            mapping = self.__member
        else:
            mapping = f"{self.__key} => {self.__member}"

        if self.__options:
            mapping += f" = ({', '.join([str(option) for option in self.__options])})"

        if self.__required:
            mapping += ": Required"

        return mapping


class NestedField(Field):
    """
    Represents a field that has one or more fields nested underneath it
    """
    def __init__(
        self,
        member: str,
        sub_fields: typing.Collection[Field],
        key: str = None,
        default: typing.Callable[[], typing.Any] = None,
        validation: typing.Callable[[typing.Any], bool] = None,
        description: str = None,
        *args,
        **kwargs
    ):
        """
        Constructor

        Args:
            member: The name that the field should be on a class instance
            sub_fields: Fields that should fall under the indicated field
            key: The name of the field in another source that dictates where the data that should populate this field is
            default: A function to create a default value
            validation: A function to dictate if a passed value is valid
            description: Optional text used to indicate the use case for the field
            *args:
            **kwargs:
        """
        # This is a required field if any of its subfields are required
        required = len([subfield for subfield in sub_fields if subfield.required]) > 0

        super().__init__(
            member=member,
            key=key,
            required=required,
            default=default,
            validation=validation,
            data_type=typing.Mapping,
            description=description,
            *args,
            **kwargs
        )
        self.__sub_fields = sub_fields

    def value_is_valid(self, value: typing.Any) -> bool:
        """
        Checks to see if the passed value matches this described field.

        Checks to make sure that all subfields are valid as well

        Args:
            value: The value to check

        Returns:
            Whether the given value is valid for this field
        """
        if not super().value_is_valid(value):
            return False

        for field in self.__sub_fields:
            # Return False if the sub field is required but doesn't have a matching subvalue
            if field.required and (value is None or field.key not in value or value[field.key] is None):
                return False

            # Go ahead and continue if value is none - the following code will break if attempted and this isn't a
            # failure condition yet
            if value is None:
                continue

            subvalue = value[field.key]

            # This isn't considered valid if a nested value isn't considered valid
            if not field.value_is_valid(subvalue):
                return False

        return True

    @property
    def field_format(self) -> dict:
        """
        Metadata about how this field should be present within a message
        """
        field_format = super().field_format

        subfield_format = dict()
        for subfield in self.__sub_fields:
            subfield_format.update(subfield.field_format)
        field_format[self.key]['fields'] = subfield_format

        return field_format

    def __str__(self):
        sub_keys = "{" + ", ".join([str(sub_field) for sub_field in self.__sub_fields]) + "}"
        return f"{self.key} => {sub_keys}{': Required' if self.required else ''}"


class FieldedMessage(AbstractInitRequest):
    """
    A message formed by dictated fields coming from subclasses
    """
    event_type: ClassVar[MessageEventType] = MessageEventType.INFORMATION_UPDATE
    """
    The event type for this message; this shouldn't have as much bearing on how to handle this message. 
    Use members and class type instead.
    """

    def __init__(self, document: typing.Mapping, *args, **kwargs):
        """
        Constructor

        Args:
            document: The document that should be used to populate the designated fields
            *args: Positional arguments to pass to the AbstractInitRequest constructor
            **kwargs: Keyword arguments to pass to the AbstractInitRequest constructor
        """
        super().__init__(*args, **kwargs)
        self.__message = document
        """The original document that created this message"""

        self.__field_values: typing.Dict[str, typing.Any] = dict()
        """A mapping between encountered fields and their values"""

        fields = self._get_fields()

        if len(fields) < 1:
            raise RegistrationError(
                f"There aren't enough fields in {self.__class__.__name__} for it to be considered a valid message type"
            )

        # Form a list to describe every missing field
        missing_fields: typing.List[str] = list()

        # Add every indicated field to this message so that its value may be accessed via 'message.member' and
        # 'message[member]'. Values that are required and missing should be noted
        for field in fields:
            # Try to get the value from the source
            if field.key in document:
                value = document.get(field.key)
            elif field.required:
                # If the value wasn't present in the source, yet was required, take note and move to the next one
                missing_fields.append(str(field))
                continue
            else:
                # If no value was present and the field isn't required, add in a default value
                value = field.get_default()

            # Add member values to this instance if nothing was deemed as missing
            if not missing_fields:
                # Set the value as an attribute so that it may be accessed via 'message.member' or
                # 'getattr(message, 'member')
                setattr(self, field.member, value)

                # Add the value to an internal dictionary so that the value may be accessed by 'message[member]'
                self.__field_values[field.member] = value

        # Throw an exception if field values are missing
        if missing_fields:
            raise RegistrationError(
                f"{self.__class__.__name__} could not be constructed. "
                f"The following fields are missing: {', '.join(missing_fields)}"
            )

    def __getitem__(self, member: str):
        if member not in self.__field_values:
            raise KeyError(f"There is no {member} field in a {self.__class__.__name__}")
        return self.__field_values[member]

    @classmethod
    @abc.abstractmethod
    def _get_fields(cls) -> typing.Collection[Field]:
        """
        Returns:
            All fields required to form this message
        """
        pass

    @property
    def original_message(self) -> dict:
        """
        The original JSON object that formed this message
        """
        return {
            key: value
            for key, value in self.__message.items()
        }

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> typing.Optional["FieldedMessage"]:
        """
        Attempts to convert the passed in json object into this kind of message

        Args:
            json_obj: The JSON message to interpret

        Returns:
            An instantiated message if the format fits
        """
        all_fields_are_present = True
        required_fields = [field for field in cls._get_fields() if field.required]

        if len(required_fields) < 1:
            raise RegistrationError(
                f"There aren't required enough fields in {cls.__name__} for it to be considered a valid message type"
            )

        for field in cls._get_fields():
            all_fields_are_present = field.value_is_valid(json_obj.get(field.key))

        if all_fields_are_present and cls.additional_validations_pass(json_obj):
            return cls(json_obj)

        return None

    @classmethod
    def additional_validations_pass(cls, json_obj: dict) -> bool:
        """
        Checks to make sure that any implemented additional validations pass

        Args:
            json_obj: The JSON object to check

        Returns:
            True if not overridden
        """
        return True

    @classmethod
    def get_message_layout(cls) -> dict:
        """
        Gets the general layout of how this message should be formed based on its fields
        """
        layout = dict()

        for field in cls._get_fields():
            layout.update(field.field_format)

        return layout

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        """
        Returns:
            The message in a serializable dictionary form
        """
        return self.original_message


class FieldedActionMessage(FieldedMessage, abc.ABC):
    """
    A message consisting of a named domain (such as 'evaluations', a named action (like 'launch'),
    and all parameters required to perform the action within the domain

    These types of messages should be structured like:
        - "domain": "evaluations"
        - "action": "launch"
        - "action_parameters":
            - "param1": value
            - "param2": value
    """
    @classmethod
    @abc.abstractmethod
    def _get_action_parameters(cls) -> typing.Collection[Field]:
        """
        Returns:
            All parameters that should be passed into the message
        """
        pass

    @classmethod
    @abc.abstractmethod
    def get_action_name(cls) -> str:
        """
        Returns:
            The name of the action associated with this type
        """
        pass

    @classmethod
    @abc.abstractmethod
    def get_valid_domains(cls) -> typing.Union[str, typing.Collection[str]]:
        """
        Returns:
            The names of the domains that this message belongs in
        """
        ...

    @classmethod
    def get_message_layout(cls) -> dict:
        layout = super().get_message_layout()

        return layout

    @classmethod
    def _get_fields(cls) -> typing.Collection[Field]:
        """
        Get a list of all fields that should be on this action message

        Should consist of {'domain': str, 'action': str, 'action_parameters': dict} at the very least

        Returns:
            All fields that make up this message
        """
        fields = [
            Field(
                "domain",
                data_type=str,
                required=True,
                options=cls.get_valid_domains(),
                description="The name of the domain that this message pertains to. For example, "
                            "multiple domains might have a 'status' action."
            ),
            Field(
                "action",
                data_type=str,
                required=True,
                options=[cls.get_action_name()],
                description="The name of the action that the service should perform based on this message"
            )
        ]

        parameters = cls._get_action_parameters()

        if parameters:
            fields.append(NestedField("action_parameters", sub_fields=parameters))

        return fields

    @classmethod
    def additional_validations_pass(cls, json_obj: dict) -> bool:
        """
        Ensures that the passed json object exists within one of the valid domains and that the action matches

        Args:
            json_obj: The json object to check

        Returns:
            Whether the passed json object has the right domain and action
        """
        domain = json_obj.get("domain")

        # action messages require a domain (domains A and B might both have a launch function, for example)
        if not domain:
            return False

        # Action messages of course require an action, so make sure it's there
        action = json_obj.get("action")

        if not action:
            return False

        # A message may be valid for multiple domains, so get all approved domains and make sure that the given domain
        # fits the constraints of this type of message class
        valid_domains = cls.get_valid_domains()

        domains_is_a_sequence = valid_domains
        domains_is_a_sequence = domains_is_a_sequence and not isinstance(valid_domains, (str, bytes))
        domains_is_a_sequence = domains_is_a_sequence and isinstance(valid_domains, typing.Iterable)

        if domains_is_a_sequence:
            if isinstance(valid_domains[0], str) and valid_domains[0].strip().upper() in ["*", "ANY", "ALL"]:
                valid_domains = [valid_domain for valid_domain in valid_domains] + [domain]
            else:
                valid_domains = [str(valid_domain).strip().upper() for valid_domain in cls.get_valid_domains()]
        else:
            valid_domains = [valid_domains]

        passes = str(domain).strip().upper() in valid_domains

        # Now make sure that the given action matches this class' action, case-insensitive.
        # 'Launch ' should be able to match on 'launch' as forms of input may not always be precise for casing
        # and outer whitespace
        passes = passes and str(action).strip().upper() == str(cls.get_action_name()).strip().upper()

        return passes
