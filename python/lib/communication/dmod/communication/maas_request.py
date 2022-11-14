"""
Lays out details describing how a request may be created and the different types of requests

@author: Chris Tubbs
"""

from dmod.core.execution import AllocationParadigm
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DiscreteRestriction, DataRequirement, TimeRange
from .message import AbstractInitRequest, MessageEventType, Response, InitRequestResponseReason
from abc import ABC, abstractmethod
from numbers import Number
from typing import Dict, List, Optional, Set, Union


def get_available_models() -> dict:
    """
    :return: The names of all models mapped to their class
    """

    def recursively_get_all_model_subclasses(model_exec_request: "ModelExecRequest") -> dict:
        available_models = dict()

        for subclass in model_exec_request.__subclasses__():  # type: ModelExecRequest
            available_models[subclass.model_name] = subclass
            # TODO: what to do if descendant subclass "overwrites" ancestor subclass?
            available_models.update(recursively_get_all_model_subclasses(subclass))

        return available_models

    return recursively_get_all_model_subclasses(ModelExecRequest)


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


class ExternalRequest(AbstractInitRequest, ABC):
    """
    The base class underlying all types of externally-initiated (and, therefore, authenticated) MaaS system requests.
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

    def __init__(self, session_secret: str, *args, **kwargs):
        """
        Initialize the base attributes and state of this request object.

        Parameters
        ----------
        session_secret : str
            The session secret for the right session when communicating with the MaaS request handler
        """
        super(ExternalRequest, self).__init__(*args, **kwargs)
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


class DmodJobRequest(AbstractInitRequest, ABC):
    """
    The base class underlying all types of messages requesting execution of some kind of workflow job.
    """

    def __int__(self, *args, **kwargs):
        super(DmodJobRequest, self).__int__(*args, **kwargs)

    @property
    @abstractmethod
    def data_requirements(self) -> List[DataRequirement]:
        """
        List of all the explicit and implied data requirements for this request, as needed for creating a job object.

        Returns
        -------
        List[DataRequirement]
            List of all the explicit and implied data requirements for this request.
        """
        pass

    @property
    @abstractmethod
    def output_formats(self) -> List[DataFormat]:
        """
        List of the formats of each required output dataset for the requested job.

        Returns
        -------
        List[DataFormat]
            List of the formats of each required output dataset for the requested job.
        """
        pass


class ModelExecRequest(ExternalRequest, DmodJobRequest, ABC):
    """
    An abstract extension of ::class:`DmodJobRequest` for requesting model execution jobs.
    """

    event_type: MessageEventType = MessageEventType.MODEL_EXEC_REQUEST

    model_name = None
    """(:class:`str`) The name of the model to be used"""

    _DEFAULT_CPU_COUNT = 1
    """ The default number of CPUs to assume are being requested for the job, when not explicitly provided. """

    @classmethod
    def factory_init_correct_subtype_from_deserialized_json(cls, json_obj: dict) -> 'ModelExecRequest':
        """
        Factory method to deserialize a ::class:`ModelExecRequest` object of the correct subtype.

        Much like ::method:`factory_init_from_deserialized_json`, except (sub)type agnostic, allowing this to determine
        the correct ::class:`ModelExecRequest` type from the contents of the JSON, and return a call to that particular
        class's ::method:`factory_init_from_deserialized_json`

        Parameters
        ----------
        json_obj : dict
            A JSON object representing the serialize form of a ::class:`ModelExecRequest` to be deserialized.

        Returns
        -------
        ModelExecRequest
            A deserialized ::class:`ModelExecRequest` of the appropriate subtype.
        """
        try:
            for model in get_available_models():
                if model in json_obj['model'] or ('name' in json_obj['model'] and json_obj['model']['name'] == model):
                    return get_available_models()[model].factory_init_from_deserialized_json(json_obj)
            return None
        except:
            return None

    @classmethod
    def get_model_name(cls) -> str:
        """
        :return: The name of this model
        """
        return cls.model_name

    def __init__(self, config_data_id: str, cpu_count: Optional[int] = None,
                 allocation_paradigm: Optional[Union[str, AllocationParadigm]] = None,  *args, **kwargs):
        """
        Initialize model-exec-specific attributes and state of this request object common to all model exec requests.

        Parameters
        ----------
        session_secret : str
            The session secret for the right session when communicating with the request handler.
        """
        super(ModelExecRequest, self).__init__(*args, **kwargs)
        self._config_data_id = config_data_id
        self._cpu_count = cpu_count if cpu_count is not None else self._DEFAULT_CPU_COUNT
        if allocation_paradigm is None:
            self._allocation_paradigm = AllocationParadigm.get_default_selection()
        elif isinstance(allocation_paradigm, str):
            self._allocation_paradigm = AllocationParadigm.get_from_name(allocation_paradigm)
        else:
            self._allocation_paradigm = allocation_paradigm

    def __eq__(self, other):
        if not self._check_class_compatible_for_equality(other):
            return False
        elif self.session_secret != other.session_secret:
            return False
        elif len(self.data_requirements) != len(other.data_requirements):
            return False
        elif self.allocation_paradigm != other.allocation_paradigm:
            return False
        #elif 0 < len([req for req in self.data_requirements if req not in set(other.data_requirements)]):
        #    return False
        #else:
        #    return True
        else:
            for req in self.data_requirements:
                if req not in other.data_requirements:
                    return False
            return True

    @property
    def allocation_paradigm(self) -> AllocationParadigm:
        """
        The allocation paradigm desired for use when allocating resources for this request.

        Returns
        -------
        AllocationParadigm
            The allocation paradigm desired for use with this request.
        """
        return self._allocation_paradigm

    @property
    def config_data_id(self) -> str:
        """
        Value of ``data_id`` index to uniquely identify the dataset with the primary configuration for this request.

        Returns
        -------
        str
            Value of ``data_id`` identifying the dataset with the primary configuration applicable to this request.
        """
        return self._config_data_id

    @property
    def cpu_count(self) -> int:
        """
        The number of processors requested for this job.

        Returns
        -------
        int
            The number of processors requested for this job.
        """
        return self._cpu_count


class ExternalRequestResponse(Response, ABC):

    response_to_type = ExternalRequest
    """ The type of :class:`AbstractInitRequest` for which this type is the response"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ModelExecRequestResponse(ExternalRequestResponse, ABC):

    _data_dict_key_job_id = 'job_id'
    _data_dict_key_output_data_id = 'output_data_id'
    _data_dict_key_scheduler_response = 'scheduler_response'
    response_to_type = ModelExecRequest
    """ The type of :class:`AbstractInitRequest` for which this type is the response"""

    @classmethod
    def _convert_scheduler_response_to_data_attribute(cls, scheduler_response=None):
        if scheduler_response is None:
            return None
        elif isinstance(scheduler_response, dict) and len(scheduler_response) == 0:
            return {}
        elif isinstance(scheduler_response, dict):
            return scheduler_response
        else:
            return {cls._data_dict_key_job_id: scheduler_response.job_id,
                    cls._data_dict_key_output_data_id: scheduler_response.output_data_id,
                    cls._data_dict_key_scheduler_response: scheduler_response.to_dict()}

    @classmethod
    def get_job_id_key(cls) -> str:
        """
        Get the serialization dictionary key for the field containing the ::attribute:`job_id` property.

        Returns
        -------
        str
            Serialization dictionary key for the field containing the ::attribute:`job_id` property.
        """
        return str(cls._data_dict_key_job_id)

    @classmethod
    def get_output_data_id_key(cls) -> str:
        """
        Get the serialization dictionary key for the field containing the ::attribute:`output_data_id` property.

        Returns
        -------
        str
            Serialization dictionary key for the field containing the ::attribute:`output_data_id` property.
        """
        return str(cls._data_dict_key_output_data_id)

    @classmethod
    def get_scheduler_response_key(cls) -> str:
        """
        Get the serialization dictionary key for the field containing the 'scheduler_response' value.

        Returns
        -------
        str
            Serialization dictionary key for the field containing the 'scheduler_response' value.
        """
        return str(cls._data_dict_key_scheduler_response)

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

    def __init__(self, scheduler_response=None, *args, **kwargs):
        data = self._convert_scheduler_response_to_data_attribute(scheduler_response)
        if data is not None:
            kwargs['data'] = data
        super().__init__(*args, **kwargs)

    @property
    def job_id(self):
        if not isinstance(self.data, dict) or self._data_dict_key_job_id not in self.data:
            return -1
        else:
            return self.data[self._data_dict_key_job_id]

    @property
    def output_data_id(self) -> Optional[str]:
        """
        The 'data_id' of the output dataset for the requested job, if the associated request was successful.

        Returns
        -------
        Optional[str]
            The 'data_id' of the output dataset for requested job, if request was successful; otherwise ``None``.
        """
        if not isinstance(self.data, dict) or self._data_dict_key_output_data_id not in self.data:
            return None
        else:
            return self.data[self._data_dict_key_output_data_id]

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


class NWMConfig:

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
    def get_distribution_types(cls) -> list:
        """
        :return: All distribution types that this model uses
        """
        return cls.distribution_types

    @classmethod
    def get_output_variables(cls) -> list:
        """
        :return: The variables that the model is able to generate
        """
        return cls.output_variables

    @classmethod
    def get_parameters(cls) -> list:
        """
        :return: The parameters for the model that may be configured
        """
        return cls.parameters

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
                "{} is too low of a scalar value for {}. It must be greater than or equal to {}.".format(
                    scalar.scalar,
                    parameter_name,
                    cls.min_scalar
                )
            )
        elif scalar.scalar > cls.max_scalar:
            raise ValueError(
                "{} is too high of a scalar value for {}. It must be less than or equal to {}.".format(
                    scalar.scalar,
                    parameter_name,
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
                "{} is too low of a distribution value for {} for. "
                "It must be greater than or equal to {}".format(
                    distribution.minimum,
                    parameter_name,
                    cls.min_distribution
                )
            )

        if distribution.minimum > cls.max_distribution:
            messages.append(
                "{} is too high of a distribution value for {}. "
                "It must be less than or equal to {}".format(
                    distribution.maximum,
                    parameter_name,
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
            raise ValueError("{} is not supported by NWM model.".format(output))

    def __init__(self, data_id: str, version: float, output: str, domain: str, parameters: dict):
        self.data_id = data_id

        # TODO: add something to set these from a dataset
        self._version = version
        self._output = output
        self._domain = domain
        self.parameters = parameters if parameters is not None else {}

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


class NWMRequest(ModelExecRequest):

    event_type = MessageEventType.MODEL_EXEC_REQUEST
    """(:class:`MessageEventType`) The type of event for this message"""
    #Once more the case senstivity of this model name is called into question
    #note: this is essentially keyed to image_and_domain.yml and the cases must match!
    model_name = 'nwm'
    """(:class:`str`) The name of the model to be used"""

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

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Recall this will look something like:

        {
            'model': {
                'NWM': {
                    'allocation_paradigm': '<allocation_paradigm_str>',
                    'config_data_id': '<config_dataset_data_id>',
                    'cpu_count': <count>,
                    'data_requirements': [ ... (serialized DataRequirement objects) ... ]
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
            nwm_element = json_obj['model'][cls.model_name]
            additional_kwargs = dict()
            if 'cpu_count' in nwm_element:
                additional_kwargs['cpu_count'] = nwm_element['cpu_count']

            if 'allocation_paradigm' in nwm_element:
                additional_kwargs['allocation_paradigm'] = nwm_element['allocation_paradigm']

            obj = cls(config_data_id=nwm_element['config_data_id'], session_secret=json_obj['session-secret'],
                      **additional_kwargs)

            reqs = [DataRequirement.factory_init_from_deserialized_json(req_json) for req_json in
                    json_obj['model'][cls.model_name]['data_requirements']]

            obj._data_requirements = reqs

            return obj
        except Exception as e:
            return None

    def __init__(self, *args, **kwargs):
        super(NWMRequest, self).__init__(*args, **kwargs)
        self._data_requirements = None

    @property
    def data_requirements(self) -> List[DataRequirement]:
        """
        List of all the explicit and implied data requirements for this request, as needed for creating a job object.

        Returns
        -------
        List[DataRequirement]
            List of all the explicit and implied data requirements for this request.
        """
        if self._data_requirements is None:
            data_id_restriction = DiscreteRestriction(variable='data_id', values=[self.config_data_id])
            self._data_requirements = [
                DataRequirement(
                    domain=DataDomain(data_format=DataFormat.NWM_CONFIG, discrete_restrictions=[data_id_restriction]),
                    is_input=True,
                    category=DataCategory.CONFIG
                )
            ]
        return self._data_requirements

    @property
    def output_formats(self) -> List[DataFormat]:
        """
        List of the formats of each required output dataset for the requested job.

        Returns
        -------
        List[DataFormat]
            List of the formats of each required output dataset for the requested job.
        """
        return [DataFormat.NWM_OUTPUT]

    def to_dict(self) -> dict:
        """
        Converts the request to a dictionary that may be passed to web requests.

        Will look like:

        {
            'model': {
                'NWM': {
                    'allocation_paradigm': '<allocation_paradigm_str>',
                    'config_data_id': '<config_dataset_data_id>',
                    'cpu_count': <count>,
                    'data_requirements': [ ... (serialized DataRequirement objects) ... ]
                }
            }
            'session-secret': 'secret-string-val'
        }

        Returns
        -------
        dict
            A dictionary containing all the data in such a way that it may be used by a web request
        """
        model = dict()
        model[self.get_model_name()] = dict()
        model[self.get_model_name()]['allocation_paradigm'] = self.allocation_paradigm.name
        model[self.get_model_name()]['config_data_id'] = self.config_data_id
        model[self.get_model_name()]['cpu_count'] = self.cpu_count
        model[self.get_model_name()]['data_requirements'] = [r.to_dict() for r in self.data_requirements]
        return {'model': model, 'session-secret': self.session_secret}


class NWMRequestResponse(ModelExecRequestResponse):
    """
    A response to a :class:`NWMRequest`.

    Note that, when not ``None``, the :attr:`data` value will be a dictionary with the following format:
        - key 'job_id' : the appropriate job id value in response to the request
        - key 'output_data_id' : the 'data_id' of the output dataset for the requested job
        - key 'scheduler_response' : the related :class:`SchedulerRequestResponse`, in serialized dictionary form

    For example:
    {
        'job_id': 1,
        'output_data_id': '00000000-0000-0000-0000-000000000000',
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
        'output_data_id': '00000000-0000-0000-0000-000000000000',
        'scheduler_response': {
            'success': False,
            'reason': 'Testing Stub',
            'message': 'Testing stub',
            'data': {}
        }
    }
    """

    response_to_type = NWMRequest


class NGENRequest(ModelExecRequest):

    event_type = MessageEventType.MODEL_EXEC_REQUEST
    """(:class:`MessageEventType`) The type of event for this message"""

    model_name = 'ngen' #FIXME case sentitivity
    """(:class:`str`) The name of the model to be used"""

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
            optional_kwargs_w_defaults = dict()
            if 'cpu_count' in json_obj['model']:
                optional_kwargs_w_defaults['cpu_count'] = json_obj['model']['cpu_count']
            if 'allocation_paradigm' in json_obj['model']:
                optional_kwargs_w_defaults['allocation_paradigm'] = json_obj['model']['allocation_paradigm']
            if 'catchments' in json_obj['model']:
                optional_kwargs_w_defaults['catchments'] = json_obj['model']['catchments']
            if 'partition_config_data_id' in json_obj['model']:
                optional_kwargs_w_defaults['partition_config_data_id'] = json_obj['model']['partition_config_data_id']

            return cls(time_range=TimeRange.factory_init_from_deserialized_json(json_obj['model']['time_range']),
                       hydrofabric_uid=json_obj['model']['hydrofabric_uid'],
                       hydrofabric_data_id=json_obj['model']['hydrofabric_data_id'],
                       config_data_id=json_obj['model']['config_data_id'],
                       bmi_cfg_data_id=json_obj['model']['bmi_config_data_id'],
                       session_secret=json_obj['session-secret'],
                       **optional_kwargs_w_defaults)
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

    def __eq__(self, other):
        return self.time_range == other.time_range and self.hydrofabric_data_id == other.hydrofabric_data_id \
               and self.hydrofabric_uid == other.hydrofabric_uid and self.config_data_id == other.config_data_id \
               and self.bmi_config_data_id == other.bmi_config_data_id and self.session_secret == other.session_secret \
               and self.cpu_count == other.cpu_count and self.partition_cfg_data_id == other.partition_cfg_data_id \
               and self.catchments == other.catchments

    def __hash__(self):
        hash_str = '{}-{}-{}-{}-{}-{}-{}-{}-{}'.format(self.time_range.to_json(), self.hydrofabric_data_id,
                                                       self.hydrofabric_uid, self.config_data_id,
                                                       self.bmi_config_data_id, self.session_secret, self.cpu_count,
                                                       self.partition_cfg_data_id, ','.join(self.catchments))
        return hash(hash_str)

    def __init__(self, time_range: TimeRange, hydrofabric_uid: str, hydrofabric_data_id: str, bmi_cfg_data_id: str,
                 catchments: Optional[Union[Set[str], List[str]]] = None, partition_cfg_data_id: Optional[str] = None,
                 *args, **kwargs):
        """
        Initialize an instance.

        Parameters
        ----------
        time_range : TimeRange
            A definition of the time range for the requested model execution.
        hydrofabric_uid : str
            The unique ID of the applicable hydrofabric for modeling, which provides the outermost geospatial domain.
        hydrofabric_data_id : str
            A data identifier for the hydrofabric, for distinguishing between different hydrofabrics that cover the same
            set of catchments and nexuses (i.e., the same sets of catchment and nexus ids).
        catchments : Optional[Union[Set[str], List[str]]]
            An optional collection of the catchment ids to narrow the geospatial domain, where the default of ``None``
            or an empty collection implies all catchments in the hydrofabric.
        bmi_cfg_data_id : Optional[str]
            The optioanl BMI init config ``data_id`` index, for identifying the particular BMI init config datasets
            applicable to this request.

        Keyword Args
        -----------
        config_data_id : str
            The config data id index, for identifying the particular configuration datasets applicable to this request.
        session_secret : str
            The session secret for the right session when communicating with the MaaS request handler
        """
        super().__init__(*args, **kwargs)
        self._time_range = time_range
        self._hydrofabric_uid = hydrofabric_uid
        self._hydrofabric_data_id = hydrofabric_data_id
        self._bmi_config_data_id = bmi_cfg_data_id
        self._part_config_data_id = partition_cfg_data_id
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

        self._hydrofabric_data_requirement = None
        self._forcing_data_requirement = None
        self._realization_cfg_data_requirement = None
        self._bmi_cfg_data_requirement = None
        self._partition_cfg_data_requirement = None

    def _gen_catchments_domain_restriction(self, var_name: str = 'catchment_id') -> DiscreteRestriction:
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
    def data_requirements(self) -> List[DataRequirement]:
        """
        List of all the explicit and implied data requirements for this request, as needed for creating a job object.

        Returns
        -------
        List[DataRequirement]
            List of all the explicit and implied data requirements for this request.
        """
        return [self.bmi_cfg_data_requirement, self.forcing_data_requirement, self.hydrofabric_data_requirement,
                self.partition_cfg_data_requirement, self.realization_cfg_data_requirement]

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
            hydro_restrictions = [DiscreteRestriction(variable='hydrofabric_id', values=[self._hydrofabric_uid]),
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
    def output_formats(self) -> List[DataFormat]:
        """
        List of the formats of each required output dataset for the requested job.

        Returns
        -------
        List[DataFormat]
            List of the formats of each required output dataset for the requested job.
        """
        return [DataFormat.NGEN_OUTPUT]

    @property
    def partition_cfg_data_id(self) -> Optional[str]:
        """
        The ``data_id`` for the partition config dataset to use in requested modeling.

        This identifier is needed to distinguish the correct specific partition config dataset, and thus the correct
        partition config, expected for this modeling request.  However, this may not always be necessary, as it should
        be possible to find a compatible partitioning config dataset of the right hydrofabric and size, so long as one
        exists.

        Returns
        -------
        Optional[str]
            The data format ``data_id`` for the partition config dataset to use in requested modeling, or ``None``.
        """
        return self._part_config_data_id

    @property
    def partition_cfg_data_requirement(self) -> DataRequirement:
        """
        A requirement object defining of the partitioning configuration data needed to execute this request.

        Returns
        -------
        DataRequirement
            A requirement object defining of the partitioning configuration data needed to execute this request.
        """
        if self._partition_cfg_data_requirement is None:
            d_restricts = []

            # Add restriction on hydrofabric
            d_restricts.append(DiscreteRestriction(variable="hydrofabric_id", values=[self.hydrofabric_uid]))

            # Add restriction on partition count, which will be based on the number of request CPUs
            d_restricts.append(DiscreteRestriction(variable="length", values=[self.cpu_count]))

            # If present, add restriction on data_id
            if self.partition_cfg_data_id is not None:
                d_restricts.append(DiscreteRestriction(variable="data_id", values=[self.partition_cfg_data_id]))
            part_domain = DataDomain(data_format=DataFormat.NGEN_PARTITION_CONFIG, discrete_restrictions=d_restricts)
            self._partition_cfg_data_requirement = DataRequirement(domain=part_domain, is_input=True,
                                                                   category=DataCategory.CONFIG)
        return self._partition_cfg_data_requirement

    @property
    def realization_config_data_id(self) -> str:
        """
        The index value of ``data_id`` to uniquely identify sets of realization config data that are otherwise similar.

        For example, two realization configs may apply to the same time and catchments, but be very different.  The
        nature of the differences is not necessarily even possible to define generally, and certainly not through
        (pre-existing) indices.  As such, the `data_id` index is added for such differentiating purposes.

        Returns
        -------
        str
            The index value of ``data_id`` to uniquely identify the required realization config dataset.
        """
        return self.config_data_id

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
                                     DiscreteRestriction(variable='data_id', values=[self.realization_config_data_id])]
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
                'allocation_paradigm': <allocation_paradigm_str>,
                'cpu_count': <cpu_count>,
                'time_range': { <serialized_time_range_object> },
                'hydrofabric_data_id': 'hy-data-id-val',
                'hydrofabric_uid': 'hy-uid-val',
                'config_data_id': 'config-data-id-val',
                'bmi_config_data_id': 'bmi-config-data-id',
                'partition_config_data_id': 'partition_config_data_id',
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
        model["allocation_paradigm"] = self.allocation_paradigm.name
        model["cpu_count"] = self.cpu_count
        model["time_range"] = self.time_range.to_dict()
        model["hydrofabric_data_id"] = self.hydrofabric_data_id
        model["hydrofabric_uid"] = self.hydrofabric_uid
        model["config_data_id"] = self.config_data_id
        model["bmi_config_data_id"] = self._bmi_config_data_id
        if self.catchments is not None:
            model['catchments'] = self.catchments
        if self.partition_cfg_data_id is not None:
            model['partition_config_data_id'] = self.partition_cfg_data_id

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
        'output_data_id': '00000000-0000-0000-0000-000000000000',
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
        'output_data_id': '00000000-0000-0000-0000-000000000000',
        'scheduler_response': {
            'success': False,
            'reason': 'Testing Stub',
            'message': 'Testing stub',
            'data': {}
        }
    }
    """

    response_to_type = NGENRequest


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


def get_request(model: str, config_data_id: str, session_secret: str = '', *args, **kwargs) -> ModelExecRequest:
    """
    Converts a basic definition of a request into a proper request object

    Parameters
    ----------
    model : str
        The type of model we want to run.
    config_data_id : str
        The model configuration dataset for the request.
    session_secret : str
        The session secret for the right session when communicating with the MaaS request handler.

    Returns
    -------
    ModelExecRequest
        A request object that may be converted into context data for a web request.
    """
    if model not in get_available_models():
        err_msg = "{} is not an allowable model; the only acceptable models are: {}"
        raise ValueError(err_msg.format(model, get_available_models()))

    return get_available_models()[model](config_data_id=config_data_id, session_secret=session_secret, *args, **kwargs)


class NGENCalibrationRequest(NGENRequest):
    model_name: str = "ngen_cal"
