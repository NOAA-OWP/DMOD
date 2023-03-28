"""
Provides classes and functions used to manipulated Evaluation specifications
"""
import typing

from dmod.evaluations import specification
from dmod.evaluations.specification import TemplateDetails
from dmod.evaluations.specification.template import TemplateManager

from .models import SpecificationTemplateCommunicator


class SpecificationTemplateManager(TemplateManager):
    """
    Object manager used to provide details about available templates defined within the Django DB instance
    """
    def get_specification_types(self) -> typing.Sequence[typing.Tuple[str, str]]:
        types: typing.List[typing.Tuple[str, str]] = list()

        for subclass in specification.TemplatedSpecification.__subclasses__():
            types.append((subclass.get_specification_type(), subclass.get_specification_description()))

        return types

    def get_templates(self, specification_type: str) -> typing.Sequence[TemplateDetails]:
        specification_type = specification_type.strip()
        return SpecificationTemplateCommunicator.filter(template_specification_type=specification_type)