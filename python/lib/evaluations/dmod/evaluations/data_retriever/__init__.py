import os

__all__ = [
    os.path.splitext(package_file)[0]
    for package_file in os.listdir(os.path.dirname(__file__))
    if package_file != "__init__.py"
]

from . import *

import pandas

import dmod.core.common as common

from .. import specification
from .. import retrieval


def get_datasource_retriever(datasource_definition: specification.DataSourceSpecification) -> retrieval.Retriever:
    reader_format = datasource_definition.backend.format.lower()

    readers = [
        cls
        for cls in common.get_subclasses(retrieval.Retriever)
        if cls.get_purpose().lower() == 'input_data'
           and cls.get_format().lower() == reader_format
    ]

    if not readers:
        raise KeyError(
                f"There are not data retrievers that read '{reader_format}' data."
                f"Check to make sure the correct format and spelling are given."
        )

    return readers[0](datasource_definition)


def read(datasource_definition: specification.DataSourceSpecification) -> pandas.DataFrame:
    """
    Get the data indicated by the DataSource definition
    Args:
        datasource_definition:
            A specification detailing what data to load
    Returns:
        A DataFrame containing the data that complies with the specification
    """
    retriever = get_datasource_retriever(datasource_definition)
    return retriever.retrieve()

