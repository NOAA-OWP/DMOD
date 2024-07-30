
class MaaSDataCatalog:

	def __init__(self, sources : list, start_dates : map, stop_dates : map, variables : map):
		"""
		Parameters
		----------------------
		self: the Catalog Object being created
		sources: a list of data source names
		start_dates: a map containing the start date for each data source in sources
		stop_dates: a map containg the stop date for each data source in sources
		variables: a map containing the recorded variables for each data source in sources
		:rtype: object

		"""

		self.data_sources = sources
		self.start_dates = start_dates
		self.stop_dates = stop_dates
		self.variables = variables
