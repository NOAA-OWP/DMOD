"""
Provides classes that enable the representation and discovery of specification templates
"""
import abc
import json
import typing


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
    def get_templates(self, specification_type: str
    ) -> typing.Sequence[TemplateDetails]:
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