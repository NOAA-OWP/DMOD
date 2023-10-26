"""
Provides classes that enable the representation and discovery of specification templates
"""
from __future__ import annotations
import abc
import json
import logging
import os
import pathlib
import tempfile
import typing
from collections import defaultdict

from dmod.core.common import humanize_text
from dmod.core.common.types import TextValue
from dmod.core.common import DBAPIConnection
from dmod.core.common import DBAPICursor
from dmod.core.common import find
from dmod.core.common import flatmap
from dmod.core.common.helper_functions import package_directory

from ._all import get_specification_options
from ._all import TemplateDetails
from ._all import TemplateManagerProtocol
from ._all import TemplatedSpecification
from .base import GetSpecificationTypeProtocol
from .base import SUPPORTS_SPECIFICATION_TYPE

from .templates import FileTemplateManifest


class BasicTemplateDetails(TemplateDetails):
    """
    The most basic implementation of TemplateDetails possible
    Gained by just providing all raw values
    """
    @classmethod
    def from_record(
        cls,
        record: typing.Mapping[str, typing.Any],
        name_field: str = None,
        specification_type_field: str = None,
        description_field: str = None,
        configuration_field: str = None
    ) -> TemplateDetails:
        """
        Generate TemplateDetails from values in a Map

        Args:
            record: The map to read data from
            name_field: The field
            specification_type_field:
            description_field:
            configuration_field:

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

        return cls(
            name=record[name_field],
            specification_type=record[specification_type_field],
            description=record.get(description_field),
            configuration=record[configuration_field]
        )

    def __init__(
        self,
        name: str,
        specification_type: str,
        configuration: str,
        description: str = None
    ):
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
        self.__specification_type = specification_type
        self.__description = description
        self.__configuration = configuration

    @property
    def name(self) -> str:
        return self.__name

    @property
    def specification_type(self) -> str:
        return self.__specification_type

    def get_configuration(self, decoder_type: typing.Type[json.JSONDecoder] = None) -> dict:
        return json.loads(self.__configuration, decoder_type=decoder_type)

    @property
    def description(self) -> typing.Optional[str]:
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

    def export_to_database(self, table_name: str, connection: DBAPIConnection, exists_ok: bool = None):
        """
        Write templates to a database

        Args:
            table_name: The name of the table to store templates in
            connection: A connection to the desired database
            exists_ok: Whether it is ok to insert data into the table if it already exists
        """
        cursor: typing.Optional[DBAPICursor] = None

        if exists_ok is None:
            exists_ok = False

        try:
            cursor = connection.cursor()
            table_creation_script = f"""CREATE TABLE{' IF NOT EXISTS' if exists_ok else ''} "{table_name}" (
    name varchar(255),
    specification_type varchar(255),
    description varchar(500) NULL,
    configuration TEXT
)"""
            cursor.execute(table_creation_script)
            connection.commit()

            entries = flatmap(
                lambda entry: (
                    entry.name,
                    entry.specification_type,
                    entry.description,
                    json.dumps(entry.get_configuration(), indent=4)
                ),
                self.get_all_templates()
            )

            insertion_script = f'INSERT INTO "{table_name}" (name, specification_type, description, configuration) ' \
                               f'VALUES (?, ?, ?, ?)'

            cursor.executemany(insertion_script, entries)

            connection.commit()
        finally:
            try:
                cursor.close()
            except:
                logging.error("A cursor for a connection could not be closed")

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
    def __init__(self, templates: typing.Mapping[str, typing.Iterable[TemplateDetails]] = None):
        """
        An in-memory manager requires data to be passed in directly, ready to go

        Args:
            templates: The template data to provide
        """
        if templates:
            self.__templates = {
                key: [entry for entry in value]
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
    def __init__(self, manifest_path: typing.Union[str, pathlib.Path]):
        """
        Load a manifest to instruct access to elements on disk

        Args:
            manifest_path: The path to the manifest file
        """
        manifest_path = pathlib.Path(manifest_path) if isinstance(manifest_path, str) else manifest_path
        with manifest_path.open('r') as manifest_file:
            manifest_data = json.load(manifest_file)
        self.manifest: FileTemplateManifest = FileTemplateManifest.parse_obj(manifest_data)
        self.manifest.set_root_directory(manifest_path.parent)
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
        table_name: str,
        connection: DBAPIConnection,
        name_column: str = None,
        specification_type_column: str = None,
        description_column: str = None,
        configuration_column: str = None
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
        self.connection = connection

        self.__name_column = name_column if name_column else 'name'

        if specification_type_column:
            self.__specification_type_column = specification_type_column
        else:
            self.__specification_type_column = 'specification_type'

        self.__description_column = description_column if description_column else 'description'
        self.__configuration_column = configuration_column if configuration_column else 'configuration'

        self.__loaded_entries: typing.MutableMapping[str, typing.List[TemplateDetails]] = defaultdict(list)