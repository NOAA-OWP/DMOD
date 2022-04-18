"""
Lays out details describing how a request may be created and the different types of requests

@author: Chris Tubbs
"""

from .message import AbstractInitRequest, MessageEventType, Response, InitRequestResponseReason
from dmod.core.meta_data import ContinuousRestriction, DataCategory, DataDomain, DataFormat, DiscreteRestriction, DataRequirement, TimeRange
from abc import ABC, abstractmethod
from numbers import Number
from typing import Dict, List, Optional, Set, Union


def get_available_models() -> dict:
    """
    :return: The names of all models mapped to their class
    """
    available_models = dict()

    for subclass in ModelExecRequest.__subclasses__():  # type: ModelExecRequest
        available_models[subclass.model_name] = subclass

    return available_models


def get_available_outputs() -> set:
    """
    :return: A collection of all valid outputs across any model
    """
    all_outputs = set()

    for model in get_available_models().values():  # type: ModelExecRequest
        all_outputs = all_outputs.union(set(model.get_output_variables()))

    return all_outputs


def get_distribution_types() -> set:
    """
    :return: The distribution types used across any model
    """
    all_types = set()

    for model in get_available_models().values():
        all_types = all_types.union(set(model.get_distribution_types()))

    return all_types


class Scalar(object):
    """
    Represents a parameter value that is bound to a single number
    """
    def __init__(self, scalar: int):
        """
        :param int scalar: The value for the parameter
        """
        self.scalar = scalar

    def to_dict(self):
        return {'scalar': self.scalar}

    def __str__(self):
        return str(self.scalar)

    def __repr__(self):
        return self.__str__()


class Distribution(object):
    """
    Represents the definition of a distribution of numbers
    """
    def __init__(self, minimum: int = 0, maximum: int = 0, distribution_type: str = 'normal'):
        """
        :param int minimum: The lower bound for the distribution
        :param int maximum: The upper bound of the distribution
        :param str distribution_type: The type of the distribution
        """
        self.minimum = minimum
        self.maximum = maximum
        self.distribution_type = distribution_type

    def to_dict(self):
        return {'distribution': {'min': self.minimum, 'max': self.maximum, 'type': self.distribution_type}}

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return self.__str__()


class MaaSRequest(AbstractInitRequest, ABC):
    """
    The base class underlying all types of MaaS requests
    """

    @classmethod
    @abstractmethod
    def factory_init_correct_response_subtype(cls, json_obj: dict):
        """
        Init a :obj:`Response` instance of the appropriate subtype for this class from the provided JSON object.

        Parameters
        ----------
        json_obj

        Returns
        -------

        """
        pass

    def __init__(self, session_secret: str):
        self.session_secret = session_secret

    def _check_class_compatible_for_equality(self, other) -> bool:
        """
        Check and return whether another object is of some class that is compatible for equality checking with the class
        of this instance, such that the class difference does not independently imply the other object and this instance
        are not equal.

        In the base implementation, the method returns True if and only if the class of the parameter object is equal to
        the class of the receiver object.

        Overriding implementations must always ensure the method returns True when the parameter has the same class
        value as the receiver object.

        Further, overriding implementations should ensure the method remains symmetric across implementations; i.e., for
        any objects x and y where both object have an implementation of this method as a member, then the following
        should always be True:

            x._check_class_compatible_for_equality(y) == y._check_class_compatible_for_equality(x)

        Parameters
        ----------
        other

        Returns
        -------
        type_compatible_for_equality : bool
            whether the class of the other object is not independently sufficient for a '==' check between this and the
            other object to return False
        """
        try:
            return other is not None and self.__class__ == other.__class__
        except:
            return False


# TODO: this type, the subtypes (especially for NWM), all things using it, etc., need to be completely overhauled;
#  instead of itself containing all necessary params, it should reference a config dataset that defines the params
class ModelExecRequest(MaaSRequest, ABC):
    """
    The base class underlying MaaS requests for model execution jobs.
    """

    event_type: MessageEventType = MessageEventType.MODEL_EXEC_REQUEST

    model_name = None
    """(:class:`str`) The name of the model to be used"""

    parameters = [
        'hydraulic_conductivity',
        'land_cover'
    ]
    """(:class:`list`) The collection of parameters to use"""

    max_distribution = 0
    """(:class:`int`) The maximum value for a distribution for a parameter that the model may handle"""

    min_distribution = 10
    """(:class:`int`) The minimum value for a distribution for a parameter that the model may handle"""

    min_scalar = 0
    """(:class:`int`) The minimum scalar value for a parameter that the model may handle"""

    max_scalar = 10
    """(:class:`int`) The maximum scalar value for a parameter that the model may handle"""

    distribution_types = [
        'normal',
        'lognormal'
    ]
    """(:class:`list`) The collection of distribution types that the model may handle"""

    output_variables = [
        'streamflow'
    ]
    """(:class:`list`) The collection of output variables that the model may generate"""

    @classmethod
    def factory_init_correct_subtype_from_deserialized_json(cls, json_obj: dict):
        """
        Much like :meth:`factory_init_from_deserialized_json`, except (sub)type agnostic, allowing this to determine the
        correct type of :class:`MaasRequest` from the contents of the JSON, and return a call to that particular class's
        :meth:`factory_init_from_deserialized_json`
        Parameters
        ----------
        json_obj

        Returns
        -------

        """
        try:
            model_name = list(json_obj['model'].keys())[0]
            return get_available_models()[model_name].factory_init_from_deserialized_json(json_obj)
        except:
            return None

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Recall this will look something like:

        {
            'model': {
                'NWM': {
                    'version': 2.1,
                    'output': 'streamflow',
                    'parameters': [
                        {
                            'land_cover': {
                                'distribution': {
                                    'min': 0,
                                    'max': 10,
                                    'type': 'lognormal'
                                }
                            }
                        }
                    ]
                }
            }
            'session-secret': 'secret-string-val'
        }


        Parameters
        ----------
        json_obj

        Returns
        -------
        A new object of this type instantiated from the deserialize JSON object dictionary, or none if the provided
        parameter could not be used to instantiated a new object.
        """
        try:
            model_name = cls.model_name
            return cls(version=json_obj['model'][model_name]['version'],
                       output=json_obj['model'][model_name]['output'],
                       domain=json_obj['model'][model_name]['domain'],
                       parameters=json_obj['model'][model_name]['parameters'],
                       session_secret=json_obj['session-secret'])
        except:
            return None

    # TODO: version probably needs to be changed from float to str, but leaving for now since the schema has it as a
    #  number
    def __init__(self, version: float, output: str, domain: str, parameters: dict, session_secret: str):
        """
        :param float version: The version of the model to use
        :param str output: The name of the variable to generate numbers for
        :param str domain: The domain to execute over
        :param dict parameters: A mapping between parameters to configure and their scalar or distribution configurations
        :param str session_secret: The session secret for the right session when communicating with the MaaS request handler
        """
        super(ModelExecRequest, self).__init__(session_secret=session_secret)
        # If this model doesn't generate the output, we want to fail
        if output not in get_available_outputs():
            raise ValueError(
                "{} is not an allowable output; "
                "the only acceptable outputs are: {}".format(output, get_available_outputs())
            )

        # Replace a value of None for parameters with an empty dict
        if parameters is None:
            parameters = {}

        # We want to check each parameter if they are formally defined by the model request
        if len(self.get_parameters()) > 0:
            for parameter in parameters:
                # If the parameter isn't approved, we want to fail
                if parameter not in self.get_parameters():
                    raise ValueError(
                        '{} is not a valid parameter; '
                        'the only acceptable parameters are: {}'.format(parameter, self.get_parameters())
                    )

                # Validate the parameter based on scalar rules if it's a scalar
                if isinstance(parameters[parameter], Scalar):
                    self.validate_scalar(parameter, parameters[parameter])
                elif isinstance(parameters[parameter], Distribution):
                    # Validate the parameter based on distribution rules if it's a distribution
                    self.validate_distribution(parameter, parameters[parameter])
                else:
                    # Raise an exception since we only approve of Scalar or Distribution parameters
                    raise ValueError(
                        "{} is not a scalar or distribution.".format(parameter)
                    )

        self._version = version
        self.output = output
        self._domain = domain
        self.parameters = parameters

    def __eq__(self, other):
        return self._check_class_compatible_for_equality(other) \
               and self._version == other._version \
               and self.output == other.output \
               and self.parameters == other.parameters \
               and self.session_secret == other.session_secret \
               and self._domain == other._domain

    #TODO is classmethod appropriate here?  Seems more like an instance
    @property
    def version(self) -> float:
        """
        :return: the version of the model to run
        """
        return self._version

    @property
    def domain(self) -> str:
        """
        :return: domain name the model is executing on
        """
        return self._domain

    @classmethod
    def get_distribution_types(cls) -> list:
        """
        :return: All distribution types that this model uses
        """
        return cls.distribution_types

    @classmethod
    def get_model_name(cls) -> str:
        """
        :return: The name of this model
        """
        return cls.model_name

    @classmethod
    def get_parameters(cls) -> list:
        """
        :return: The parameters for the model that may be configured
        """
        return cls.parameters

    @classmethod
    def get_output_variables(cls) -> list:
        """
        :return: The variables that the model is able to generate
        """
        return cls.output_variables

    @classmethod
    def validate_scalar(cls, parameter_name: str, scalar: Scalar):
        """
        Test the scalar value to see if it is compatible with the model

        A different way to approach this might be to make the parameter list a mapping between the
        parameters and their boundaries (i.e. shifting the min/max scalar value into the map). This will allow
        behavior that has different bounds between parameters. For instance, 'land_cover' could have a max scalar of
        8 while 'hydro_whatever' might have a max scalar of 72.

        :param str parameter_name: The name of the parameter with the scalar
        :param Scalar scalar: The value for the parameter
        :raises ValueError: Raised in the event that the scalar is incompatible with the model
        """
        if scalar.scalar < cls.min_scalar:
            raise ValueError(
                "{} is too low of a scalar value for {} for {} models. It must be greater than or equal to {}.".format(
                    scalar.scalar,
                    parameter_name,
                    cls.model_name,
                    cls.min_scalar
                )
            )
        elif scalar.scalar > cls.max_scalar:
            raise ValueError(
                "{} is too high of a scalar value for {} for {} models. It must be less than or equal to {}.".format(
                    scalar.scalar,
                    parameter_name,
                    cls.model_name,
                    cls.max_scalar
                )
            )

    @classmethod
    def validate_distribution(cls, parameter_name: str, distribution: Distribution):
        """
        Test the distribution value to see if it is compatible with the model

        A different way to approach this might be to make the parameter list a mapping between the
        parameters and their boundaries (i.e. shifting the min/max scalar value into the map). This will allow
        behavior that has different bounds between parameters. For instance, 'land_cover' could have a max scalar of
        8 while 'hydro_whatever' might have a max scalar of 72.

        :param str parameter_name: The name of the parameter with the distribution
        :param Distribution distribution: The value for the parameter
        :raises ValueError: Raised in the event that the distribution is incompatible with the model
        """
        messages = list()

        if distribution.minimum < cls.min_distribution:
            messages.append(
                "{} is too low of a distribution value for {} for {} models. "
                "It must be greater than or equal to {}".format(
                    distribution.minimum,
                    parameter_name,
                    cls.model_name,
                    cls.min_distribution
                )
            )

        if distribution.minimum > cls.max_distribution:
            messages.append(
                "{} is too high of a distribution value for {} for {} models. "
                "It must be less than or equal to {}".format(
                    distribution.maximum,
                    parameter_name,
                    cls.model_name,
                    cls.max_distribution
                )
            )

        if distribution.minimum > distribution.maximum:
            messages.append(
                "The minimum value for the distribution ({}) is higher than the maximum ({}) "
                "for the {} parameter".format(distribution.minimum, distribution.maximum, parameter_name)
            )

        if distribution.distribution_type not in cls.distribution_types:
            messages.append(
                "The {} distribution type may not be used for the {} parameter".format(
                    distribution.distribution_type,
                    parameter_name
                )
            )

        if len(messages) > 0:
            raise ValueError(". ".join(messages))

    @classmethod
    def validate_output(cls, output: str):
        """
        :param str output: The type of output that we want the model to generate
        :raises ValueError if the model cannot generate the given output type
        """
        if output not in cls.output_variables:
            raise ValueError("{} is not supported by the {} model.".format(output, cls.model_name))

    def to_dict(self) -> dict:
        """
        Converts the request to a dictionary that may be passed to web requests

        Will look like:

        {
            'model': {
                'NWM': {
                    'version': 2.1,
                    'output': 'streamflow',
                    'parameters': [
                        {
                            'land_cover': {
                                'distribution': {
                                    'min': 0,
                                    'max': 10,
                                    'type': 'lognormal'
                                }
                            }
                        }
                    ]
                    'domain': 'test-domain'
                }
            }
            'session-secret': 'secret-string-val'
        }

        :return: A dictionary containing all the data in such a way that it may be used by a web request
        """
        model = dict()
        model[self.get_model_name()] = dict()
        model[self.get_model_name()]['version'] = self._version
        model[self.get_model_name()]['output'] = self.output
        model[self.get_model_name()]['domain'] = self._domain
        model[self.get_model_name()]['parameters'] = dict()

        for parameter in self.parameters:
            model[self.get_model_name()]['parameters'].update({parameter: self.parameters[parameter].to_dict()})

        return {'model': model, 'session-secret': self.session_secret}


class MaaSRequestResponse(Response, ABC):
    def __init__(self, success: bool, reason: str, message: str = '', data=None):
        super().__init__(success=success, reason=reason, message=message, data=data)


class ModelExecRequestResponse(MaaSRequestResponse, ABC):

    @property
    def reason_enum(self):
        try:
            return InitRequestResponseReason[self.reason]
        except:
            return InitRequestResponseReason.UNKNOWN

class Parameter(object):
    """
        Base clase for model parameter descriptions that a given model may expose to DMOD for dynamic parameter selection.
    """
    def __init__(self, name):
        """
            Set the base meta data of the parameter
        """
        self.name = name

class ScalarParameter(Parameter):
    """
        A Scalar parameter is a simple interger parameter who's valid range are integer increments between
        min and max, inclusive.
    """

    def __init__(self, min, max):
        self.min = min
        self.max=max

class NWMRequest(ModelExecRequest):

    event_type = MessageEventType.MODEL_EXEC_REQUEST
    """(:class:`MessageEventType`) The type of event for this message"""
    #Once more the case senstivity of this model name is called into question
    #note: this is essentially keyed to image_and_domain.yml and the cases must match!
    model_name = 'nwm'
    """(:class:`str`) The name of the model to be used"""

    parameters = [
        'hydraulic_conductivity',
        'land_cover'
    ]
    """(:class:`list`) The collection of parameters to use"""

    output_variables = [
        'streamflow'
    ]
    """(:class:`list`) The collection of output variables that the model may generate"""

    max_distribution = 10
    """(:class:`int`) The maximum value for a distribution for a parameter that the model may handle"""

    min_distribution = 0
    """(:class:`int`) The minimum value for a distribution for a parameter that the model may handle"""

    min_scalar = 0
    """(:class:`int`) The minimum scalar value for a parameter that the model may handle"""

    max_scalar = 10
    """(:class:`int`) The maximum scalar value for a parameter that the model may handle"""

    distribution_types = [
        'normal',
        'lognormal'
    ]
    """(:class:`list`) The collection of distribution types that the model may handle"""

    @classmethod
    def factory_init_correct_response_subtype(cls, json_obj: dict) -> ModelExecRequestResponse:
        """
        Init a :obj:`Response` instance of the appropriate subtype for this class from the provided JSON object.

        Parameters
        ----------
        json_obj

        Returns
        -------

        """
        return NWMRequestResponse.factory_init_from_deserialized_json(json_obj=json_obj)

    def __init__(self, session_secret: str, version: float = 0.0, output: str = 'streamflow', domain: str = None, parameters: dict = None):
        super(NWMRequest, self).__init__(version=version, output=output, domain=domain, parameters=parameters,
                                         session_secret=session_secret)


class NWMRequestResponse(ModelExecRequestResponse):
    """
    A response to a :class:`NWMRequest`.

    Note that, when not ``None``, the :attr:`data` value will be a dictionary with the following format:
        - key 'job_id' : the appropriate job id value in response to the request
        - key 'scheduler_response' : the related :class:`SchedulerRequestResponse`, in serialized dictionary form

    For example:
    {
        'job_id': 1,
        'scheduler_response': {
            'success': True,
            'reason': 'Testing Stub',
            'message': 'Testing stub',
            'data': {
                'job_id': 1
            }
        }
    }

    Or:
    {
        'job_id': 0,
        'scheduler_response': {
            'success': False,
            'reason': 'Testing Stub',
            'message': 'Testing stub',
            'data': {}
        }
    }
    """

    _data_dict_key_job_id = 'job_id'
    _data_dict_key_scheduler_response = 'scheduler_response'
    response_to_type = NWMRequest

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Parameters
        ----------
        json_obj

        Returns
        -------
        response_obj : Response
            A new object of this type instantiated from the deserialize JSON object dictionary, or none if the provided
            parameter could not be used to instantiated a new object.

        See Also
        -------
        _factory_init_data_attribute
        """
        try:
            return cls(success=json_obj['success'], reason=json_obj['reason'], message=json_obj['message'],
                       scheduler_response=json_obj['data'])
        except Exception as e:
            return None

    @classmethod
    def _convert_scheduler_response_to_data_attribute(cls, scheduler_response=None):
        job_id_key = cls.get_data_dict_key_for_job_id()
        sched_resp_key = cls.get_data_dict_key_for_scheduler_response()
        if scheduler_response is None:
            return None
        elif isinstance(scheduler_response, dict) and len(scheduler_response) == 0:
            return {}
        elif isinstance(scheduler_response, dict):
            return scheduler_response
        else:
            return {job_id_key: scheduler_response.job_id, sched_resp_key: scheduler_response.to_dict()}

    @classmethod
    def get_data_dict_key_for_job_id(cls):
        """
        Get the standard key name used in the :attr:`data` attribute dictionary for storing the ``job_id`` value.
        Returns
        -------
        str
            the standard key name used in the :attr:`data` attribute dictionary for storing the ``job_id`` value
        """
        return cls._data_dict_key_job_id

    @classmethod
    def get_data_dict_key_for_scheduler_response(cls):
        """
        Get the standard key name used in the :attr:`data` attribute dictionary for storing the serialized scheduler
        response value.

        Returns
        -------
        str
            the standard key name used in the :attr:`data` attribute dictionary for storing the serialized scheduler
            response value
        """
        return cls._data_dict_key_scheduler_response

    def __init__(self, success: bool, reason: str, message: str = '', scheduler_response=None):
        super().__init__(success=success,
                         reason=reason,
                         message=message,
                         data=self._convert_scheduler_response_to_data_attribute(scheduler_response))

    @property
    def job_id(self):
        if not isinstance(self.data, dict):
            return -1
        else:
            return self.data[self.get_data_dict_key_for_job_id()]

class NGENRequest(ModelExecRequest):

    event_type = MessageEventType.MODEL_EXEC_REQUEST
    """(:class:`MessageEventType`) The type of event for this message"""

    model_name = 'ngen' #FIXME case sentitivity
    """(:class:`str`) The name of the model to be used"""

    parameters = []
    """(:class:`list`) The collection of parameters to use"""

    # TODO: this no longer makes sense in the context of Nextgen, as it is entirely (BMI) model dependent
    output_variables = []
    """(:class:`list`) The collection of output variables that the model may generate"""

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> Optional['NGENRequest']:
        """
        Deserialize request formated as JSON to an instance.

        See the documentation of this type's ::method:`to_dict` for an example of the format of valid JSON.

        Parameters
        ----------
        json_obj : dict
            The serialized JSON representation of a request object.

        Returns
        -------
        The deserialized ::class:`NGENRequest`, or ``None`` if the JSON was not valid for deserialization.

        See Also
        -------
        ::method:`to_dict`
        """
        try:
            return cls(time_range=TimeRange.factory_init_from_deserialized_json(json_obj['model']['time_range']),
                       hydrofabric_uid=json_obj['model']['hydrofabric_uid'],
                       hydrofabric_data_id=json_obj['model']['hydrofabric_data_id'],
                       cfg_data_id=json_obj['model']['config_data_id'],
                       bmi_cfg_data_id=json_obj['model']['bmi_config_data_id'],
                       catchments=json_obj['catchments'] if 'catchments' in json_obj else None,
                       session_secret=json_obj['session-secret'])
        except Exception as e:
            return None

    @classmethod
    def factory_init_correct_response_subtype(cls, json_obj: dict) -> ModelExecRequestResponse:
        """
        Init a :obj:`Response` instance of the appropriate subtype for this class from the provided JSON object.

        Parameters
        ----------
        json_obj

        Returns
        -------

        """
        return NGENRequestResponse.factory_init_from_deserialized_json(json_obj=json_obj)

    def __init__(self, session_secret: str, time_range: TimeRange, hydrofabric_uid: str, hydrofabric_data_id: str,
                 cfg_data_id: str, bmi_cfg_data_id: str, catchments: Optional[Union[Set[str], List[str]]] = None):
        """
        Initialize an instance.

        Parameters
        ----------
        session_secret : str
            The session secret used for checking authentication and authorization of this request.
        time_range : TimeRange
            A definition of the time range for the requested model execution.
        hydrofabric_uid : str
            The unique ID of the applicable hydrofabric for modeling, which provides the outermost geospatial domain.
        hydrofabric_data_id : str
            A data identifier for the hydrofabric, for distinguishing between different hydrofabrics that cover the same
            set of catchments and nexuses (i.e., the same sets of catchment and nexus ids).
        cfg_data_id : str
            The config data id index, for identifying the particular configuration datasets applicable to this request.
        catchments : Optional[Union[Set[str], List[str]]]
            An optional collection of the catchment ids to narrow the geospatial domain, where the default of ``None``
            or an empty collection implies all catchments in the hydrofabric.
        bmi_cfg_data_id : Optional[str]
            The optioanl BMI init config ``data_id`` index, for identifying the particular BMI init config datasets
            applicable to this request.
        """
        super().__init__(version=4.0, output="streamflow", domain="Nextgen Custom Spatial Domain", parameters={},
                         session_secret=session_secret)
        self._time_range = time_range
        self._hydrofabric_uid = hydrofabric_uid
        self._hydrofabric_data_id = hydrofabric_data_id
        self._config_data_id = cfg_data_id
        # Convert an initial list to a set to remove duplicates
        try:
            catchments = set(catchments)
        # TypeError should mean that we received `None`, so just use that to set _catchments
        except TypeError:
            self._catchments = catchments
        # Assuming we have a set now, move this set back to list and sort
        else:
            self._catchments = list(catchments)
            self._catchments.sort()

        self._bmi_config_data_id = bmi_cfg_data_id
        self._hydrofabric_data_requirement = None
        self._output_data_requirement = None
        self._forcing_data_requirement = None
        self._realization_cfg_data_requirement = None
        self._bmi_cfg_data_requirement = None

    def _gen_catchments_domain_restriction(self, var_name: str = 'catchment-id') -> DiscreteRestriction:
        """
        Generate a ::class:`DiscreteRestriction` that will restrict to the catchments applicable to this request.

        Note that if the ::attribute:`catchments` property is ``None`` or empty, then the generated restriction object
        will reflect that with an empty list of values, implying "all catchments in hydrofabric."  This is slightly
        different than the internal behavior of ::class:`DiscreteRestriction` itself, which only infers this for empty
        lists (i.e., not a ``values`` value of ``None``).  This is intentional here, as the natural implication of
        specific catchments not being provided as part of a job request is to include all of them.

        Parameters
        ----------
        var_name : str
            The value of the ::attribute:`DiscreteRestriction.variable` for the restriction; defaults to `catchment-id`.

        Returns
        -------
        DiscreteRestriction
            ::class:`DiscreteRestriction` that will restrict to the catchments applicable to this request.
        """
        return DiscreteRestriction(variable=var_name, values=([] if self.catchments is None else self.catchments))

    @property
    def bmi_config_data_id(self) -> str:
        """
        The index value of ``data_id`` to uniquely identify sets of BMI module config data that are otherwise similar.

        Returns
        -------
        str
            Index value of ``data_id`` to uniquely identify sets of BMI module config data that are otherwise similar.
        """
        return self._bmi_config_data_id

    @property
    def bmi_cfg_data_requirement(self) -> DataRequirement:
        """
        A requirement object defining of the BMI configuration data needed to execute this request.

        Returns
        -------
        DataRequirement
            A requirement object defining of the BMI configuration data needed to execute this request.
        """
        if self._bmi_cfg_data_requirement is None:
            bmi_config_restrict = [DiscreteRestriction(variable='data_id', values=[self._bmi_config_data_id])]
            bmi_config_domain = DataDomain(data_format=DataFormat.BMI_CONFIG, discrete_restrictions=bmi_config_restrict)
            self._bmi_cfg_data_requirement = DataRequirement(bmi_config_domain, True, DataCategory.CONFIG)
        return self._bmi_cfg_data_requirement

    @property
    def catchments(self) -> Optional[List[str]]:
        """
        An optional list of catchment ids for those catchments in the request ngen execution.

        No list implies "all" known catchments.

        Returns
        -------
        Optional[List[str]]
            An optional list of catchment ids for those catchments in the request ngen execution.
        """
        return self._catchments

    @property
    def config_data_id(self) -> str:
        """
        The index value of ``data_id`` to uniquely identify sets of config data that are otherwise similar.

        For example, two realization configs may apply to the same time and catchments, but be very different.  The
        nature of the differences is not necessarily even possible to define generally, and certainly not through
        (pre-existing) indices.  As such, the `data_id` index is added for such differentiating purposes.

        Returns
        -------
        str
            The index value of ``data_id`` to uniquely identify sets of config data that are otherwise similar.
        """
        return self._config_data_id

    @property
    def forcing_data_requirement(self) -> DataRequirement:
        """
        A requirement object defining of the forcing data needed to execute this request.

        Returns
        -------
        DataRequirement
            A requirement object defining of the forcing data needed to execute this request.
        """
        if self._forcing_data_requirement is None:
            # TODO: going to need to address the CSV usage later
            forcing_domain = DataDomain(data_format=DataFormat.AORC_CSV, continuous_restrictions=[self._time_range],
                                        discrete_restrictions=[self._gen_catchments_domain_restriction()])
            self._forcing_data_requirement = DataRequirement(domain=forcing_domain, is_input=True,
                                                             category=DataCategory.FORCING)
        return self._forcing_data_requirement

    @property
    def hydrofabric_data_requirement(self) -> DataRequirement:
        """
        A requirement object defining the hydrofabric data needed to execute this request.

        Returns
        -------
        DataRequirement
            A requirement object defining the hydrofabric data needed to execute this request.
        """
        if self._hydrofabric_data_requirement is None:
            hydro_restrictions = [DiscreteRestriction(variable='hydrofabric_uid', values=[self._hydrofabric_uid]),
                                  DiscreteRestriction(variable='data_id', values=[self._hydrofabric_data_id])]
            hydro_domain = DataDomain(data_format=DataFormat.NGEN_GEOJSON_HYDROFABRIC,
                                      discrete_restrictions=hydro_restrictions)
            self._hydrofabric_data_requirement = DataRequirement(domain=hydro_domain, is_input=True,
                                                                 category=DataCategory.HYDROFABRIC)
        return self._hydrofabric_data_requirement

    @property
    def hydrofabric_data_id(self) -> str:
        """
        The data format ``data_id`` for the hydrofabric dataset to use in requested modeling.

        This identifier is needed to distinguish the correct hydrofabric dataset, and thus the correct hydrofabric,
        expected for this modeling request.  For arbitrary hydrofabric types, this may not be possible with the unique
        id of the hydrofabric alone.  E.g., a slight adjustment of catchment coordinates may be ignored with respect
        to the hydrofabric's uid, but may be relevant with respect to a model request.

        Returns
        -------
        str
            The data format ``data_id`` for the hydrofabric dataset to use in requested modeling.
        """
        return self._hydrofabric_data_id

    @property
    def hydrofabric_uid(self) -> str:
        """
        The unique id of the hydrofabric for this modeling request.

        Returns
        -------
        str
            The unique id of the hydrofabric for this modeling request.
        """
        return self._hydrofabric_uid

    @property
    def output_data_requirement(self) -> DataRequirement:
        """
        A requirement object defining of the output data storage capabilities needed to execute this request.

        Returns
        -------
        DataRequirement
            A requirement object defining of the output data storage capabilities needed to execute this request.
        """
        if self._output_data_requirement is None:
            # For now, don't restrict 'data_id' of output domain; expect this to be equal to the job id
            # TODO: handle setting of output dataset data_id as job_id on the client side properly
            output_domain = DataDomain(DataFormat.NGEN_OUTPUT)
            self._output_data_requirement = DataRequirement(domain=output_domain, is_input=False,
                                                            category=DataCategory.OUTPUT)
        return self._output_data_requirement

    @property
    def realization_cfg_data_requirement(self) -> DataRequirement:
        """
        A requirement object defining of the realization configuration data needed to execute this request.

        Returns
        -------
        DataRequirement
            A requirement object defining of the realization configuration data needed to execute this request.
        """
        if self._realization_cfg_data_requirement is None:
            real_cfg_dis_restrict = [self._gen_catchments_domain_restriction(),
                                     DiscreteRestriction(variable='data_id', values=[self.config_data_id])]
            real_cfg_domain = DataDomain(data_format=DataFormat.NGEN_REALIZATION_CONFIG,
                                         continuous_restrictions=[self.time_range],
                                         discrete_restrictions=real_cfg_dis_restrict)
            self._realization_cfg_data_requirement = DataRequirement(domain=real_cfg_domain, is_input=True,
                                                                     category=DataCategory.CONFIG)
        return self._realization_cfg_data_requirement

    @property
    def time_range(self) -> TimeRange:
        """
        The time range for the requested model execution.

        Returns
        -------
        TimeRange
            The time range for the requested model execution.
        """
        return self._time_range

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        """
        Converts the request to a dictionary that may be passed to web requests

        Will look like:

        {
            'model': {
                'name': 'ngen',
                'time_range': { <serialized_time_range_object> },
                'hydrofabric_data_id': 'hy-data-id-val',
                'hydrofabric_uid': 'hy-uid-val',
                'config_data_id': 'config-data-id-val',
                'bmi_config_data_id': 'bmi-config-data-id',
                ['catchments': { <serialized_catchment_discrete_restriction_object> },]
                'version': 4.0
            },
            'session-secret': 'secret-string-val'
        }

        As a reminder, the ``catchments`` item may be absent, which implies the object does not have a specified list of
        catchment ids.

        Returns
        -------
        Dict[str, Union[str, Number, dict, list]]
            A dictionary containing all the data in such a way that it may be used by a web request
        """
        model = dict()
        model["name"] = self.get_model_name()
        model["time_range"] = self.time_range.to_dict()
        model["hydrofabric_data_id"] = self.hydrofabric_data_id
        model["hydrofabric_uid"] = self.hydrofabric_uid
        model["config_data_id"] = self.config_data_id
        model["bmi_config_data_id"] = self._bmi_config_data_id
        if self.catchments is not None:
            model['catchments'] = self.catchments
        model['version'] = self._version

        return {'model': model, 'session-secret': self.session_secret}


class NGENRequestResponse(ModelExecRequestResponse):
    """
    A response to a :class:`NGENRequest`.

    Note that, when not ``None``, the :attr:`data` value will be a dictionary with the following format:
        - key 'job_id' : the appropriate job id value in response to the request
        - key 'scheduler_response' : the related :class:`SchedulerRequestResponse`, in serialized dictionary form

    For example:
    {
        'job_id': 1,
        'scheduler_response': {
            'success': True,
            'reason': 'Testing Stub',
            'message': 'Testing stub',
            'data': {
                'job_id': 1
            }
        }
    }

    Or:
    {
        'job_id': 0,
        'scheduler_response': {
            'success': False,
            'reason': 'Testing Stub',
            'message': 'Testing stub',
            'data': {}
        }
    }
    """

    _data_dict_key_job_id = 'job_id'
    _data_dict_key_scheduler_response = 'scheduler_response'
    response_to_type = NGENRequest

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Parameters
        ----------
        json_obj

        Returns
        -------
        response_obj : Response
            A new object of this type instantiated from the deserialize JSON object dictionary, or none if the provided
            parameter could not be used to instantiated a new object.

        See Also
        -------
        _factory_init_data_attribute
        """
        try:
            return cls(success=json_obj['success'], reason=json_obj['reason'], message=json_obj['message'],
                       scheduler_response=json_obj['data'])
        except Exception as e:
            return None

    #Should this go up level to the abstract request class?
    @classmethod
    def _convert_scheduler_response_to_data_attribute(cls, scheduler_response=None):
        job_id_key = cls.get_data_dict_key_for_job_id()
        sched_resp_key = cls.get_data_dict_key_for_scheduler_response()
        if scheduler_response is None:
            return None
        elif isinstance(scheduler_response, dict) and len(scheduler_response) == 0:
            return {}
        elif isinstance(scheduler_response, dict):
            return scheduler_response
        else:
            return {job_id_key: scheduler_response.job_id, sched_resp_key: scheduler_response.to_dict()}

    @classmethod
    def get_data_dict_key_for_job_id(cls):
        """
        Get the standard key name used in the :attr:`data` attribute dictionary for storing the ``job_id`` value.
        Returns
        -------
        str
            the standard key name used in the :attr:`data` attribute dictionary for storing the ``job_id`` value
        """
        return cls._data_dict_key_job_id

    @classmethod
    def get_data_dict_key_for_scheduler_response(cls):
        """
        Get the standard key name used in the :attr:`data` attribute dictionary for storing the serialized scheduler
        response value.

        Returns
        -------
        str
            the standard key name used in the :attr:`data` attribute dictionary for storing the serialized scheduler
            response value
        """
        return cls._data_dict_key_scheduler_response

    def __init__(self, success: bool, reason: str, message: str = '', scheduler_response=None):
        super().__init__(success=success,
                         reason=reason,
                         message=message,
                         data=self._convert_scheduler_response_to_data_attribute(scheduler_response))

    @property
    def job_id(self):
        if not isinstance(self.data, dict):
            return -1
        else:
            return self.data[self.get_data_dict_key_for_job_id()]

def get_parameters() -> dict:
    """
    Maps each model to the natural and human readable forms of all of their parameters

    Say we have the models:

    * NWM : hydro_whatever, land_cover
    * XYZ : hydro_whatever, land_cover

    This will give us:

    {
        'NWM': [{'value': 'hydro_whatever', 'name': 'Hydro Whatever'}, {'value': 'land_cover', 'name': 'Land Cover'}],

        'XYZ': [{'value': 'hydro_whatever', 'name': 'Hydro Whatever'}, {'value': 'land_cover', 'name': 'Land Cover'}]
    }

    :return: A mapping between the name of the model and actual/human readable names of their parameters
    """
    parameters = dict()

    for model_name, model in get_available_models().items():  # type: str, MaaSJobRequest
        # Say our model is 'NWM'
        model_parameters = list()

        for parameter in model.get_parameters():
            # Say out parameter is 'land_cover'
            parameter_value = dict()
            parameter_value['name'] = " ".join(parameter.split("_")).title()
            parameter_value['value'] = parameter

            # We'll now have {'name': 'Land Cover', 'value': 'land_cover'}, which we'll stick in the list for 'NWM'
            model_parameters.append(parameter_value)

        # This will give us: {'NWM': [{'name': 'Land Cover', 'value': 'land_cover'}]}
        parameters[model_name] = model_parameters

    return parameters


def get_request(model: str, version: float = 0.0, output: str = 'streamflow', domain: str = None, parameters: dict = None,
                session_secret: str = '') -> ModelExecRequest:
    """
    Converts a basic definition of a request into a proper request object

    :param str model: The type of model we want to run
    :param float version: The version of the model to run
    :param str output: What we want the model to generate
    :param str domain: What input domain to execute on
    :param dict parameters: A mapping of all the parameters for the model that we want to set and their values
    :param str session_secret: The session secret for the right session when communicating with the MaaS request handler
    :return: A request object that may be converted into context data for a web request
    """
    if model not in get_available_models():
        raise ValueError(
            "{} is not an allowable model; "
            "the only acceptable models are: {}".format(model, get_available_models())
        )

    if parameters is None:
        parameters = dict()

    return get_available_models()[model](version=version, output=output, domain=domain, parameters=parameters, session_secret=session_secret)
