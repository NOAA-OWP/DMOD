from abc import ABC

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

    def __init__(self, *args, **kwargs):
        super(ModelExecRequest, self).__init__(*args, **kwargs)

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
