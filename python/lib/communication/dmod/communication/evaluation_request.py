import typing
import abc
import json

from numbers import Number
from pydantic import Field, validator

from dmod.core.serializable import Serializable
from .message import Message, MessageEventType, Response

SERIALIZABLE_DICT = typing.Dict[str, typing.Union[str, Number, dict, typing.List]]


class EvaluationRequest(Message, abc.ABC):
    """
    A request to be forwarded to the evaluation service
    """

    event_type: typing.ClassVar[MessageEventType] = MessageEventType.EVALUATION_REQUEST
    """ :class:`MessageEventType`: the event type for this message implementation """

    action: str

    @classmethod
    @abc.abstractmethod
    def get_action(cls) -> str:
        ...


class EvaluationConnectionRequest(EvaluationRequest):
    """
    A request used to communicate through a chained websocket connection
    """
    action: typing.Literal["connect"] = "connect"
    parameters: typing.Dict[str, typing.Any] = Field(default_factory=dict)

    class Config:
        fields = {
            "parameters": {"alias": "action_parameters"}
            }

    @classmethod
    def get_action(cls) -> str:
        return cls.__fields__["action"].default

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> typing.Optional[EvaluationRequest]:
        """
        Create a request object from a passed in deserialized json document

        Args:
            json_obj: The deserialized

        Returns:
            A new request instance
        """
        if "action" not in json_obj or json_obj['action'] != cls.get_action():
            return None

        json_obj.pop('action')

        return cls(**json_obj)


class EvaluationConnectionRequestResponse(Response):
    pass


class SaveEvaluationRequest(EvaluationRequest):
    pass

class ActionParameters(Serializable):
    evaluation_name: str
    instructions: str

    @validator("instructions", pre=True)
    def _coerce_instructions(cls, value):
        if isinstance(value, dict):
            return json.dumps(value, indent=4)
        return value


class StartEvaluationRequest(EvaluationRequest):
    action: typing.Literal["launch"] = "launch"
    parameters: typing.Dict[str, typing.Any]

    class Config:
        fields = {
            "parameters": {"alias": "action_parameters"}
            }

    # Note: `parameters` is a dictionary representation of `ActionParameters` plus arbitrary keys
    # and values
    @validator("parameters", pre=True)
    def _coerce_action_parameters(cls, value: typing.Union[typing.Dict[str, typing.Any], ActionParameters]):
        if isinstance(value, ActionParameters):
            return value.to_dict()

        parameters = ActionParameters(**value)
        return {**value, **parameters.to_dict()}

    @classmethod
    def get_action(cls) -> str:
        return cls.__fields__["action"].default

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> typing.Optional[EvaluationRequest]:
        try:
            if "action" in json_obj and json_obj["action"] != cls.get_action():
                return None

            return cls(**json_obj)
        except Exception:
            return None

    def __init__(
        self,
        # NOTE: None for backwards compatibility
        instructions: str = None,
        evaluation_name: str = None,
        **kwargs
    ):
        # assume no need for backwards compatibility
        if instructions is None or evaluation_name is None:
            super().__init__(**kwargs)
            return

        parameters = ActionParameters(instructions=instructions, evaluation_name=evaluation_name, **kwargs)
        super().__init__(parameters=parameters.to_dict())


class FindEvaluationRequest(EvaluationRequest):
    pass


class SaveEvaluationResponse(Response):
    pass


class StartEvaluationResponse(Response):
    pass


class FindEvaluationResponse(Response):
    pass
