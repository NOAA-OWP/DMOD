from queue import Queue
from typing import Collection, Optional, Set, Tuple, Union
from . import MaaSDataCatalog, MaaSDataCatalogReader, DataRequestDefinition


class DataRequestHandler:

    @classmethod
    def factory_create_from_geojson(cls, catalog_json) -> 'DataRequestHandler':

        catalog = MaaSDataCatalogReader(catalog_json).catalog
        return cls(catalog=catalog)

    def __init__(self, catalog):
        """

        Parameters
        ----------
        hydrofabric
            The hydrofabric of catchments and nexuses
        """
        self._catalog = catalog

    def validate(self, request: DataRequestDefinition) -> Tuple[bool, Optional[str]]:
        """
        Validate the request and give feedback if invalid.

        Check whether the given data request is valid and, in the case when the data request is invalid, obtain at least a partial
        description of why it is invalid.  Return these as a tuple.

        Parameters
        ----------
        request : DataRequestDefinition
            A an object specifying the required data source, date-range, and variables.

        Returns
        -------
        Tuple[bool, Optional[str]]
            Whether the data request is valid and, if not, a partial description of why not (or ``None`` if it is valid).

        """

        description = None
        if request.source not in self._catalog.data_sources:
            description = "Invalid data source"
        elif request.start_date < self._catalog.start_date[request.source] or request.stop_date > \
                self._catalog.stop_date[request.source]:
            description = "invalid date range for requested data source."
        elif not all(e in self._catalog.variables[request.source] for e in request.variables):
            description = "data source does not contain required variables."

        return description is None, description
