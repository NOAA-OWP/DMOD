from abc import ABC
from typing import ClassVar, Dict
from ..message import MessageEventType
from .dmod_job_request import DmodJobRequest
from .external_request import ExternalRequest


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

    Note that subtypes must ensure they define both the ::attribute:`model_name` class attribute and the
    ::attribute:`job_type` instance attribute to the same value.  The latter will be a discriminator, so should be
    defined as a fixed ::class:`Literal`. The ::method:`factory_init_correct_subtype_from_deserialized_json` class
    function requires this to work correctly.
    """

    event_type: ClassVar[MessageEventType] = MessageEventType.MODEL_EXEC_REQUEST
    """ (::class:`MessageEventType`) The type of event for this message. """
    model_name: ClassVar[str]
    """ (::class:`str`) The name of the model to be used. """

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
            job_type = json_obj["job_type"]
            models = get_available_models()
            return models[job_type].factory_init_from_deserialized_json(json_obj)
        except:
            return None

    @classmethod
    def get_model_name(cls) -> str:
        """
        :return: The name of this model
        """
        return cls.model_name
