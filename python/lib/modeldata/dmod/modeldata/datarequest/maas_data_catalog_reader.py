import json

from . import MaaSDataCatalog

class MaaSDataCatalogReader:

    def __init__(self, catalog_file):
        """

        :param jsonfile: A file containing a valid json encoding for a MaaS Catalog
        """

        json_data = json.load(catalog_file)

        data_sources = json_data['data_sources']
        start_dates = json_data['start_dates']
        stop_dates = json_data['stop_dates']
        variables = json_data['variables']

        self.catalog = MaaSDataCatalog(data_sources, start_dates, stop_dates, variables)
