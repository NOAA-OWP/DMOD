from abc import ABC, abstractmethod
import json


class Serializable(ABC):
    """
    An interface class for an object that can be serialized to a dictionary-like format (i.e., potentially a JSON
    object) and JSON string format based directly from dumping the aforementioned dictionary-like representation.

    Objects of this type will also used the JSON string format as their default string representation.
    """

    _SERIAL_DATETIME_STR_FORMAT = '%Y-%m-%d %H:%M:%S'

    @classmethod
    @abstractmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Parameters
        ----------
        json_obj

        Returns
        -------
        A new object of this type instantiated from the deserialize JSON object dictionary
        """
        pass

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

    @abstractmethod
    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        """
        Get the representation of this instance as a serialized dictionary or dictionary-like object (e.g., a JSON
        object).

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
        pass

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
        return json.dumps(self.to_dict())


class SerializedDict(Serializable):
    """
    A basic encapsulation of a dictionary as a :class:`Serializeable`.
    """

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        return cls(json_obj)

    def __init__(self, base_dict: dict):
        self.base_dict = base_dict

    def to_dict(self) -> dict:
        return self.base_dict
