#!/usr/bin/env python3
import typing
import os
import inspect

import pandas

from .. import specification
from .. import util

from . import reader
from .retriever import CrosswalkRetriever


__all__ = [
    os.path.splitext(package_file)[0]
    for package_file in os.listdir(os.path.dirname(__file__))
    if package_file != "__init__.py"
       and package_file != 'retriever.py'
]

from . import *


def get_crosswalk(definition: specification.CrosswalkSpecification) -> CrosswalkRetriever:
    possible_crosswalks = [
        cls for cls in util.get_subclasses(CrosswalkRetriever)
        if cls.get_type().lower() == definition.backend.type.lower()
           and cls.get_format().lower() == definition.backend.format.lower()
    ]

    if not possible_crosswalks:
        raise TypeError(
                f"'{definition.backend.format}' from '{definition.backend.type}' is not a "
                f"supported type of crosswalk source."
        )

    return possible_crosswalks[0](definition)


def get_data(definition: specification.CrosswalkSpecification) -> pandas.DataFrame:
    crosswalk_retriever = get_crosswalk(definition)
    return crosswalk_retriever.retrieve()
