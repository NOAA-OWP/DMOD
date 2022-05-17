#!/usr/bin/env python3
import typing
import os
import inspect

import pandas

from .. import specification

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
    crosswalk_map = {
        (subclass.get_type().lower(), subclass.get_format().lower()): subclass
        for subclass in CrosswalkRetriever.__subclasses__()
        if not inspect.isabstract(subclass)
    }

    crosswalk = crosswalk_map.get((definition.backend.type.lower(), definition.backend.format.lower()))

    if crosswalk is None:
        raise TypeError(
                f"'{definition.backend.format}' from '{definition.backend.type}' is not a "
                f"supported type of crosswalk source."
        )

    return crosswalk(definition)


def get_data(definition: specification.CrosswalkSpecification) -> pandas.DataFrame:
    crosswalk_retriever = get_crosswalk(definition)
    return crosswalk_retriever.retrieve()
