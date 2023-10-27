"""
@TODO: Put a module wide description here
"""
from __future__ import annotations

import typing
import pathlib

from django.core.management import BaseCommand
from django.core.management import CommandParser

import evaluation_service.data.templates as templates

class Command(BaseCommand):
    help = "Export templates for distribution"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("action", type=str, choices=["import", "export"])
        parser.add_argument("format", type=str, choices=["database", "file", "archive"])
        parser.add_argument("path", type=pathlib.Path, help="Where data should be imported from or exported to")

    def import_template(self):
        pass

    def export_template(self):
        pass

    def handle(self, *args, **options):
        pass