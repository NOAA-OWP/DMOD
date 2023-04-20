"""
Defines classes used to map data to named fields and how to extract data from documents
"""
import json
import typing
import os

from datetime import date
from datetime import time
from datetime import datetime

import pytz

from dateutil.parser import parse as parse_date

from dmod.core.common import find
from dmod.core.common import contents_are_equivalent
from dmod.core.common import Bag

from . import TemplateManager
from .base import TemplatedSpecification
from .. import util


class FieldMappingSpecification(TemplatedSpecification):
    """
    Details on how a field should be aliased
    """

    def __eq__(self, other: "FieldMappingSpecification") -> bool:
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "field") or self.field != other.field:
            return False
        elif not hasattr(other, "map_type") or self.map_type != other.map_type:
            return False

        return hasattr(other, "value") and self.value == other.value

    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields.update({
            "field": self.__field,
            "map_type": self.__map_type,
            "value": self.__value
        })
        return fields

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        self.__field = configuration.get("field", self.__field)
        self.__map_type = configuration.get("map_type", self.__map_type)
        self.__value = configuration.get("value", self.__value)

    def validate(self) -> typing.Sequence[str]:
        return list()

    __slots__ = ["__field", "__map_type", "__value"]

    def __init__(
        self,
        field: str,
        map_type: str,
        value: str,
        **kwargs
    ):
        super().__init__(**kwargs)
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


class AssociatedField(TemplatedSpecification):
    """
    A specification for additional data that should accompany selected data
    (retrieved measurements? Also get their dates)
    """

    def __eq__(self, other: "AssociatedField") -> bool:
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "name") or self.name != other.name:
            return False
        elif not hasattr(other, "path") or self.path != other.path:
            return False

        return hasattr(other, "datatype") and self.datatype == other.datatype

    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields.update({
            "datatype": self.__datatype,
            "path": self.__path
        })
        return fields

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        self.__datatype = configuration.get("datatype", self.__datatype)
        self.__path = configuration.get("path", self.__path)

    def validate(self) -> typing.Sequence[str]:
        messages = list()
        if self.name is None or self.name == '':
            messages.append(f"An index is missing a proper name")

        return messages

    __slots__ = ["__name", "__datatype", "__path"]

    def __init__(
        self,
        path: typing.Union[str, typing.Sequence[str]] = None,
        datatype: typing.Union[str, typing.Sequence[str]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)

        path_starts_at_root = False

        if path is None:
            self.__path = [self.name]
        elif isinstance(path, str):
            path_starts_at_root = path.startswith("/")
            self.__path = path.split("/")
        else:
            self.__path = path

        if path_starts_at_root:
            self.__path.insert(0, "$")

        self.__datatype = datatype.lower() if datatype else None

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
        return f"{self.name}: {self.__datatype}"


class ValueSelector(TemplatedSpecification):
    """
    Instructions for how to retrieve values from a data source
    """

    def __eq__(self, other: "ValueSelector") -> bool:
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "name") or self.name != other.name:
            return False
        elif not hasattr(other, "where") or self.where != other.where:
            return False
        elif not hasattr(other, "origin") or self.origin != other.origin:
            return False
        elif not hasattr(other, "path") or self.path != other.path:
            return False
        elif not hasattr(other, "associated_fields"):
            return False

        return contents_are_equivalent(Bag(self.associated_fields), Bag(other.associated_fields))

    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields.update({
            "where": self.__where,
            "path": self.__path,
            "origin": self.__origin,
            "datatype": self.__datatype
        })

        if self.__associated_fields:
            fields['associated_fields'] = [
                field.to_dict()
                for field in self.__associated_fields
            ]
        return fields

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        self.__where = configuration.get("where", self.__where)
        self.__datatype = configuration.get("datatype", self.__datatype)

        if 'path' in configuration:
            self.__set_path(configuration['path'])

        if 'origin' in configuration:
            self.__set_origin(configuration['origin'])

        for associated_field in configuration.get("associated_fields", list()):
            matching_field = find(
                self.__associated_fields,
                lambda field: field.identities_match(associated_field)
            )

            if matching_field:
                matching_field.overlay_configuration(
                    configuration=associated_field,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.__associated_fields.append(
                    AssociatedField.create(
                        data=associated_field,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                )

    def validate(self) -> typing.Sequence[str]:
        return list()

    __slots__ = ["__where", "__path", "__associated_fields", "__datatype", "__origin"]

    def __init__(
        self,
        where: str,
        origin: typing.Union[str, bytes, typing.Sequence[str]] = None,
        path: typing.Union[str, bytes, typing.Sequence[str]] = None,
        associated_fields: typing.Sequence[AssociatedField] = None,
        datatype: str = None,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.__where = where

        self.__origin = None
        self.__set_origin(origin)

        self.__path = None

        self.__set_path(path)

        if associated_fields is None:
            associated_fields: typing.List[AssociatedField] = list()

        self.__associated_fields = associated_fields
        self.__datatype = datatype.lower() if datatype is not None else None

    def __set_path(self, path):
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

        self.__path = path

    def __set_origin(self, origin):
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

        self.__origin = origin

    def get_column_types(self) -> typing.Dict[str, typing.Union[typing.Dict[str, typing.Any], typing.List[str]]]:
        """
        Gets a list of columns and their required parsing types

        This should only be necessary for constructors that require extra notification for fields, such as pandas

        Returns:
            A dictionary mapping columns to their parsing types and an optional list of columns that are dates
        """
        column_options = dict()

        if self.__datatype in ["datetime", "date"]:
            column_options['parse_dates'] = [self.name]
        else:
            dtype = util.type_name_to_dtype(self.__datatype)

            if dtype is not None:
                column_options['dtype'] = {self.name: dtype}

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
    def datatype(self) -> typing.Optional[str]:
        return self.__datatype

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
    def associated_fields(self) -> typing.Sequence[AssociatedField]:
        """
        Additional values to retrieve with selected values
        """
        return self.__associated_fields

    def __str__(self) -> str:
        description = f"{self.name} => {self.__where}"

        if self.__path:
            description += f": {os.linesep.join(self.__path)}"

        if self.__associated_fields:
            description += f", indexed by [{','.join([str(field) for field in self.__associated_fields])}]"

        return description
