from abc import ABC

from typing import Optional, Union

from dmod.core.execution import AllocationParadigm
from ..message import MessageEventType
from .dmod_job_request import DmodJobRequest
from .external_request import ExternalRequest


def get_available_models() -> dict:
    """
    :return: The names of all models mapped to their class
    """
    # TODO: the previous implementation; confirm reason this change was needed
    # available_models = dict()
    #
    # for subclass in ModelExecRequest.__subclasses__():  # type: ModelExecRequest
    #     available_models[subclass.model_name] = subclass
    #
    # return available_models

    def recursively_get_all_model_subclasses(model_exec_request: "ModelExecRequest") -> dict:
        available_models = dict()

        for subclass in model_exec_request.__subclasses__():  # type: ModelExecRequest
            available_models[subclass.model_name] = subclass
            # TODO: what to do if descendant subclass "overwrites" ancestor subclass?
            available_models.update(recursively_get_all_model_subclasses(subclass))

        return available_models

    return recursively_get_all_model_subclasses(ModelExecRequest)


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
    def factory_init_correct_subtype_from_deserialized_json(
        cls, json_obj: dict
    ) -> "ModelExecRequest":
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
                if model in json_obj["model"] or (
                    "name" in json_obj["model"] and json_obj["model"]["name"] == model
                ):
                    return get_available_models()[
                        model
                    ].factory_init_from_deserialized_json(json_obj)
            return None
        except:
            return None

    @classmethod
    def get_model_name(cls) -> str:
        """
        :return: The name of this model
        """
        return cls.model_name

    def __init__(
        self,
        config_data_id: str,
        cpu_count: Optional[int] = None,
        allocation_paradigm: Optional[Union[str, AllocationParadigm]] = None,
        *args,
        **kwargs
    ):
        """
        Initialize model-exec-specific attributes and state of this request object common to all model exec requests.

        Parameters
        ----------
        session_secret : str
            The session secret for the right session when communicating with the request handler.
        """
        super(ModelExecRequest, self).__init__(*args, **kwargs)
        self._config_data_id = config_data_id
        self._cpu_count = (
            cpu_count if cpu_count is not None else self._DEFAULT_CPU_COUNT
        )
        if allocation_paradigm is None:
            self._allocation_paradigm = AllocationParadigm.get_default_selection()
        elif isinstance(allocation_paradigm, str):
            self._allocation_paradigm = AllocationParadigm.get_from_name(
                allocation_paradigm
            )
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
        # elif 0 < len([req for req in self.data_requirements if req not in set(other.data_requirements)]):
        #    return False
        # else:
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
