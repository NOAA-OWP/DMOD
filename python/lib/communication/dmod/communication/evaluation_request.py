import typing
import abc
import json

from numbers import Number
from pydantic import Field, validator

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


class StartEvaluationRequest(EvaluationRequest):
    @classmethod
    def get_action(cls) -> str:
        return "launch"

    evaluation_name: str = None

    instructions: typing.Union[str, dict] = None

    action_parameters: dict = None

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> typing.Optional[EvaluationRequest]:
        try:
            if "action" in json_obj and json_obj['action'] != cls.get_action():
                return None

            if "action_parameters" in json_obj:
                parameters = json_obj['action_parameters']
            else:
                parameters = json_obj

            missing_instructions = not parameters.get("instructions") \
                                   or not isinstance(parameters.get("instructions"), (str, dict))
            missing_name = not parameters.get("evaluation_name")

            if missing_instructions or missing_name:
                return None

            return cls(
                instructions=parameters.get("instructions"),
                evaluation_name=parameters.get("evaluation_name"),
                **parameters
            )
        except Exception as e:
            return None

    def to_dict(self) -> SERIALIZABLE_DICT:
        return {
            "action": self.action,
            "action_parameters": self.action_parameters.update(
                {
                    "evaluation_name": self.evaluation_name,
                    "instructions": self.instructions
                }
            )
        }

    def __init__(
        self,
        instructions: str,
        evaluation_name: str,
        **kwargs
    ):
        self._instructions = json.dumps(instructions, indent=4) if isinstance(instructions, dict) else instructions
        self._evaluation_name = evaluation_name
        self._action_parameters = kwargs


class FindEvaluationRequest(EvaluationRequest):
    pass


class SaveEvaluationResponse(Response):
    pass


class StartEvaluationResponse(Response):
    pass


class FindEvaluationResponse(Response):
    pass
