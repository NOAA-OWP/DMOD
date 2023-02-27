"""
Defines functions providing choices for models and fields
"""
import abc
import inspect
import typing


CHOICES = typing.List[typing.Tuple[str, str]]
"""
A list of tuples, the first entry being the value stored in the database, 
the second entry being the value provided to the user
"""

VALUE_TYPE = typing.TypeVar("VALUE_TYPE")


VALID_CHOICE_VALUE_TYPES = (
    str,
    int,
    float,
    bool
)

TEXT_FIELD = "text"
VALUE_FIELD = "value"
ENTRY_FIELD = "entry"
DESCRIPTION_FIELD = "description"


class ChoiceException(Exception):
    pass


def make_choice(text: str, value: VALUE_TYPE, description: str = None) -> typing.Callable[[], VALUE_TYPE]:
    """
    Creates a decorated static function that returns the given value, with attributes detailing the Django choice
    associated with it, the function's value, the function's text, along with an optional description

    Args:
        text: The name of the choice that should appear on the screen
        value: Some value that the choice should allude to
        description: An optional description detailing what the choice means

    Returns:
        A decorated method with no parameters
    """
    if not isinstance(value, VALID_CHOICE_VALUE_TYPES):
        valid_types = f"[{', '.join([str(valid_type) for valid_type in VALID_CHOICE_VALUE_TYPES])}]"
        raise ChoiceException(
            f"The value {text}=`{str(value)}` cannot be created. "
            f"Received a value of type `{type(value)}` and only the following types are allowed: {valid_types}"
        )

    def get_value():
        return value

    get_value = staticmethod(get_value)
    setattr(get_value, TEXT_FIELD, text)
    setattr(get_value, VALUE_FIELD, value)
    setattr(get_value, ENTRY_FIELD, (value, text))

    if description:
        setattr(get_value, DESCRIPTION_FIELD, description)

    return get_value


class _Choices(abc.ABC):
    """
    Defines classes with self-discoverable attributes with variable value types, mostly for use when constraining
    selectable values for models.

    Enum is not used here since `StrEnum` isn't implemented until 3.11 (3.8 is the minimum at the time of writing).
    """
    @classmethod
    def get_choice_type(cls) -> typing.Type:
        """
        The type of value that class values should be
        """
        return object

    @classmethod
    def field_choices(cls) -> CHOICES:
        """
        Returns the value of all classmethod properties in a CHOICES format with the name of the
        property as the first element and the value of the property as the second value
        """
        filtered_entries = [
            (method_name, method) for method_name, method in cls.__dict__.items()
            if isinstance(method, staticmethod)
               and len(inspect.signature(method).parameters) == 0
               and hasattr(method, ENTRY_FIELD)
               and hasattr(method, VALUE_FIELD)
               and isinstance(getattr(method, VALUE_FIELD), cls.get_choice_type())
        ]

        choices: CHOICES = list()
        texts: typing.Dict[str, str] = dict()

        for method_name, choice_method in filtered_entries:
            try:
                entry = getattr(choice_method, ENTRY_FIELD)

                is_entry_type = isinstance(entry, tuple) and len(entry) == 2
                if not (is_entry_type and isinstance(entry[1], str) and isinstance(entry[0], VALID_CHOICE_VALUE_TYPES)):
                    continue

                text = getattr(choice_method, TEXT_FIELD)
                value = getattr(choice_method, VALUE_FIELD)

                if getattr(choice_method, TEXT_FIELD) in texts:
                    raise ChoiceException(
                        f"Cannot define the field `{method_name} = ({text}, {str(value)})`. "
                        f"There is already a field with the text '{text}' bound "
                        f"to {cls.__class__.__name__}.{texts[text]}"
                    )

                if not (isinstance(value, cls.get_choice_type()) or value is None):
                    raise ChoiceException(
                        f"The value for the {text} variable should be a `{str(cls.get_choice_type())}` but "
                        f"'{str(value)}' (a {str(type(value))}) was encountered instead"
                    )

                choices.append(entry)
                texts[text] = method_name
            except Exception as e:
                pass

        return choices


class StringChoices(_Choices, abc.ABC):
    @classmethod
    def get_choice_type(cls) -> typing.Type:
        return str


class StoredDatasetType(StringChoices):
    """
    Provides choices for what a stored dataset might contain
    """
    geometry = make_choice(text="Geometry", value="geometry")


class StoredDatasetFormat(StringChoices):
    """
    Provides choices for what a stored dataset might exist as
    """
    gpkg = make_choice(text="GeoPackage", value="gpkg")

    json = make_choice(text="JSON", value="json")

    geojson = make_choice(text="GeoJSON", value="geojson")
