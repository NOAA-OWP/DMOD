"""
Provide utilities to import and export templates
"""
from __future__ import annotations

import os
import sys
import sqlite3
import sys
import typing
import pathlib
from datetime import datetime
from getpass import getpass

from typing_extensions import ParamSpec
from typing_extensions import Concatenate

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from django.core.management import BaseCommand
from django.core.management import CommandParser

from dmod.core.common.helper_functions import is_true
from dmod.evaluations.specification import TemplateManager
from dmod.evaluations.specification import InMemoryTemplateManager
from dmod.evaluations.specification import FileTemplateManager
from dmod.evaluations.specification import DatabaseTemplateManager

import evaluation_service.data.templates as templates
from evaluation_service.apps import EvaluationServiceConfig
from evaluation_service.specification import SpecificationTemplateManager

_ACTION_TYPE = typing.Literal['import', 'export']
"""Type specifications for what actions are handled"""

_ACTIONS: typing.Sequence[str] = typing.get_args(_ACTION_TYPE)
"""The name of each action that is handled"""

_DATA_FORMAT_TYPE = typing.Literal['database', 'files', 'archive']
"""Type specifications for what formats are allowed"""

_DATA_FORMATS: typing.Sequence[str] = typing.get_args(_DATA_FORMAT_TYPE)
"""The name of each format that is allowed"""

_DEFAULT_EXPORT_TYPE: str = os.environ.get("DEFAULT_TEMPLATE_EXPORT_TYPE", "database")
"""The default format to export data to if none is given"""

_DEFAULT_OVERRIDE_SETTING = is_true(os.environ.get("DEFAULT_TEMPLATE_OVERRIDE", False))
"""Whether to override template data if it is not indicated whether to do so"""

_DEFAULT_TEMPLATE_EXPORT_TABLE = os.environ.get("DEFAULT_TEMPLATE_EXPORT_TABLE", "template")
"""What table to export data into if no table name is given"""


_DEFAULT_FORMAT_FILENAME: typing.Mapping[_DATA_FORMAT_TYPE, str] = {
    "database": "exported_templates.sqlite",
    "files": "",
    "archive": "exported_templates.zip"
}
"""The default file name parameter for each format type"""


def get_application_name() -> str:
    return EvaluationServiceConfig.name


def get_command_name() -> str:
    """
    Get the name of the current command

    Django defines command names by file names under `<app>/management/commands`, so the name for this set of commands
    will be this file name without the extension

    Returns:
        The name of this management command
    """
    return os.path.splitext(os.path.basename(__file__))[0]


def get_default_export_path(data_format: _DATA_FORMAT_TYPE) -> pathlib.Path:
    """
    Get the default path for template exports

    Args:
        data_format: The format that will be exported

    Returns:
        The path where exported data should lie
    """
    default_export_path = os.environ.get("DEFAULT_TEMPLATE_EXPORT_PATH")

    if default_export_path is None:
        default_export_path = pathlib.Path.cwd() / "template_exports"

    default_export_path = default_export_path / data_format / str(int(datetime.now().timestamp()))
    default_export_path.mkdir(parents=True, exist_ok=True)

    default_filename = _DEFAULT_FORMAT_FILENAME[data_format]

    if default_filename:
        default_export_path = default_export_path / default_filename

    return default_export_path


def export_archive(manager: TemplateManager, path: pathlib.Path, override: bool, *args, **kwargs):
    """
    Dump templates within the manager into an archive at the given path

    Args:
        manager: The manager that contains the templates and know-how needed to export
        path: Where to place the new archive
        override: Whether it's ok to overwrite a preexisting version of this archive
        *args:
        **kwargs:
    """
    if path.exists() and not override:
        raise FileExistsError(
            f"Files already exist at {path}. Try again with the override flag or choose a different location"
        )
    archive_path = manager.export_to_archive(path)
    print(f"Templates exported to an archive at {archive_path}")


def export_files(manager: TemplateManager, path: pathlib.Path, override: bool, *args, **kwargs):
    """
    Dump templates within the manager into a file structure at the given path

    Args:
        manager: The manager that contains the templates and know-how needed to export
        path: Where to place the template files
        override: Whether it's ok to overwrite data
        *args:
        **kwargs:
    """
    if path.exists() and not override:
        raise FileExistsError(
            f"Files already exist at {path}. Try again with the override flag or choose a different location"
        )
    manifest_path = manager.export_to_file(directory=path)
    print(f"Templates exported to files with the manifest at {manifest_path}")


def export_database(
    manager: SpecificationTemplateManager,
    path: pathlib.Path,
    override: bool,
    template_table: str = None,
    *args,
    **kwargs
):
    """
    Dump templates within the manager into a sqlite database

    Args:
        manager: The manager that contains the templates and know-how needed to export
        path: Where to put the sqlite database
        override: Whether it's ok to overwrite data in the database
        template_table: What table to put the data in
        *args:
        **kwargs:

    Returns:

    """
    if template_table is None:
        template_table = _DEFAULT_TEMPLATE_EXPORT_TABLE

    try:
        manager.export_to_database(table_name=template_table, database_connection=path, exists_ok=override)
    except sqlite3.OperationalError as sql_error:
        print(f"Could not manipulate the database: {sql_error}", file=sys.stderr)
        sys.exit(255)
    except:
        raise
    else:
        print(f"Template database exported to '{path}")


_EXPORT_FUNCTIONS: typing.Dict[_DATA_FORMAT_TYPE, typing.Callable] = {
    "database": export_database,
    "files": export_files,
    "archive": export_archive,
}
"""A mapping between format names and the export functions for those formats"""


def create_database_import_manager(path: pathlib.Path, template_table: str = None, *args, **kwargs) -> TemplateManager:
    """
    Create a template manager that will import data from a sqlite database

    Args:
        path: The path to the sqlite database
        template_table: The table that contains the
        *args:
        **kwargs:

    Returns:

    """
    return DatabaseTemplateManager(table_name=template_table, connection=path, *args, **kwargs)


def create_file_import_manager(path: pathlib.Path, *args, **kwargs) -> TemplateManager:
    """
    Create a template manager that will read in data from a file structure organised with a manifest

    Args:
        path: The path to either the directory holding the template manifest or the manifest itself
        *args:
        **kwargs:

    Returns:

    """
    if path.is_dir():
        path = path / "template_manifest.json"
    return FileTemplateManager(path=path, *args, **kwargs)


def create_archive_import_manager(path: pathlib.Path, *args, **kwargs) -> TemplateManager:
    """
    Create a template manager that will handle information within an archive

    Args:
        path: The location of the archive to read
        *args:
        **kwargs:

    Returns:
        A template manager that provides access to templates within an archive
    """
    return InMemoryTemplateManager.from_archive(path=path, *args, **kwargs)


def export_templates(data_format: _DATA_FORMAT_TYPE, path: pathlib.Path, override: bool = None, *args, **kwargs):
    """
    Export template data from this Django instance's database into a given format at a given location

    Args:
        data_format: What format to export data as
        path: Where to export the data to
        override: Whether to replace data if it already exists
        *args:
        **kwargs:
    """
    if override is None:
        override = _DEFAULT_OVERRIDE_SETTING

    manager = SpecificationTemplateManager()

    export_function = _EXPORT_FUNCTIONS.get(data_format)

    if export_function is None:
        raise KeyError(f"Templates cannot be exported into the '{data_format}' format")

    export_function(manager=manager, path=path, override=override, *args, **kwargs)


VARIABLE_ARGUMENTS = ParamSpec("VARIABLE_ARGUMENTS")
"""
Represents arguments containing '*args' and '**kwargs'
"""

IMPORT_MANAGER_CONSTRUCTOR = typing.Callable[Concatenate[pathlib.Path, VARIABLE_ARGUMENTS], TemplateManager]
"""Represents a function that takes a path and variable types of arguments"""

_IMPORT_MANAGER_CONSTRUCTORS: typing.Dict[_DATA_FORMAT_TYPE, IMPORT_MANAGER_CONSTRUCTOR] = {
    "database": create_database_import_manager,
    "files": create_file_import_manager,
    "archive": create_archive_import_manager
}
"""
A mapping from an acceptable data format to a function that will create the template manager to handle that type of data
"""


def create_manager(
    data_format: _DATA_FORMAT_TYPE,
    path: pathlib.Path,
    template_table: str = None,
    *args,
    **kwargs
) -> TemplateManager:
    """
    Create a new instance of a template manager that can read data of the requested format

    Args:
        data_format: The type of data to read
        path: Where the type of data lives
        template_table: The name of the table to read if it's in a table
        *args:
        **kwargs:

    Returns:
        The TemplateManager that will facilitate an import
    """
    if not path.exists():
        raise FileNotFoundError(f"No template data can be found at {path}")

    constructor = _IMPORT_MANAGER_CONSTRUCTORS.get(data_format)

    if constructor is None:
        raise KeyError(f"'{data_format}' is not an importable format")

    return constructor(path=path, template_table=template_table, *args, **kwargs)


def get_author() -> typing.Optional[User]:
    """
    Prompt the user for information on what user to use as the default author for importing

    Returns:
        An object representing the default author of imported templates
    """
    create_user = False
    username = input(f"Who should import these templates?{os.linesep}>>> ")

    if not User.objects.filter(username=username).exists():
        create_user = is_true(
            input(
                f"There are no users named '{username}' - "
                f"would you like to create them? (y/t/yes/1/true){os.linesep}>>> "
            )
        )

        if not create_user:
            print("Cannot import templates - a valid user must be provided to import", file=sys.stderr)
            sys.exit(255)

    password = getpass(f"Password for the '{username}'{os.linesep}>>> ")

    user = None

    if create_user:
        user = User.objects.create_user(username=username, password=password)
    else:
        maximum_times_to_ask = 3
        times_asked = 0

        while times_asked < maximum_times_to_ask:
            user = authenticate(username=username, password=password)

            if user is not None:
                break
            else:
                print(f"The password for '{username}' is incorrect", file=sys.stderr)
                times_asked += 1
                password = getpass(f"Try typing the password again{os.linesep}>>> ")

    return user


def import_templates(data_format: _DATA_FORMAT_TYPE, path: pathlib.Path, author: User = None, *args, **kwargs):
    """
    Import data of a given type at a given location into this Django instance's database

    Args:
        data_format: What the source data is formatted as
        path: Where the source data is
        author: The default user to act as the author if there is not one associated with it
        *args:
        **kwargs:
    """
    if not isinstance(author, User):
        author = get_author()

    if author is None:
        print(f"Cannot import templates - cannot validate user")
        sys.exit(255)

    template_manager = create_manager(data_format=data_format, path=path, *args, **kwargs)
    import_results = templates.import_templates(author=author, manager=template_manager)

    print("Templates imported:")
    print(import_results.format_as_text())


_OPERATIONS: typing.Dict[_ACTION_TYPE, typing.Callable] = {
    "export": export_templates,
    "import": import_templates,
}
"""
A mapping between an available action and the function that handles it
"""


class Command(BaseCommand):
    """
    A django management command used to operate upon SpecificationTemplates
    """
    help = "Import or Export templates for distribution"

    def add_arguments(self, parser: CommandParser):
        """
        Add required arguments to this command's command line parser

        Args:
            parser: The parser that interprets command line arguments
        """
        parser.add_argument("action", type=str, choices=_ACTIONS)
        parser.add_argument(
            "-f",
            "--format",
            type=str,
            dest="data_format",
            default=_DEFAULT_EXPORT_TYPE,
            choices=_DATA_FORMATS
        )

        parser.add_argument(
            "-p",
            "--path",
            dest="path",
            type=pathlib.Path,
            help="Where data should be imported from or exported to"
        )

        database_group = parser.add_argument_group("Database")
        database_group.add_argument(
            "-t",
            "--table",
            default="template",
            type=str,
            help="The name of the table holding template data within the given database"
        )

        export_group = parser.add_argument_group("Export")
        export_group.add_argument("-o", "--override", action="store_true", help="Override existing exports")

    def handle(
        self,
        *args,
        action: _ACTION_TYPE,
        data_format: _DATA_FORMAT_TYPE,
        path: pathlib.Path = None,
        table: str = None,
        override: bool = None,
        **options
    ):
        """
        Execute the intended logic for a user's CLI command

        Args:
            *args:
            action: What sort of action to perform
            data_format: The format for the template to operate on
            path: The path to where data should come from or go
            table: The name of the table to use if data is going to or from a database
            override: Whether to replace data
            **options:
        """
        if path is None and action == "import":
            print()
            print(f"Cannot import data without a path", file=sys.stderr)
            print()
            self.print_help(get_application_name(), get_command_name())
            sys.exit(1)

        if path is None:
            path = get_default_export_path(data_format=data_format)

        operation = _OPERATIONS.get(action)

        if operation is None:
            raise KeyError(f"'{action}' is not a valid operation for templates")

        operation(data_format=data_format, path=path, template_table=table, override=override)
