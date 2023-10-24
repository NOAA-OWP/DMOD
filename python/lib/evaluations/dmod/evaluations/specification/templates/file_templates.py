"""
@TODO: Put a module wide description here
"""
from __future__ import annotations

import json
import logging
import pathlib
import re
import shutil
import typing
import tempfile

import pydantic
from dmod.core.common.collection import CollectionEvent
from dmod.core.common.collection import MapModel
from dmod.core.common.collection import SequenceModel

from . import base

StringOrInt = typing.Union[str, int]
StringOrIntToAnything = typing.Mapping[StringOrInt, typing.Any]
SetOfStringsOrInts = typing.Set[StringOrInt]


class FileTemplateDetails(base.TemplateDetails):
    def __init__(self, name: str, specification_type: str, description: str, path: pathlib.Path):
        self.__name = name
        self.__specification_type = specification_type
        self.__description = description
        self.__path = path

    @property
    def name(self) -> str:
        return self.__name

    @property
    def specification_type(self) -> str:
        return self.__specification_type

    def get_configuration(self, decoder_type: typing.Type[json.JSONDecoder] = None) -> dict:
        with self.__path.open('r') as configuration_file:
            return json.load(fp=configuration_file, cls=decoder_type)

    @property
    def description(self) -> typing.Optional[str]:
        return self.__description

    @property
    def path(self) -> pathlib.Path:
        return self.__path

    def dict(self) -> typing.Dict[str, typing.Union[str, pathlib.Path]]:
        return {
            "name": self.name,
            "specification_type": self.specification_type,
            "description": self.description,
            "path": self.path
        }


def serialize_path(path: pathlib.Path, *args, **kwargs) -> str:
    return str(path)


class FileTemplateManifestEntry(pydantic.BaseModel):
    name: str
    path: pathlib.Path
    description: str
    specification_type: typing.Optional[str]

    _root_directory: typing.Optional[pathlib.Path] = pydantic.PrivateAttr(None)

    class Config:
        json_encoders = {
            "path": serialize_path
        }

    def as_details(self) -> FileTemplateDetails:
        return FileTemplateDetails(
            name=self.name,
            specification_type=self.specification_type,
            description=self.description,
            path=self.full_path()
        )

    @property
    def kwargs(self) -> typing.Dict[str, typing.Union[str, pathlib.Path]]:
        if self.specification_type is None:
            raise ValueError(
                f"Cannot retrieve arguments for a manifest entry named '{self.name}' at '{self.path}' - "
                f"Make sure 'specification_type' is populated on all Manifest Entries"
            )

        return {
            "name": self.name,
            "path": self.path,
            "description": self.description,
            "specification_type": self.specification_type
        }

    def set_root_directory(self, directory: pathlib.Path):
        self._root_directory = directory

    def get_configuration(self, decoder_type: typing.Type[json.JSONDecoder] = None) -> dict:
        with self.full_path().open('r') as configuration_file:
            return json.load(fp=configuration_file, cls=decoder_type)

    def full_path(self) -> pathlib.Path:
        if self._root_directory and not self.path.is_absolute():
            path = self._root_directory / self.path
            path = path.resolve()
        else:
            path = self.path

        return path

    def save(
        self,
        configuration: typing.Union[dict, str] = None,
        path: typing.Union[pathlib.Path, str] = None
    ):
        if isinstance(path, str):
            path = pathlib.Path(path)
        elif path is None:
            path = self.full_path()

        path.parent.mkdir(parents=True, exist_ok=True)
        if configuration is None:
            configuration = self.get_configuration()

        if isinstance(configuration, str):
            path.write_text(data=configuration)
        else:
            with path.open('w') as configuration_file:
                json.dump(obj=configuration, fp=configuration_file, indent=4)

    @property
    def exists(self) -> bool:
        """
        Returns:
            Whether this template exists
        """
        return self.full_path().exists()

    def __eq__(self, other):
        if not isinstance(other, FileTemplateManifestEntry):
            return False

        return self.name == other.name and self.path == other.path

    def __gt__(self, other):
        return isinstance(other, FileTemplateManifestEntry) and self.path > other.path

    def __lt__(self, other):
        return isinstance(other, FileTemplateManifestEntry) and self.path < other.path

    def __ge__(self, other):
        return isinstance(other, FileTemplateManifestEntry) and self.path >= other.path

    def __le__(self, other):
        return isinstance(other, FileTemplateManifestEntry) and self.path <= other.path

    def dict(
        self,
        *,
        include: typing.Union[SetOfStringsOrInts, StringOrIntToAnything] = None,
        exclude: typing.Union[SetOfStringsOrInts, StringOrIntToAnything] = None,
        by_alias: bool = False,
        skip_defaults: typing.Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> typing.Dict[str, any]:
        if exclude is None:
            exclude = set()

        if isinstance(exclude, typing.Set) and 'specification_type' not in exclude:
            exclude.add('specification_type')

        return super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none
        )


class FileTemplateManifestEntries(SequenceModel[FileTemplateManifestEntry]):
    _root_directory: typing.Optional[pathlib.Path] = pydantic.PrivateAttr(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_handler(
            CollectionEvent.INSERT,
            lambda entries, index, value: value.set_root_directory(entries.root_directory)
        )
        self.add_handler(
            CollectionEvent.ADD,
            lambda entries, value: value.set_root_directory(entries.root_directory)
        )

    def save(self, directory: typing.Union[str, pathlib.Path]):
        directory = pathlib.Path(directory) if isinstance(directory, str) else directory

        directory.mkdir(exist_ok=True, parents=True)

        for entry in self.values:
            new_path = directory / entry.path
            entry.save(path=new_path)

    @property
    def missing_templates(self) -> typing.Sequence[FileTemplateManifestEntry]:
        return [
            entry
            for entry in self.values
            if not entry.exists
        ]

    def as_details(self) -> typing.Sequence[FileTemplateDetails]:
        return [
            entry.as_details()
            for entry in self.values
        ]

    @property
    def root_directory(self) -> typing.Optional[pathlib.Path]:
        return self._root_directory

    def set_root_directory(self, directory: pathlib.Path):
        self._root_directory = directory
        for entry in self.values:
            entry.set_root_directory(directory)

    def set_specification_type(self, specification_type: str):
        for entry in self.values:
            entry.specification_type = specification_type

    def __getitem__(self, index: typing.Union[str, slice, int]) -> FileTemplateManifestEntry:
        if isinstance(index, str):
            for entry in self.values:
                if entry.name == index:
                    return entry
            raise KeyError(f"There are no Manifest Entries with a name of '{index}'")
        return super().__getitem__(index)


class FileTemplateManifest(MapModel[str, FileTemplateManifestEntries]):
    _root_directory: typing.Optional[pathlib.Path] = pydantic.PrivateAttr(None)

    def ensure_validity(self):
        """
        Throw an error if templates are missing
        """
        missing_templates: typing.List[FileTemplateManifestEntry] = []

        for specification_type, entries in self.items():
            entries.set_specification_type(specification_type)
            missing_templates.extend(entries.missing_templates)

    def set_root_directory(self, directory: pathlib.Path):
        for entries in self.values():
            entries.set_root_directory(directory)

    def add(self, entry: FileTemplateManifestEntry) -> FileTemplateManifest:
        if entry.specification_type not in self.__root__.keys():
            self.__root__[entry.specification_type] = FileTemplateManifestEntries()
        self.__root__[entry.specification_type].append(entry)
        return self

    def save(self, directory: typing.Union[str, pathlib.Path]) -> pathlib.Path:
        directory = pathlib.Path(directory) if isinstance(directory, str) else directory

        manifest_path = directory / "template_manifest.json"

        with manifest_path.open('w') as manifest_file:
            manifest_file.write(self.json(indent=4))

        for specification_type, templates in self.items():
            templates.save(directory)

        return manifest_path

    def archive(self, output_path: typing.Union[pathlib.Path, str]) -> pathlib.Path:
        if isinstance(output_path, pathlib.Path):
            output_path = str(output_path)

        with tempfile.TemporaryDirectory() as output_directory:
            saved_directory = self.save(directory=output_directory).parent

            # Defined separately from the function call in case the use case for different formats is desired
            archive_format = "zip"

            archive_pattern = re.compile(r"\.(zip|tar|gz|gztar|bztar|xztar)$")
            non_zip_pattern = re.compile(r"\.(tar|gz|gztar|bztar|xztar)$")

            while archive_pattern.search(output_path) is not None:
                non_zip_extension = non_zip_pattern.search(output_path)

                if non_zip_extension is not None:
                    desired_archive_type = non_zip_extension.group()
                    logging.warning(
                        f"A request to archive templates to a {desired_archive_type} file was given - "
                        f"all template archives are saved as zip files to maintain near-universal compatibility. "
                        f"The desired {desired_archive_type} archive type will not be used."
                    )

                output_path = archive_pattern.sub("", output_path)

            archive_path = shutil.make_archive(
                output_path,
                format=archive_format,
                root_dir=saved_directory,
                base_dir="./",
                verbose=True
            )

            return pathlib.Path(archive_path)

    def __eq__(self, other: FileTemplateManifest) -> bool:
        if not isinstance(other, FileTemplateManifest):
            return False

        if len(self) != len(other):
            return False

        for specification_type, entries in self.items():
            if specification_type not in other:
                return False

            other_entries = other[specification_type]

            if len(entries) != len(other_entries):
                return False

            if not entries == other_entries:
                return False

        return True
