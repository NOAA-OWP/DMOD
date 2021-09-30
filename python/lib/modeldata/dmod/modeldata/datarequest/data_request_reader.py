from . import DataRequestDefinition

from datetime import datetime


class DataRequestReader:

    def __init__(self, json_data: dict):
        """

        :param json_data: A dictionary containing the following keys
            data_source: (string) the data source to request from
            start_date: The first date time in the request
            stop_date: The last date time in the request
            variables: A list of required variables for the request
        """

        data_source = json_data['data_sources']
        start_date = datetime.strptime(json_data['start_dates'], "%m/%d/%y: %H:%M:%S %Z")
        stop_date = datetime.strptime(json_data['stop_dates'], "%m/%d/%y: %H:%M:%S %Z")
        variables = json_data['variables']

        self.request = DataRequestDefinition(data_source, start_date, stop_date, variables)
