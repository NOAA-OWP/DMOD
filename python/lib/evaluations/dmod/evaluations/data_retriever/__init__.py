import os

import pandas

from dmod.core.common.collections import catalog
from dmod.core import common

from .. import specification
from .. import retrieval

files_in_package = [
    package_file
    for package_file in os.listdir(os.path.dirname(__file__))
    if package_file != "__init__.py"
]

__all__ = [
    os.path.splitext(package_file)[0]
    for package_file in files_in_package
]


def get_datasource_retriever(
    datasource_definition: specification.DataSourceSpecification,
    input_catalog: catalog.InputCatalog
) -> retrieval.Retriever[specification.DataSourceSpecification]:
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

    return readers[0](datasource_definition, input_catalog=input_catalog)


def read(
    datasource_definition: specification.DataSourceSpecification,
    input_catalog: catalog.InputCatalog
) -> pandas.DataFrame:
    """
    Get the data indicated by the DataSource definition
    Args:
        datasource_definition:
            A specification detailing what data to load
        input_catalog: A shared catalog of loaded input data
    Returns:
        A DataFrame containing the data that complies with the specification
    """
    retriever = get_datasource_retriever(datasource_definition, input_catalog=input_catalog)
    return retriever.retrieve()
