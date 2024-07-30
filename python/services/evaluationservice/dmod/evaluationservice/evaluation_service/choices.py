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


VALID_CHOICE_VALUE_TYPES = (
    str,
    int,
    float,
    bool
)


class ChoiceException(Exception):
    pass


class Choice:
    def __init__(self, text: str, value: typing.Any, description: str = None, ensured_type: typing.Type = None):
        if not isinstance(value, VALID_CHOICE_VALUE_TYPES):
            raise ChoiceException(
                f"Choices must be one of the following types: "
                f"{', '.join([str(valid_type) for valid_type in VALID_CHOICE_VALUE_TYPES])}. "
                f"Received {type(value)} for {text}"
            )

        if ensured_type:
            if not isinstance(value, ensured_type):
                raise ChoiceException(
                    f"The value for {text} must be a {str(ensured_type)}, but received a {type(value)}"
                )

        self.__text = text
        self.__value = value
        self.__description = description
        self.__entry = (self.__value, self.__text)

    @property
    def text(self):
        return self.__text

    @property
    def value(self):
        return self.__value

    @property
    def description(self):
        return self.__description

    @property
    def entry(self):
        return self.__entry[0], self.__entry[1]

    def __str__(self):
        return self.__description or self.__text

    def __repr__(self):
        return f"{self.__text}: {self.__value}"

    def __eq__(self, other):
        return self.__value == other


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
        filtered_entries: typing.List[typing.Callable[[typing.Type[cls]], Choice]] = [
            getattr(method, '__func__')
            for method_name, method in cls.__dict__.items()
            if not method_name.startswith("_")
               and isinstance(method, classmethod)
        ]

        filtered_entries = [
            method
            for method in filtered_entries
            if len(inspect.signature(method).parameters) == 1
               and inspect.signature(method).return_annotation == Choice
        ]

        if len(filtered_entries) == 0:
            raise ChoiceException(f"Something went wrong when trying to find available choices for {cls.__name__}")

        return [method(cls).entry for method in filtered_entries]


class StringChoices(_Choices, abc.ABC):
    @classmethod
    def get_choice_type(cls) -> typing.Type:
        return str


class StoredDatasetType(StringChoices):
    """
    Provides choices for what a stored dataset might contain
    """
    @classmethod
    def geometry(cls) -> Choice:
        return Choice("Geometry", "geometry", ensured_type=cls.get_choice_type())


class StoredDatasetFormat(StringChoices):
    """
    Provides choices for what a stored dataset might exist as
    """
    @classmethod
    def gpkg(cls) -> Choice:
        return Choice("GeoPackage", "gpkg", ensured_type=cls.get_choice_type())

    @classmethod
    def json(cls) -> Choice:
        return Choice("JSON", "json", ensured_type=cls.get_choice_type())

    @classmethod
    def geojson(cls) -> Choice:
        return Choice("GeoJSON", "geojson", ensured_type=cls.get_choice_type())
