from typing import List

from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DataRequirement, DiscreteRestriction
from ...message import MessageEventType
from ..model_exec_request import ModelExecRequest
from ..model_exec_request_response import ModelExecRequestResponse

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
