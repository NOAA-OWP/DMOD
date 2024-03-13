import os


__all__ = [
    os.path.splitext(package_file)[0]
    for package_file in os.listdir(os.path.dirname(__file__))
    if package_file not in ("__init__.py", 'retriever.py')
]

import pandas

import dmod.core.common as common
from dmod.core.common.collections import catalog

from .. import specification

from . import *

from .retriever import CrosswalkRetriever


def get_crosswalk(
    definition: specification.CrosswalkSpecification,
    input_catalog: catalog.InputCatalog
) -> CrosswalkRetriever:
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

    return possible_crosswalks[0](definition, input_catalog=input_catalog)


def get_data(definition: specification.CrosswalkSpecification, input_catalog: catalog.InputCatalog) -> pandas.DataFrame:
    crosswalk_retriever = get_crosswalk(definition, input_catalog=input_catalog)
    return crosswalk_retriever.retrieve()
