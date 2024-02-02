"""
Provides classes and functions used to manipulated Evaluation specifications
"""
import pathlib
import json
import os
import typing
import sqlite3
import re

from dmod.core.common import DBAPIConnection
from collections import defaultdict

from django.contrib.auth.models import User
from dmod.evaluations import specification
from dmod.evaluations.specification import TemplateDetails
from dmod.evaluations.specification.template import GetSpecificationTypeProtocol
from dmod.evaluations.specification.template import TemplateManager

from .models import SpecificationTemplate
from .models import SpecificationTemplateCommunicator

VALUE_OPERATION = re.compile("^[a-zA-Z0-9_]+__[a-zA-Z_]+$")


class SpecificationTemplateManager(TemplateManager):
    """
    Object manager used to provide details about available templates defined within the Django DB instance
    """
    def __init__(self, *args, **kwargs):
        pass

    def get_specification_types(self) -> typing.Sequence[typing.Tuple[str, str]]:
        types: typing.List[typing.Tuple[str, str]] = list()

        for subclass in specification.TemplatedSpecification.__subclasses__():
            types.append((subclass.get_specification_type(), subclass.get_specification_description()))

        return types

    def search(
        self,
        specification_type: str = None,
        name: str = None,
        author: str = None,
        **kwargs
    ) -> typing.Mapping[str, typing.Sequence[TemplateDetails]]:
        query_parameters = dict()

        if specification_type:
            query_parameters["template_specification_type__icontains"] = specification_type

        if name:
            query_parameters["template_name__icontains"] = name

        if author:
            query_parameters['author__username__icontains'] = author

        query_parameters.update(kwargs)

        if query_parameters:
            matching_templates = SpecificationTemplateCommunicator.filter(**query_parameters)
        else:
            matching_templates = SpecificationTemplateCommunicator.all()

        filtered_templates = defaultdict(list)

        for matching_template in matching_templates:
            filtered_templates[matching_template.template_specification_type].append(matching_template)

        return filtered_templates

    def get_templates(self, specification_type: str) -> typing.Sequence[SpecificationTemplate]:
        specification_type = specification_type.strip()
        return SpecificationTemplateCommunicator.filter(template_specification_type=specification_type)

    def get_all_templates(self) -> typing.Mapping[str, typing.Sequence[TemplateDetails]]:
        templates: typing.Dict[str, typing.List[TemplateDetails]] = defaultdict(list)

        for template_specification in SpecificationTemplateCommunicator.all():
            templates[template_specification.specification_type].append(template_specification.to_details())

        return templates

    def export_to_database(
        self,
        table_name: str,
        database_connection: typing.Union[DBAPIConnection, pathlib.Path, str],
        exists_ok: bool = None
    ):
        if isinstance(database_connection, (str, pathlib.Path)):
            database_connection = sqlite3.connect(database_connection)

        return super().export_to_database(table_name, database_connection, exists_ok)

    def get_template(
        self,
        specification_type: typing.Union[str, GetSpecificationTypeProtocol],
        name: str,
        *,
        decoder_type: typing.Type[json.JSONDecoder] = None,
        author: typing.Union[str, User] = None,
        **kwargs
    ) -> typing.Optional[dict]:
        if isinstance(author, str):
            possible_authors = User.objects.filter(username=author)
            if not possible_authors:
                return None
            author = possible_authors.first()
        elif not isinstance(author, User):
            author = None

        if isinstance(specification_type, GetSpecificationTypeProtocol):
            specification_type = specification_type.get_specification_type()

        query_parameters = {
            "template_name__iexact": name,
            "template_specification_type": specification_type
        }

        if isinstance(author, User):
            query_parameters['author'] = author

        for key, value in kwargs.items():
            if key != author and not key.startswith("template_"):
                key = "template_" + key

            if isinstance(value, str) and not VALUE_OPERATION.search(key):
                query_parameters[key + "__icontains"] = value
            else:
                query_parameters[key] = value

        matching_templates = SpecificationTemplateCommunicator.filter(**query_parameters)
        if len(matching_templates) > 1:
            message = f"Search parameters were too general and too many templates were found. " \
                      f"Choose one of the following:{os.linesep}"
            message = f"{message}{(os.linesep + '    - ').join([str(template) for template in matching_templates])}"
            raise KeyError(message)

        if matching_templates:
            return matching_templates[0].template_configuration

        return None
