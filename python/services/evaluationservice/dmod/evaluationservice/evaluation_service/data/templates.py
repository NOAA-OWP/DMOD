"""
Provides utility functions for importing or exporting Specification Templates
"""
from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import typing
from collections import defaultdict

from django.contrib.auth.models import User
from dmod.core.common import DBAPIConnection
from dmod.core.common import flat
from dmod.evaluations.specification import TemplateDetails

from dmod.evaluations.specification import TemplateManager

from evaluation_service.models import SpecificationTemplateCommunicator
from evaluation_service.specification import SpecificationTemplateManager


@dataclasses.dataclass
class TemplateImportResults:
    templates_added: typing.Sequence[TemplateDetails]
    templates_updated: typing.Sequence[TemplateDetails]

    def amount_added(self) -> int:
        return len(self.templates_added)

    def amount_updated(self) -> int:
        return len(self.templates_updated)

    def format_as_text(self) -> str:
        added_templates: typing.Iterable[str] = map(str, self.templates_added)
        updated_templates: typing.Iterable[str] = map(str, self.templates_updated)

        message = "Templates Added:" + os.linesep + "    "
        message += f"{os.linesep}    ".join(added_templates)
        message += os.linesep
        message += os.linesep
        message += "Templates Updated:" + os.linesep + "    "
        message += f"{os.linesep}    ".join(updated_templates)

        return message

    def __str__(self):
        return f"Templates: [Added: {self.templates_added}, Updated: {self.templates_updated}]"

    def __repr__(self):
        return self.__str__()


def import_templates(user: User, manager: TemplateManager) -> TemplateImportResults:
    templates_to_add_or_update = flat(manager.get_all_templates().values())
    templates_updated: typing.List[TemplateDetails] = list()
    templates_added: typing.List[TemplateDetails] = list()

    for template in templates_to_add_or_update:
        instance, created = SpecificationTemplateCommunicator.update_or_create(
            template_name=template.name,
            template_specification_type=template.specification_type,
            author=user,
            defaults={
                "template_description": template.description,
                "template_configuration": template.get_configuration()
            }
        )

        if created:
            templates_added.append(instance.to_details())
        else:
            templates_updated.append(instance.to_details())

    return TemplateImportResults(templates_added=templates_added, templates_updated=templates_updated)


def export_to_db(table_name: str, connection: DBAPIConnection, exists_ok: bool = None):
    manager: TemplateManager = SpecificationTemplateManager()
    manager.export_to_database(table_name=table_name, connection=connection, exists_ok=exists_ok)


def export_to_file(output_directory: typing.Union[pathlib.Path, str]) -> pathlib.Path:
    manager: TemplateManager = SpecificationTemplateManager()
    return manager.export_to_file(output_directory)


def export_to_archive(output_path: typing.Union[pathlib.Path, str]) -> pathlib.Path:
    manager: TemplateManager = SpecificationTemplateManager()
    return manager.export_to_archive(output_path)