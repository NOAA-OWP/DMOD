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


def _entry(member):
    setattr(member, "choice", True)
    return member


class _Choices(abc.ABC):
    @classmethod
    @property
    def field_choices(cls) -> CHOICES:
        """
        Returns the value of all classmethod properties in a CHOICES format with the name of the
        property as the first element and the value of the property as the second value
        """
        filtered_entries = {
            key: getattr(cls, key) for key, value in cls.__dict__.items()
            if isinstance(value, classmethod)
        }
        choices = [
            (key, value) for key, value in filtered_entries.items()
            if isinstance(value, (str, int, float, bool))
        ]
        return choices


class StoredDatasetType(_Choices):
    """
    Provides choices for what a stored dataset might contain
    """
    @classmethod
    @property
    def geometry(cls):
        return "Geometry"


class StoredDatasetFormat(_Choices):
    """
    Provides choices for what a stored dataset might exist as
    """
    @classmethod
    @property
    def gpkg(cls):
        return "GeoPackage"

    @classmethod
    @property
    def json(cls):
        return "JSON"

    @classmethod
    @property
    def geojson(cls):
        return "GeoJSON"
