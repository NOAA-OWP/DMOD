from datetime import datetime

class DataRequestDefinition:

    def __init__(self, source: str, start_date: datetime, stop_date: datetime, variables: list):
        """
        Parameters
        ----------------------
        self: the Catalog Object being created
        sources: the name of the request data source
        start_date: first date of requested data
        stop_date: last date of requested data
        variables: required variables

        """

        self.source = source
        self.start_date = start_date
        self.stop_date = stop_date
        self.variables = variables
