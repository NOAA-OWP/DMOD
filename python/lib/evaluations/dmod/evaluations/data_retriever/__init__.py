import pandas
import typing
import inspect
import os

from .. import specification

from .dataretriever import DataRetriever


__all__ = [
    os.path.splitext(package_file)[0]
    for package_file in os.listdir(os.path.dirname(__file__))
    if package_file != "__init__.py"
       and package_file != 'dataretriever.py'
]

from . import *


def get_datasource(datasource_definition: specification.DataSourceSpecification) -> DataRetriever:
    reader_map = {
        subclass.get_format_name().lower(): subclass
        for subclass in DataRetriever.__subclasses__()
        if not inspect.isabstract(subclass)
    }

    reader_format = datasource_definition.backend.format
    reader_class = reader_map.get(reader_format)

    if reader_class is None:
        raise KeyError(
                f"There are not data retrievers that read '{reader_format}' data."
                f"Check to make sure the correct format and spelling are given."
        )

    return reader_class(datasource_definition)


def read(datasource_definition: specification.DataSourceSpecification) -> pandas.DataFrame:
    """
    Get the data indicated by the DataSource definition
    Args:
        datasource_definition:
            A specification detailing what data to load
    Returns:
        A DataFrame containing the data that complies with the specification
    """
    retriever = get_datasource(datasource_definition)
    return retriever.get_data()

