"""
Provides classes that enable the representation and discovery of specification templates
"""
import abc
import json
import pathlib
import typing

from ..util import clean_name


class TemplateDetails(abc.ABC):
    """
    A base class prescribing basic details about a template for specification objects
    """
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        The user configured name for the template
        """
        pass

    @property
    @abc.abstractmethod
    def specification_type(self) -> str:
        """
        What type of specification that this template is for
        """
        pass

    @abc.abstractmethod
    def get_configuration(self, decoder_type: typing.Type[json.JSONDecoder] = None) -> dict:
        """
        Get the deserialized configuration
        """
        pass

    @property
    @abc.abstractmethod
    def description(self) -> typing.Optional[str]:
        """
        A friendly description for what the template provides
        """
        pass

    @property
    def field_choice(self) -> typing.Tuple[str, str]:
        """
        A value-name pair that allows for templates to be selected from a dropdown
        """
        return self.name, self.name

    def __str__(self):
        return f"[{self.specification_type}] {self.name}{': ' + self.description if self.description else ''}"


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

    def get_template(
        self,
        specification_type: str,
        name: str,
        decoder_type: typing.Type[json.JSONDecoder] = None
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
        matches = [
            template.get_configuration(decoder_type=decoder_type)
            for template in self.get_templates(specification_type)
            if template.name == name
        ]

        if matches:
            return matches[0]

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


class FileTemplateDetails(TemplateDetails):
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


class FileTemplateManager(TemplateManager):
    def __init__(self, manifest_path: typing.Union[str, pathlib.Path]):
        self.__manifest: typing.Dict[str, typing.Dict[str, FileTemplateDetails]] = dict()
        self.__load_manifest(manifest_path)

    def __load_manifest(self, path: typing.Union[str, pathlib.Path]):
        manifest_path = pathlib.Path(path) if isinstance(path, str) else path

        if not manifest_path.exists():
            raise Exception(f"No template manifest could be found at '{manifest_path}'")

        with manifest_path.open('r') as manifest_file:
            manifest = json.load(manifest_file)

        manifest_directory = manifest_path.parent

        for specification_name, template_details in manifest.items():  # type: str, typing.List[typing.Dict[str, str]]
            if specification_name not in self.__manifest:
                self.__manifest[specification_name]: typing.Dict[str, FileTemplateDetails] = dict()

            for details in template_details:  # type: typing.Dict[str, str]
                name = details['name']
                template_path = manifest_directory / pathlib.Path(details['path'])
                template_path = template_path.resolve()

                if not template_path.exists():
                    raise ValueError(f"File Template Manifest cannot find the template named {name}")

                description = details.get("description")

                self.__manifest[specification_name][name] = FileTemplateDetails(
                    name=name,
                    specification_type=specification_name,
                    path=template_path,
                    description=description
                )

    def get_specification_types(self) -> typing.Sequence[typing.Tuple[str, str]]:
        types: typing.List[typing.Tuple[str, str]] = list()

        for specification_type in self.__manifest:
            types.append(
                (specification_type, clean_name(specification_type))
            )

        return types

    def get_templates(self, specification_type: str) -> typing.Sequence[TemplateDetails]:
        if specification_type not in self.__manifest:
            raise ValueError(f"There are no {specification_type}s configured within the File Template Manager")

        return [
            details
            for details in self.__manifest[specification_type].values()
        ]

