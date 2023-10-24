"""
Provides utility functions for importing or exporting Specification Templates
"""
from __future__ import annotations

import pathlib
import typing

from django.contrib.auth.models import User

from evaluation_service.models import SpecificationTemplate
from dmod.evaluations.specification import FileTemplateManager


class TemplateExporter:
    def to_database(self):
        pass

    def to_files(self):
        pass

    def to_archive(self):
        pass

class TemplateImporter:
    def __init__(self, user: User):
        self._user = user

    def from_database(self):
        pass

    def from_files(self, manifest_path: typing.Union[pathlib.Path, str]):
        pass