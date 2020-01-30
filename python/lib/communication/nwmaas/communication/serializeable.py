from abc import ABC, abstractmethod
import json


class Serializable(ABC):
    """
    An interface class for an object that can be serialized to a dictionary-like format (i.e., potentially a JSON
    object) and JSON string format based directly from dumping the aforementioned dictionary-like representation.

    Objects of this type will also used the JSON string format as their default string representation.
    """

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

    @abstractmethod
    def to_dict(self) -> dict:
        """
        Get the representation of this instance as a dictionary or dictionary-like object (e.g., a JSON object).

        Returns
        -------
        dict
            the representation of this instance as a dictionary or dictionary-like object (e.g., a JSON object)
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
