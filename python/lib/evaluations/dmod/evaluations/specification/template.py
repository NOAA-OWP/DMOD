"""
Provides classes that enable the representation and discovery of specification templates
"""
from __future__ import annotations
import abc
import json
import pathlib
import typing
from collections import defaultdict

from dmod.core.common import humanize_text
from dmod.core.common.types import TextValue

from .templates import FileTemplateManifest
from .templates import TemplateDetails
from .templates import GetSpecificationTypeProtocol


class TemplateManager(abc.ABC):
    @abc.abstractmethod
    def get_specification_types(self) -> typing.Sequence[typing.Tuple[str, str]]:
        """
        Get a list of value-name pairs for use when building HTML selectors

        Both elements should be the name of a configuration specification that supports templates

        Returns:
            A list of value-name pairs tying the name of a configuration specification to a friendly name for a configuraiton specification
        """
        pass

    @abc.abstractmethod
    def get_templates(self, specification_type: str) -> typing.Sequence[TemplateDetails]:
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
        specification_type: typing.Union[str, GetSpecificationTypeProtocol],
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

    def get_options(self, specification_type: str) -> typing.Sequence[typing.Tuple[str, str]]:
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

    def export_to_database(self, directory: typing.Union[str, pathlib.Path]) -> pathlib.Path:
        raise Exception(
            f"Database Exports have not been implemented for '{self.__class__.__name__}' template managers"
        )

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
        raise Exception(
            f"File Exports have not been implemented for '{self.__class__.__name__}' template managers"
        )

    def export_to_archive(self, directory: typing.Union[str, pathlib.Path]) -> pathlib.Path:
        raise Exception(
            f"Archive Exports have not been implemented for '{self.__class__.__name__}' template managers"
        )


class FileTemplateManager(TemplateManager):
    def __init__(self, manifest_path: typing.Union[str, pathlib.Path]):
        manifest_path = pathlib.Path(manifest_path) if isinstance(manifest_path, str) else manifest_path
        with manifest_path.open('r') as manifest_file:
            manifest_data = json.load(manifest_file)
        self.manifest: FileTemplateManifest = FileTemplateManifest.parse_obj(manifest_data)
        self.manifest.set_root_directory(manifest_path.parent)
        self.manifest.ensure_validity()

    def get_specification_types(self) -> typing.Sequence[typing.Tuple[str, str]]:
        types: typing.List[typing.Tuple[str, str]] = list()

        for specification_type in self.manifest.keys():
            types.append(
                (specification_type, humanize_text(specification_type, exclude_phrases='Specification'))
            )

        return types

    def get_templates(self, specification_type: str) -> typing.Sequence[TemplateDetails]:
        if specification_type not in self.manifest:
            raise ValueError(f"There are no {specification_type}s configured within the File Template Manager")

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

