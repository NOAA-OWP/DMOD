from abc import ABC

from typing import ClassVar, Dict, Optional, Union

from dmod.core.execution import AllocationParadigm
from ..message import MessageEventType
from .dmod_job_request import DmodJobRequest
from .external_request import ExternalRequest
from .model_exec_request_body import ModelExecRequestBody


def get_available_models() -> Dict[str, "ModelExecRequest"]:
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


# TODO: #pydantic_rebase - confirm implementation is Pydantic and consistent with changes made to class hierarchy
class ModelExecRequest(ExternalRequest, DmodJobRequest, ABC):
    """
    An abstract extension of ::class:`DmodJobRequest` for requesting model execution jobs.
    """

    event_type: ClassVar[MessageEventType] = MessageEventType.MODEL_EXEC_REQUEST

    model_name: ClassVar[str] = None
    """(:class:`str`) The name of the model to be used"""

    _DEFAULT_CPU_COUNT: ClassVar[int] = 1
    """ The default number of CPUs to assume are being requested for the job, when not explicitly provided. """

    model: ModelExecRequestBody

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
            model = json_obj["model"]

            # TODO: remove logic once `nwm` ModelExecRequest changes where it store the model name.
            model_name = model["name"] if "name" in model else "nwm"
            models = get_available_models()

            return models[model_name].factory_init_from_deserialized_json(json_obj)
        except:
            return None

    # TODO: #pydantic_rebase - see if it makes more sense just to change the serialized structure
    @classmethod
    def get_model_name(cls) -> str:
        """
        :return: The name of this model
        """
        return cls.__fields__["model"].type_.__fields__["name"].default

    # TODO: #pydantic_rebase - reconcile with changes to class hierarchy and property placement, taking out entirely if feasible
    def __init__(
        self,
        # required in prior version of code
        config_data_id: str = None,
        # optional in prior version of code
        cpu_count: Optional[int] = None,
        allocation_paradigm: Optional[Union[str, AllocationParadigm]] = None,
        **data
    ):
        """
        Initialize model-exec-specific attributes and state of this request object common to all model exec requests.

        Parameters
        ----------
        session_secret : str
            The session secret for the right session when communicating with the request handler.
        """
        # assume no need for backwards compatibility
        if "model" in data:
            super().__init__(**data)
            return

        data["model"] = {"config_data_id": config_data_id}

        if cpu_count is not None:
            data["model"]["cpu_count"] = cpu_count

        if allocation_paradigm is not None:
            data["model"]["allocation_paradigm"] = cpu_count

        super().__init__(**data)

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

    # TODO: #pydantic_rebase - make sure this works with eventual changes to class hierarchy
    @property
    def allocation_paradigm(self) -> AllocationParadigm:
        """
        The allocation paradigm desired for use when allocating resources for this request.

        Returns
        -------
        AllocationParadigm
            The allocation paradigm desired for use with this request.
        """
        return self.model.allocation_paradigm

    # TODO: #pydantic_rebase - make sure this works with eventual changes to class hierarchy
    @property
    def config_data_id(self) -> str:
        """
        Value of ``data_id`` index to uniquely identify the dataset with the primary configuration for this request.

        Returns
        -------
        str
            Value of ``data_id`` identifying the dataset with the primary configuration applicable to this request.
        """
        return self.model.config_data_id

    # TODO: #pydantic_rebase - make sure this works with eventual changes to class hierarchy
    @property
    def cpu_count(self) -> int:
        """
        The number of processors requested for this job.

        Returns
        -------
        int
            The number of processors requested for this job.
        """
        return self.model.cpu_count
