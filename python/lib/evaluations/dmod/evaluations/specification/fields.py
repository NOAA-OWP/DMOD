"""
Defines classes used to map data to named fields and how to extract data from documents
"""
from __future__ import annotations

import json
import typing
import os

from datetime import date
from datetime import time
from datetime import datetime

import pytz

from dateutil.parser import parse as parse_date

from pydantic import Field

from dmod.core.common import find
from dmod.core.common import contents_are_equivalent
from dmod.core.common import Bag
from pydantic import root_validator
from pydantic import validator

from .base import TemplateManagerProtocol
from .base import TemplatedSpecification
from .. import util


class FieldMappingSpecification(TemplatedSpecification):
    """
    Details on how a field should be aliased
    """
    field: str = Field(description="The field to be aliased")

    # TODO: Define the options for map types elsewhere and use that to define a literal
    map_type: str = Field(
        description="Where the field to be aliased lies (is it a key? Is it a dictionary value? Is it a column?)"
    )
    # TODO: Define the options for this elsewhere and use that to define a literal
    value: str = Field(description="What the field should end up being called")

    def __eq__(self, other: "FieldMappingSpecification") -> bool:
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "field") or self.field != other.field:
            return False
        elif not hasattr(other, "map_type") or self.map_type != other.map_type:
            return False

        return hasattr(other, "value") and self.value == other.value

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManagerProtocol,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        self.field = configuration.get("field", self.field)
        self.map_type = configuration.get("map_type", self.map_type)
        self.value = configuration.get("value", self.value)

    def validate_self(self) -> typing.Sequence[str]:
        return list()

    def __str__(self) -> str:
        return f"{self.map_type}: {self.field} comes from {self.value}"


class AssociatedField(TemplatedSpecification):
    """
    A specification for additional data that should accompany selected data
    (retrieved measurements? Also get their dates)
    """

    datatype: typing.Optional[str] = Field(
        default=None,
        description="A datatype to coerce this value to"
    )
    path: typing.Optional[typing.Union[str, typing.List[str]]] = Field(default=None, description="The path to the data in the source")

    def __eq__(self, other: "AssociatedField") -> bool:
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "name") or self.name != other.name:
            return False
        elif not hasattr(other, "path") or self.path != other.path:
            return False

        return hasattr(other, "datatype") and self.datatype == other.datatype

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManagerProtocol,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        self.datatype = configuration.get("datatype", self.datatype)
        self.path = configuration.get("path", self.path)

    def validate_self(self) -> typing.Sequence[str]:
        messages = list()
        if self.name is None or self.name == '':
            messages.append("An index is missing a proper name")

        return messages

    @root_validator
    def _format_path(cls, values):
        path_starts_at_root = False
        path = values.get("path")

        if path is None and values.get("name") is not None:
            values['path'] = [values['name']]
        elif isinstance(path, str):
            path_starts_at_root = path.startswith("/")
            values['path'] = path.split("/")

        if path_starts_at_root:
            values['path'].insert(0, "$")

        if 'path' not in values and 'name' not in path:
            raise ValueError("Associated fields must define a name and/or path")

        if values.get("datatype"):
            values['datatype'] = values['datatype'].lower()

        return values

    def to_datatype(self, value):
        """
        Attempt to convert the given value to the required datatype

        Args:
            value: The value to convert

        Returns:
            The converted value, if specified
        """
        if not self.datatype or value is None:
            return value

        datatype = self.datatype.lower()

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
        datatype = self.datatype.lower()
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
        if self.name:
            return f"{self.name}{': ' + self.datatype if self.datatype else ''}"
        else:
            # We must have a path here
            return f"{'/'.join([part for part in self.path])}{': ' + self.datatype if self.datatype else ''}"


class ValueSelector(TemplatedSpecification):
    """
    Instructions for how to retrieve values from a data source
    """
    where: typing.Literal["key", "value", "filename", "constant", "column"] = Field(
        description="Where the value may be found (Dict key? Dict value? Column?)"
    )
    origin: typing.Optional[typing.Union[str, bytes, typing.List[str]]] = Field(
        default=None,
        description="The path from which to look. The value should be `""` or `'/'` if searching from the root."
    )
    path: typing.Optional[typing.Union[str, bytes, typing.List[str]]] = Field(
        default=None,
        description="The path from which to look from the origin"
    )
    associated_fields: typing.Optional[typing.List[AssociatedField]] = Field(
        default_factory=list,
        description="Additional values to retrieve with selected values"
    )
    datatype: typing.Optional[str] = Field(
        default=None,
        description="How to interpret selected values"
    )

    def __eq__(self, other: ValueSelector) -> bool:
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

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManagerProtocol,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if "where" in configuration:
            where = configuration['where']

            if isinstance(where, bytes):
                where = where.decode()

            if isinstance(where, str):
                where = where.lower()

            where_annotation = self.__class__.__fields__['where'].annotation
            if where not in typing.get_args(where_annotation):
                raise ValueError(f"'{str(where)}' is not a valid value for 'where' in a Value Selector")

            self.where = where

        if "datatype" in configuration and configuration['datatype'] != self.datatype:
            datatype = configuration['datatype']

            if isinstance(datatype, bytes):
                datatype = datatype.decode()

            if not isinstance(datatype, str):
                raise ValueError(f"Values for the data type in a ValueSelector must be a string. Instead received '{str(datatype)}'")

            self.datatype = datatype

        if 'path' in configuration:
            self.__set_path(configuration['path'])

        if 'origin' in configuration:
            self.__set_origin(configuration['origin'])

        for associated_field in configuration.get("associated_fields", list()):
            matching_field = find(
                self.associated_fields,
                lambda field: field.identities_match(associated_field)
            )

            if matching_field:
                matching_field.overlay_configuration(
                    configuration=associated_field,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.associated_fields.append(
                    AssociatedField.create(
                        data=associated_field,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                )

    def validate_self(self) -> typing.Sequence[str]:
        return list()

    @validator("datatype")
    def _interpret_datatype(cls, value: typing.Union[bytes, str] = None) -> typing.Optional[str]:
        if isinstance(value, bytes):
            value = value.decode()

        if isinstance(value, str):
            value = value.lower()

        return value

    def __set_path(self, path):
        if isinstance(path, bytes):
            path = path.decode()

        path_starts_at_root = False

        if isinstance(path, str):
            path_starts_at_root = path.startswith("/")
            path = path.split("/")

        if path_starts_at_root:
            path.insert(0, '$')

        if path:
            path = [
                part
                for part in path
                if part not in (None, "")
            ]

        self.path = path

    @validator("path")
    def _interpret_path(
        cls,
        value: typing.Union[str, bytes, typing.Sequence[str]] = None
    ) -> typing.Optional[typing.Sequence[str]]:
        if isinstance(value, bytes):
            value = value.decode()

        path_starts_at_root = False

        if isinstance(value, str):
            path_starts_at_root = value.startswith("/")
            value = value.split("/")

        if path_starts_at_root:
            value.insert(0, '$')

        if value:
            value = [
                part
                for part in value
                if part not in (None, "")
            ]

        return value

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

        self.origin = origin

    @validator("origin", always=True)
    def _interpret_origin(
        cls,
        value: typing.Union[str, bytes, typing.Sequence[str]] = None
    ) -> typing.Optional[typing.Sequence[str]]:
        origin_starts_at_root = False

        if isinstance(value, bytes):
            value = value.decode()

        if isinstance(value, str):
            origin_starts_at_root = value.startswith("/")
            value = value.split("/")
        elif not value:
            value = ["$"]

        if origin_starts_at_root and value[0] != '$':
            value.insert(0, "$")

        if value:
            value = [
                part
                for part in value
                if part not in (None, "")
            ]

        return value

    def get_column_types(self) -> typing.Dict[str, typing.Union[typing.Dict[str, typing.Any], typing.List[str]]]:
        """
        Gets a list of columns and their required parsing types

        This should only be necessary for constructors that require extra notification for fields, such as pandas

        Returns:
            A dictionary mapping columns to their parsing types and an optional list of columns that are dates
        """
        column_options = dict()

        if self.datatype in ["datetime", "date"]:
            column_options['parse_dates'] = [self.name]
        else:
            dtype = util.type_name_to_dtype(self.datatype)

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
        if not self.datatype:
            return value

        datatype = self.datatype.lower()

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

    def __str__(self) -> str:
        description = f"{self.name} => {self.where}"

        if self.path:
            description += f": {os.linesep.join(self.path)}"

        if self.associated_fields:
            description += f", indexed by [{','.join([str(field) for field in self.associated_fields])}]"

        return description
