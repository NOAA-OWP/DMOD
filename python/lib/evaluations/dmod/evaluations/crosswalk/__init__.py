#!/usr/bin/env python3
import os


__all__ = [
    os.path.splitext(package_file)[0]
    for package_file in os.listdir(os.path.dirname(__file__))
    if package_file != "__init__.py"
       and package_file != 'retriever.py'
]

from . import *

import pandas

import dmod.core.common as common

from .. import specification

from .retriever import CrosswalkRetriever


def get_crosswalk(definition: specification.CrosswalkSpecification) -> CrosswalkRetriever:
    possible_crosswalks = [
        cls for cls in common.get_subclasses(CrosswalkRetriever)
        if cls.get_type().lower() == definition.backend.backend_type.lower()
           and cls.get_format().lower() == definition.backend.format.lower()
    ]

    if not possible_crosswalks:
        raise TypeError(
                f"'{definition.backend.format}' from '{definition.backend.backend_type}' is not a "
                f"supported type of crosswalk source."
        )

    return possible_crosswalks[0](definition)


def get_data(definition: specification.CrosswalkSpecification) -> pandas.DataFrame:
    crosswalk_retriever = get_crosswalk(definition)
    return crosswalk_retriever.retrieve()
