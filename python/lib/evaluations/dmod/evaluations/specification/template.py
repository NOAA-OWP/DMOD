"""
Provides classes that enable the representation and discovery of specification templates
"""
from __future__ import annotations
import abc
import dataclasses
import json
import logging
import os
import pathlib
import sqlite3
import sys
import tempfile
import typing
import shutil

from collections import defaultdict
from datetime import datetime

from dateutil.parser import parse as parse_date

from dmod.core.common import humanize_text
from dmod.core.common.types import TextValue
from dmod.core.common import DBAPIConnection
from dmod.core.common import DBAPICursor
from dmod.core.common import find
from dmod.core.common import flat
from dmod.core.common import flatmap
from dmod.core.common.helper_functions import package_directory

from ._all import get_specification_options
from ._all import TemplateDetails
from ._all import TemplateManagerProtocol
from .base import GetSpecificationTypeProtocol
from .base import SUPPORTS_SPECIFICATION_TYPE

from .templates import FileTemplateManifest


_DEFAULT_TEMPLATE_TABLE_NAME = os.environ.get("DEFAULT_TEMPLATE_TABLE_NAME", "template")


@dataclasses.dataclass
class QueryDetails:
    query: str
    """The SQL query to execute"""

    value_labels: typing.Sequence[str]
    """The order of value names that need to be used as parameters"""


@dataclasses.dataclass
class Column:
    """
    Represents a column in a database table
    """
    name: str
    """The name of the column"""
    
    datatype: str
    """The data type for the column"""
    
    optional: typing.Optional[bool] = dataclasses.field(default=False)
    """Whether values in the column are optional"""
    @property
    def definition(self) -> str:
        """
        The definition of the column if it were to appear within a table creation script
        """
        return f"{self.name} {self.datatype}{' NULL' if self.optional else ''}"

    def __str__(self):
        return self.definition

    def __repr__(self):
        return self.__str__()


@dataclasses.dataclass
class Table:
    """
    Represents a table in a database
    """
    name: str
    """The name of the table"""
    
    columns: typing.List[Column]
    """The columns within a database"""
    
    keys: typing.Optional[typing.List[str]] = dataclasses.field(default=None)
    """Any sort of identifying values for each row in the table"""
    
    @property
    def required_columns(self) -> typing.Set[str]:
        """
         The name of all columns that MUST have a value
        """
        return set([
            column.name
            for column in self.columns
            if not column.optional
        ])

    @property
    def column_names(self) -> typing.Sequence[str]:
        """
        The name of each column
        """
        return [column.name for column in self.columns]

    @property
    def definition(self) -> str:
        """
        A script that will create this table in a database
        """
        lines: typing.List[str] = list()
        lines.append(f"CREATE TABLE IF NOT EXISTS {self.name} (")

        column_definitions = [column.definition for column in self.columns]
        full_column_definitions = "    " + f",{os.linesep}    ".join(column_definitions)

        lines.append(full_column_definitions)
        lines.append(");")

        return os.linesep.join(lines)

    def initialize(self, connection: DBAPIConnection):
        """
        Ensure that this table exists within the given database
        
        Args:
            connection: A connection to the database that will hold this table
        """
        cursor: typing.Optional[DBAPICursor] = None

        try:
            cursor = connection.cursor()
            cursor.execute(self.definition)

            try:
                connection.commit()
            except BaseException as exception:
                print(f"Could not commit possible changes to the {self.name} table - {exception}", file=sys.stderr)
        finally:
            if cursor:
                cursor.close()

    def create_keyed_insert_query(self, columns: typing.Sequence[str]) -> QueryDetails:
        """
        Generate a query that will insert unique values into the table

        Args:
            columns: The columns that will have values inserted

        Returns:
            A sql query that will insert data into a database table
        """
        missing_columns: typing.Set[str] = self.required_columns.union(self.keys).difference(columns)
        
        if missing_columns:
            raise ValueError(
                f"Cannot create a script to insert values into '{self.name}' - "
                f"missing the following required columns: {', '.join(columns)}"
            )

        # Insert values into each column that don't already exist based on the given values
        query = f"""
INSERT INTO {self.name}
    ({', '.join(columns)})
SELECT {', '.join(['?' for _ in columns])}
WHERE NOT EXISTS (
    SELECT 1
    FROM {self.name}
    WHERE {' AND '.join([f'{key} = ?' for key in self.keys])}
)"""
        labels = [name for name in columns] + [key for key in self.keys]
        return QueryDetails(query=query, value_labels=labels)

    def create_unkeyed_insert_query(self, columns: typing.Sequence[str]) -> QueryDetails:
        """
        Create an insert query for this table that does not identify values based on keys

        Args:
            columns: The columns that will have values to insert

        Returns:
            An insert script for this table that will insert values into the given columns
        """
        missing_columns: typing.Set[str] = self.required_columns.difference(columns)

        if missing_columns:
            raise ValueError(
                f"Cannot create a script to insert values into '{self.name}' - "
                f"missing the following required columns: {', '.join(columns)}"
            )

        # Insert values into the given database
        query = f"""
INSERT INTO {self.name}
    ({', '.join(columns)}
VALUES ({', '.join(['?' for _ in columns])});
"""
        labels = [name for name in columns]
        return QueryDetails(query=query, value_labels=labels)

    def override_table(self, connection: DBAPIConnection):
        cursor: typing.Optional[DBAPICursor] = None

        try:
            cursor = connection.cursor()
            cursor.execute(f"SELECT * FROM {self.name}")
            results = cursor.fetchall()
            table_is_present = len(results) > 0
        except:
            table_is_present = True
        finally:
            if cursor:
                cursor.close()

        if table_is_present:
            try:
                cursor = connection.cursor()

                cursor.execute(f"TRUNCATE TABLE {self.name}")
                cursor.fetchall()

                try:
                    connection.commit()
                except BaseException as exception:
                    print(f"Could not commit possible changes to the {self.name} table - {exception}", file=sys.stderr)
            finally:
                if cursor:
                    cursor.close()

        self.initialize(connection=connection)

    def insert_templates(
        self,
        connection: DBAPIConnection,
        rows: typing.Union[typing.Sequence[TemplateDetails], typing.Mapping[str, typing.Sequence[TemplateDetails]]],
        override: bool = None
    ):
        """
        Insert template data into this database

        Args:
            connection: The connection to the database of interest
            rows: The templates to insert
            override: Replace data that is within the database
        """
        if override is None:
            override = False

        if override:
            self.override_table(connection=connection)

        if isinstance(rows, typing.Mapping):
            rows = flat(rows)

        query_details: QueryDetails

        if self.keys and not override:
            query_details = self.create_keyed_insert_query(self.column_names)
        else:
            query_details = self.create_unkeyed_insert_query(self.column_names)

        query: str = query_details.query

        parameters: typing.Sequence[typing.Sequence[typing.Any]] = [
            [
                getattr(row, label)
                for label in query_details.value_labels
            ]
            for row in rows
        ]

        cursor: typing.Optional[DBAPICursor] = None
        try:
            cursor = connection.cursor()
            cursor.executemany(query, parameters)

            try:
                connection.commit()
            except BaseException as exception:
                print(f"Could not commit possible changes to the {self.name} table - {exception}", file=sys.stderr)
        finally:
            if cursor:
                cursor.close()

    def __str__(self):
        return self.definition

    def __repr__(self):
        return self.__str__()


def get_template_table(name: str) -> Table:
    """
    Get the specification for how a template will be stored in a database table

    Args:
        name: The expected name of the database table

    Returns:
        A Table object representing the appearance of a specification template
    """
    return Table(
        name=name,
        columns=[
            Column(name="name", datatype="VARCHAR(255)"),
            Column(name="specification_type", datatype="VARCHAR(255)"),
            Column(name="description", datatype="VARCHAR(500)", optional=True),
            Column(name="author", datatype="VARCHAR(500)", optional=True),
            Column(name="configuration", datatype="TEXT"),
            Column(name="last_modified", datatype="VARCHAR(50)")
        ],
        keys=[
            'name',
            'specification_type',
            'author'
        ]
    )


class BasicTemplateDetails(TemplateDetails):
    """
    The most basic implementation of TemplateDetails possible
    Gained by just providing all raw values
    """

    @property
    def last_modified(self) -> typing.Optional[datetime]:
        """
        The last time this template changed
        """
        return self.__last_modified

    @classmethod
    def from_record(
        cls,
        record: typing.Mapping[str, typing.Any],
        name_field: str = None,
        specification_type_field: str = None,
        description_field: str = None,
        configuration_field: str = None,
        author_name_field: str = None,
        last_modified_field: str = None
    ) -> TemplateDetails:
        """
        Generate TemplateDetails from values in a Map

        Args:
            record: The map to read data from
            name_field: The field
            specification_type_field:
            description_field:
            configuration_field:
            author_name_field:
            last_modified_field:

        Returns:
            A basic TemplateDetails object
        """
        if not name_field:
            name_field = 'name'

        if not specification_type_field:
            specification_type_field = 'specification_type'

        if not description_field:
            description_field = 'description'

        if not configuration_field:
            configuration_field = 'configuration'

        if not author_name_field:
            author_name_field = "author"

        if not last_modified_field:
            last_modified_field = "last_modified"

        return cls(
            name=record[name_field],
            specification_type=record[specification_type_field],
            description=record.get(description_field),
            configuration=record[configuration_field],
            author_name=record.get(author_name_field),
            last_modified=record.get(last_modified_field)
        )

    @classmethod
    def copy(cls, details: TemplateDetails) -> BasicTemplateDetails:
        """
        Create a copy of the given TemplateDetails object

        Args:
            details: The details to copy

        Returns:
            A new TemplateDetails object detached from the source
        """
        return cls(
            name=details.name,
            specification_type=details.specification_type,
            configuration=json.dumps(details.get_configuration(), indent=4),
            description=details.description,
            author_name=details.author_name,
            last_modified=details.last_modified
        )

    def __init__(
        self,
        name: str,
        specification_type: str,
        configuration: typing.Union[str, typing.Dict[str, typing.Any]],
        description: str = None,
        author_name: str = None,
        last_modified: typing.Optional[typing.Union[str, datetime]] = None
    ):
        """
        Constructor

        Args:
            name: The name of the template
            specification_type: What type of template this is
            configuration: The configuration that this template represents
            description: A description of what this template does
            author_name: The name of whoever created or maintains this template
            last_modified: The last time this template was modified
        """
        if not name:
            raise ValueError("Cannot create template information - no name was passed")

        if not specification_type:
            raise ValueError(
                f"Cannot create template information - no specification type was passed for the '{name}' template"
            )

        if not configuration:
            raise ValueError(
                f"Cannot create template information - no configuration was passed for the '{name}' template"
            )

        self.__name = name
        """The name of the template"""

        self.__specification_type = specification_type
        """What type of template this is"""

        self.__description = description
        """A description of what this template does"""

        self.__configuration = configuration
        """The configuration that this template represents"""

        self.__author_name = author_name
        """The name of whoever created or maintains this template"""

        self.__last_modified = parse_date(last_modified) if isinstance(last_modified, str) else last_modified
        """The last time this template was modified"""

    @property
    def name(self) -> str:
        """
        The name of the template
        """
        return self.__name

    @property
    def specification_type(self) -> str:
        """
        What type of template this is
        """
        return self.__specification_type

    @property
    def author_name(self) -> typing.Optional[str]:
        """
        The name of whoever created or maintains this template
        """
        return self.__author_name

    def get_configuration(self, decoder_type: typing.Type[json.JSONDecoder] = None) -> dict:
        """
        Get the configuration for this template

        Args:
            decoder_type: A JSON Decoder containing specialized details on how to convert the configuration from a
                str/bytes to a dictionary

        Returns:
            The dictionary containing the configuration for the template
        """
        if isinstance(self.__configuration, (str, bytes, bytearray)):
            self.__configuration = json.loads(self.__configuration, cls=decoder_type)
        return self.__configuration

    @property
    def description(self) -> typing.Optional[str]:
        """
        A description of what this template does
        """
        return self.__description

    def __hash__(self):
        return hash((self.name, self.specification_type, self.get_configuration()))

    def __eq__(self, other):
        if not isinstance(other, TemplateDetails):
            return False

        return self.name == other.name \
            and self.specification_type == other.specification_type \
            and self.get_configuration() == other.get_configuration()


class TemplateManager(abc.ABC, TemplateManagerProtocol):
    """
    A mechanism to read and write specification template data
    """
    @staticmethod
    def get_specification_types() -> typing.Sequence[typing.Tuple[str, str]]:
        """
        Get a list of value-name pairs for use when building HTML selectors

        Both elements should be the name of a configuration specification that supports templates

        Returns:
            A list of value-name pairs tying the name of a configuration specification to a friendly name for a configuration specification
        """
        return get_specification_options()

    @abc.abstractmethod
    def get_templates(self, specification_type: SUPPORTS_SPECIFICATION_TYPE) -> typing.Sequence[TemplateDetails]:
        """
        Get all templates of a given specification type

        Args:
            specification_type: The type of configuration specification that the desired templates belong to

        Returns:
            A collection of objects with the information necessary to provide basic template inspection
        """
        pass

    def search(
        self,
        specification_type: typing.Optional[str],
        name: typing.Optional[str],
        **kwargs
    ) -> typing.Mapping[str, typing.Sequence[TemplateDetails]]:
        """
        Find TemplateDetails based on individual parameters

        Args:
            specification_type: The type of specification to look for
            name: The part of the name to look for
            **kwargs: Additional parameters to check for if the underlying implementation supports it

        Returns:
            A mapping from specification types to a listing of all templates that passed the filter
        """
        if specification_type and name:
            name = name.lower()
            found_templates = [
                template
                for template in self.get_templates(specification_type=specification_type)
                if name in template.name.lower()
            ]
            found_templates = {specification_type: found_templates} if found_templates else dict()
        elif specification_type:
            return {
                specification_type: self.get_templates(specification_type=specification_type)
            }
        elif name:
            name = name.lower()
            all_templates = self.get_all_templates()
            found_templates = defaultdict(list)
            for type_of_specification, specifications_for_type in all_templates.items():
                for specification_for_type in specifications_for_type:
                    if name in specification_for_type.name.lower():
                        found_templates[type_of_specification].append(specification_for_type)
        else:
            found_templates = self.get_all_templates()

        return found_templates


    def get_all_templates(self) -> typing.Mapping[str, typing.Sequence[TemplateDetails]]:
        """
        Get all configured templates in hierarchical order

        Returns:
            A hierarchical map of all templates across all specification types
        """
        templates = dict()

        for specification_type_name, specification_type in self.get_specification_types():
            for template in self.get_templates(specification_type_name):
                if specification_type_name not in templates:
                    templates[specification_type_name] = list()

                templates[specification_type_name].append(template)

        return templates

    def get_template(
        self,
        specification_type: SUPPORTS_SPECIFICATION_TYPE,
        name: str,
        *,
        decoder_type: typing.Type[json.JSONDecoder] = None,
        **kwargs
    ) -> typing.Optional[dict]:
        """
        Get the raw configuration for a template based on the type of specification and its name

        Args:
            specification_type: The type of configuration specification that the desired template pertains to
            name: The name of the template to use
            decoder_type: a custom JSON Decoder used to overwrite json decoding for stored templates

        Returns:
            The dictionary containing the basic configuration details for a template
        """
        if isinstance(specification_type, GetSpecificationTypeProtocol):
            specification_type = specification_type.get_specification_type()

        matching_templates = [
            template
            for template in self.get_templates(specification_type)
            if template.name == name
        ]
        matches_to_remove = list()

        for match in matching_templates:
            for key, value in kwargs.items():
                if not getattr(match, key, object()) == value and match not in matches_to_remove:
                    matches_to_remove.append(match)

        for match in matches_to_remove:
            if match in matching_templates:
                matching_templates.remove(match)

        if matching_templates:
            return matching_templates[0].get_configuration(decoder_type=decoder_type)

        return None

    def get_options(self, specification_type: SUPPORTS_SPECIFICATION_TYPE) -> typing.Sequence[typing.Tuple[str, str]]:
        """
        Get value-name pairs describing the templates that pertain to a specific specification type

        Args:
            specification_type: The name of the configuration specification whose templates are desired

        Returns:
            A list of value-name pairs describing the available templates for a given specification type
        """
        return [
            detail.field_choice
            for detail in self.get_templates(specification_type)
        ]

    def export_to_database(self, table_name: str, connection: DBAPIConnection, override: bool = None):
        """
        Write templates to a database

        Args:
            table_name: The name of the table to store templates in
            connection: A connection to the desired database
            override: Replace data that already exists
        """
        if override is None:
            override = False

        table = get_template_table(table_name)

        try:
            table.initialize(connection=connection)
        except BaseException as creation_exception:
            raise Exception(f"Could not create the {table_name} table: {creation_exception}") from creation_exception

        table.insert_templates(connection=connection, rows=self.get_all_templates(), override=override)

class FileTemplateDetails(TemplateDetails):
    @property
    def text_value(self) -> TextValue[str]:
        return TextValue(
            group=self.specification_type,
            value=self.name,
            text=humanize_text(self.name)
        )

    def __init__(self, name: str, specification_type: str, description: str, path: pathlib.Path):
        self.__name = name
        self.__specification_type = specification_type
        self.__description = description
        self.__path = path

    def export_to_file(self, directory: typing.Union[str, pathlib.Path]) -> pathlib.Path:
        """
        Write templates to a file structure

        Args:
            directory: The directory to write all the templates and their manifest to

        Returns:
            The path to the manifest
        """
        basic_manifest: typing.Dict[str, typing.List[typing.Dict[str, str]]] = defaultdict(list)

        def to_record(details: TemplateDetails) -> typing.Dict[str, str]:
            record: typing.Dict[str, str] = {
                "name": details.name,
                "specification_type": details.specification_type,
                "configuration": json.dumps(details.get_configuration(), indent=4),
                "path": os.path.join(details.specification_type, details.name.lower().replace(" ", "_") + ".json")
            }

            if details.description:
                record['description'] = details.description

            return record

        template_data = flatmap(to_record, self.get_all_templates())

        for entry in template_data:
            specification_type = entry.pop("specification_type")
            configuration = entry.pop("configuration")

            container_directory = directory / specification_type
            container_directory.mkdir(parents=True, exist_ok=True)

            configuration_path = directory / entry['path']
            configuration_path.write_text(configuration)

            basic_manifest.get(specification_type).append(entry)

        manifest_path = directory / "template_manifest.json"
        manifest_path.write_text(json.dumps(basic_manifest, indent=4))
        return manifest_path

    def export_to_archive(self, archive_path: typing.Union[str, pathlib.Path]) -> pathlib.Path:
        """
        Write all the templates to a file structure within an archive

        NOTE: Only zip files are supported - data will be archived to zip files regardless of given extension

        Args:
            archive_path:  Where to save the archive

        Returns:
            The path to the newly created archive
        """
        with tempfile.TemporaryDirectory() as temporary_directory:
            manifest_path = self.export_to_file(directory=temporary_directory)
            file_directory = manifest_path.parent

            archive_path = package_directory(file_directory, archive_path)

            return archive_path


class InMemoryTemplateManager(TemplateManager):
    """
    A template manager that just stores template data in memory
    """
    @classmethod
    def from_archive(
        cls,
        path: pathlib.Path,
        manifest_path: pathlib.Path = None,
        archive_format: typing.Literal["zip", "tar", "gztar", "bztar", "xztar"] = None,
        *args,
        **kwargs
    ) -> InMemoryTemplateManager:
        with tempfile.TemporaryDirectory() as temporary_directory:
            file_manager = FileTemplateManager.from_archive(
                path,
                temporary_directory,
                manifest_path,
                archive_format,
                *args,
                **kwargs
            )
            return cls.from_template_manager(file_manager)

    @classmethod
    def from_template_manager(cls, manager: TemplateManager) -> InMemoryTemplateManager:
        return cls(templates=manager.get_all_templates())

    def __init__(self, templates: typing.Mapping[str, typing.Iterable[TemplateDetails]] = None):
        """
        An in-memory manager requires data to be passed in directly, ready to go

        Args:
            templates: The template data to provide
        """
        if templates:
            self.__templates = {
                key: [
                    BasicTemplateDetails.copy(entry)
                    for entry in value
                ]
                for key, value in templates.items()
            }
        else:
            self.__templates = {}

    def add_template(
        self,
        specification_type: SUPPORTS_SPECIFICATION_TYPE,
        template: TemplateDetails
    ) -> InMemoryTemplateManager:
        """
        Add a template to the manager

        Args:
            specification_type: The type of template to add
            template: Details about the template

        Returns:
            The updated manager
        """
        if isinstance(specification_type, GetSpecificationTypeProtocol):
            specification_type = specification_type.get_specification_type()

        if specification_type not in self.__templates:
            self.__templates[specification_type] = []

        self.__templates[specification_type].append(template)
        return self

    def get_all_templates(self) -> typing.Mapping[str, typing.Sequence[TemplateDetails]]:
        return self.__templates

    def get_templates(self, specification_type: SUPPORTS_SPECIFICATION_TYPE) -> typing.Sequence[TemplateDetails]:
        if isinstance(specification_type, GetSpecificationTypeProtocol):
            specification_type = specification_type.get_specification_type()

        return self.__templates.get(specification_type, [])


class FileTemplateManager(TemplateManager):
    """
    A template manager that reads everything based on a manifest on the file system
    """
    @classmethod
    def from_archive(
        cls,
        archive_path: pathlib.Path,
        output_path: pathlib.Path,
        manifest_path: pathlib.Path = None,
        archive_format: typing.Literal["zip", "tar", "gztar", "bztar", "xztar"] = None,
        *args,
        **kwargs
    ) -> FileTemplateManager:
        """
        Create a file template manager from an archived manager

        Args:
            archive_path: The path to the archive
            output_path: Where to unpack the archive
            manifest_path: The path to the manifest within the archive
            archive_format: The format of the archive

        Returns:
            A file manager based on the contents of the archive
        """
        if not archive_path.exists():
            raise FileNotFoundError(f"There is no archive file at {archive_path}")

        if not manifest_path:
            manifest_path = pathlib.Path("template_manifest.json")

        if not archive_format:
            archive_format = "zip"

        manifest_path = output_path / manifest_path

        directory_created = False
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
            directory_created = True

        try:
            shutil.unpack_archive(archive_path, output_path, format=archive_format)

            if not manifest_path.exists():
                raise FileNotFoundError(f"No manifest was found at {manifest_path}")

            return cls(path=manifest_path, *args, **kwargs)
        except BaseException as exception:
            if directory_created:
                shutil.rmtree(output_path, ignore_errors=True)
            raise

    def __init__(self, path: typing.Union[str, pathlib.Path], *args, **kwargs):
        """
        Load a manifest to instruct access to elements on disk

        Args:
            path: The path to the manifest file
        """
        path = pathlib.Path(path) if isinstance(path, str) else path
        with path.open('r') as manifest_file:
            manifest_data = json.load(manifest_file)
        self.manifest: FileTemplateManifest = FileTemplateManifest.parse_obj(manifest_data)
        self.manifest.set_root_directory(path.parent)
        self.manifest.ensure_validity()

    def get_templates(self, specification_type: SUPPORTS_SPECIFICATION_TYPE) -> typing.Sequence[TemplateDetails]:
        if isinstance(specification_type, GetSpecificationTypeProtocol):
            specification_type = specification_type.get_specification_type()

        if specification_type not in self.manifest:
            return []

        return [
            details
            for details in self.manifest[specification_type].as_details()
        ]

    def export_to_file(self, directory: typing.Union[str, pathlib.Path]) -> pathlib.Path:
        return self.manifest.save(directory=directory)

    def export_to_archive(self, directory: typing.Union[str, pathlib.Path]) -> pathlib.Path:
        return self.manifest.archive(output_path=directory)

    def __eq__(self, other: FileTemplateManager) -> bool:
        if not isinstance(other, FileTemplateManager):
            return False
        return self.manifest == other.manifest


def query_database(connection: DBAPIConnection, command: str, *args, **kwargs) -> typing.Sequence[typing.Dict[str, typing.Any]]:
    """
    Perform a query in the given database and return formatted data

    Examples:
        >>> query_database(connection, "SELECT * FROM ExampleTable where field = ?", 8)
        [
            {"field": 8, "et_v_name": "Example1"},
            {"field": 8, "et_v_name": "Example2"}
        ]

    Args:
        connection: The connection to the database
        command: The query to run in the database
        *args: Arguments such as a series of rows to insert or a positional list of query parameters
        **kwargs: Keyword arguments to use as named parameters in the command

    Returns:
        Results of the run query organized as a sequence of mappings from column names to column values
    """
    cursor: typing.Optional[DBAPICursor] = None

    try:
        cursor = connection.cursor()
        cursor.execute(command, *args, **kwargs)

        column_names = [
            column[0]
            for column in cursor.description
        ]

        rows = cursor.fetchall()

        return [
            {
                name: value
                for name, value in zip(column_names, row)
            }
            for row in rows
        ]
    finally:
        if cursor:
            try:
                cursor.close()
            except BaseException as close_exception:
                logging.error(f"Could not close a cursor for a database template: {close_exception}")


class DatabaseTemplateManager(TemplateManager):
    """
    Template manager for data whose contents lie within a database
    """
    @classmethod
    def default_template_table_name(cls) -> str:
        return "template"

    def get_templates(self, specification_type: SUPPORTS_SPECIFICATION_TYPE) -> typing.Sequence[TemplateDetails]:
        if isinstance(specification_type, GetSpecificationTypeProtocol):
            specification_type = specification_type.get_specification_type()

        command = f'SELECT * FROM "{self.table_name}" WHERE {self.__specification_type_column} = ?'
        raw_templates = query_database(self.connection, command, specification_type)

        templates: typing.List[TemplateDetails] = list()

        for raw_template in raw_templates:
            template = BasicTemplateDetails.from_record(
                record=raw_template,
                name_field=self.__name_column,
                specification_type_field=self.__specification_type_column,
                description_field=self.__description_column,
                configuration_field=self.__configuration_column
            )

            if specification_type not in self.__loaded_entries:
                self.__loaded_entries[specification_type] = []

            if template not in self.__loaded_entries:
                self.__loaded_entries[specification_type].append(template)

            templates.append(template)

        return templates

    def get_template(
        self,
        specification_type: SUPPORTS_SPECIFICATION_TYPE,
        name: str,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ) -> typing.Optional[dict]:
        if isinstance(specification_type, GetSpecificationTypeProtocol):
            specification_type = specification_type.get_specification_type()

        possibly_loaded_templates = self.__loaded_entries.get(specification_type)
        found_template: typing.Optional[TemplateDetails] = None

        if possibly_loaded_templates:
            found_template = find(possibly_loaded_templates, lambda loaded_template: loaded_template.name == name)

        if found_template:
            return found_template.get_configuration(decoder_type=decoder_type)

        command = f'SELECT * ' \
                  f'FROM "{self.table_name}" ' \
                  f'WHERE {self.__name_column} = ? ' \
                  f'AND {self.__specification_type_column} = ?'
        arguments = (name, specification_type)

        raw_templates = query_database(self.connection, command, *arguments)

        if len(raw_templates) > 1:
            raise KeyError(
                f"A template with a name of '{name}' and specification type of '{specification_type}' is not unique - "
                f"the database might be corrupted"
            )

        if raw_templates:
            template = BasicTemplateDetails.from_record(
                record=raw_templates[0],
                name_field=self.__name_column,
                specification_type_field=self.__specification_type_column,
                description_field=self.__description_column,
                configuration_field=self.__configuration_column
            )

            if specification_type not in self.__loaded_entries.keys():
                self.__loaded_entries[specification_type] = []

            if template not in self.__loaded_entries[specification_type]:
                self.__loaded_entries[specification_type].append(template)

            return template.get_configuration(decoder_type=decoder_type)

        return None

    def get_all_templates(self) -> typing.Mapping[str, typing.Sequence[TemplateDetails]]:
        command = f'SELECT * FROM "{self.table_name}"'
        raw_templates = query_database(self.connection, command)

        templates: typing.MutableMapping[str, typing.List[TemplateDetails]] = defaultdict(list)

        for raw_template in raw_templates:
            template = BasicTemplateDetails.from_record(
                record=raw_template,
                name_field=self.__name_column,
                specification_type_field=self.__specification_type_column,
                description_field=self.__description_column,
                configuration_field=self.__configuration_column
            )

            if template not in self.__loaded_entries[template.specification_type]:
                self.__loaded_entries[template.specification_type].append(template)

            templates[template.specification_type].append(template)

        return templates

    def __init__(
        self,
        table_name: str = None,
        connection: typing.Union[DBAPIConnection, str, pathlib.Path] = None,
        name_column: str = None,
        specification_type_column: str = None,
        description_column: str = None,
        configuration_column: str = None,
        *args,
        **kwargs
    ):
        """
        Store details used to connect to the table containing templates and define what columns to expect values
        to be in

        Args:
            table_name: The name of the table that will store templates
            connection: A connection to the database that stores templates
            name_column: The name of the column that stores the name of a template
            specification_type_column: The name of the column that stores the specification type of a template
            description_column: The name of the column that stores the description of a template
            configuration_column: The name of the column that stores the configuration of a template
        """
        self.table_name = table_name

        if connection is None:
            connection = ":memory:"

        if isinstance(connection, (str, pathlib.Path)):
            self.connection: DBAPIConnection = sqlite3.connect(connection)
        else:
            self.connection: DBAPIConnection = connection

        self.__name_column = name_column if name_column else 'name'

        if specification_type_column:
            self.__specification_type_column = specification_type_column
        else:
            self.__specification_type_column = 'specification_type'

        self.__description_column = description_column if description_column else 'description'
        self.__configuration_column = configuration_column if configuration_column else 'configuration'

        self.__loaded_entries: typing.MutableMapping[str, typing.List[TemplateDetails]] = defaultdict(list)