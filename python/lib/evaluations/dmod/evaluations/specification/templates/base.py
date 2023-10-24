"""
@TODO: Put a module wide description here
"""
from __future__ import annotations

import abc
import json
import typing



@typing.runtime_checkable
class GetSpecificationTypeProtocol(typing.Protocol):
    @classmethod
    def get_specification_type(cls) -> str:
        pass


@typing.runtime_checkable
class TemplateDetails(typing.Protocol):
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