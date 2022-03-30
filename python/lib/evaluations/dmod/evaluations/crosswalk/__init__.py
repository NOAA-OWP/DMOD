#!/usr/bin/env python3
import typing

from .. import specification

from . import reader
from . import disk
from .retriever import CrosswalkRetriever

__CROSSWALK_TYPE_MAP = {
    "file": disk
}


def get_crosswalk(definition: specification.CrosswalkSpecification) -> CrosswalkRetriever:
    crosswalk = None

    if definition.backend.type.lower() in __CROSSWALK_TYPE_MAP:
        mod = __CROSSWALK_TYPE_MAP[definition.backend.type.lower()]
        crosswalk = mod.get_retriever(definition)

    if crosswalk is None:
        raise TypeError(f"'{definition.backend.type}' is not a supported type of crosswalk source.")

    return crosswalk
