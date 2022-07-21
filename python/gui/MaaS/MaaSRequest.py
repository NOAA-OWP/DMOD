"""
Lays out details describing how a request may be created and the different types of requests

@author: Chris Tubbs
"""

from dmod.communication import ExternalRequest


class XYZRequest(ExternalRequest):
    """
    Represents requests that may be made to the XYZ model
    """
    model_name = 'XYZ'
    """(:class:`str`) The name of the model to be used"""

    parameters = [
        'hydraulic_conductivity',
        'land_cover',
        'nudge'
    ]
    """(:class:`list`) The collection of parameters to use"""

    output_variables = [
        'streamflow',
        'precipitation'
    ]
    """(:class:`list`) The collection of output variables that the model may generate"""

    max_distribution = 15
    """(:class:`int`) The maximum value for a distribution for a parameter that the model may handle"""

    min_distribution = -2
    """(:class:`int`) The minimum value for a distribution for a parameter that the model may handle"""

    min_scalar = 0
    """(:class:`int`) The minimum scalar value for a parameter that the model may handle"""

    max_scalar = 5
    """(:class:`int`) The maximum scalar value for a parameter that the model may handle"""

    distribution_types = [
        'normal',
    ]
    """(:class:`list`) The collection of distribution types that the model may handle"""

    def __init__(self, session_secret: str, version: float = 0.0, output: str = 'streamflow', parameters: dict = None):
        super(XYZRequest, self).__init__(version=version, output=output, parameters=parameters,
                                         session_secret=session_secret)


class YetAnotherRequest(ExternalRequest):
    """
    Represents requests that may be made for the YetAnother model
    """
    model_name = 'YetAnother'
    """(:class:`str`) The name of the model to be used"""

    parameters = [
        'This',
        'Is',
        'An',
        'Example'
    ]
    """(:class:`list`) The collection of parameters to use"""

    output_variables = [
        'chance_of_earthquake',
        'rain_chance'
    ]
    """(:class:`list`) The collection of output variables that the model may generate"""

    max_distribution = 15
    """(:class:`int`) The maximum value for a distribution for a parameter that the model may handle"""

    min_distribution = -2
    """(:class:`int`) The minimum value for a distribution for a parameter that the model may handle"""

    min_scalar = 0
    """(:class:`int`) The minimum scalar value for a parameter that the model may handle"""

    max_scalar = 5
    """(:class:`int`) The maximum scalar value for a parameter that the model may handle"""

    distribution_types = [
        'normal',
        'wonky',
        'exponential'
    ]
    """(:class:`list`) The collection of distribution types that the model may handle"""

    def __init__(self, session_secret: str, version: float = 0.0, output: str = 'streamflow', parameters: dict = None):
        super(YetAnotherRequest, self).__init__(version=version, output=output, parameters=parameters,
                                                session_secret=session_secret)
