"""
Provides the implementation of a class that can handle communication to and from the evaluation service
"""
import typing

from .duplex import DuplexRequestHandler
from .duplex import RepeatMixin

from dmod.core import decorators
from dmod import communication


class OpenEvaluationMessage(communication.FieldedActionMessage):
    """
    A message used to open a connect to the evaluation service without further operation
    """
    @classmethod
    def _get_action_parameters(cls) -> typing.Collection[communication.Field]:
        fields: typing.List[communication.Field] = list()
        fields.append(
            communication.Field("evaluation_id", required=True)
        )
        return fields

    @classmethod
    def get_action_name(cls) -> str:
        """
        The name of the core 'OpenEvaluationMessage' action
        """
        return "open"

    @classmethod
    def get_valid_domains(cls) -> typing.Union[str, typing.Collection[str]]:
        """
        All domains where the message is valid
        """
        return ["Evaluations", "evaluation", "eval", "evals"]


class LaunchEvaluationMessage(communication.FieldedActionMessage):
    """
    Message used to instruct the service to
    """
    @classmethod
    def _get_action_parameters(cls) -> typing.Collection[communication.Field]:
        return [
            communication.Field(
                "instructions",
                data_type=dict,
                required=True,
                description="The instructions for what to run"
            ),
            communication.Field(
                "evaluation_name",
                data_type=str,
                required=True,
                description="The name for the evaluation"
            )
        ]

    @classmethod
    def get_action_name(cls) -> str:
        """
        The name of the core 'LaunchEvaluationMessage' action
        """
        return "Launch"

    @classmethod
    def get_valid_domains(cls) -> typing.Union[str, typing.Collection[str]]:
        """
        All domains where this message is valid
        """
        return ["Evaluations", "evaluation", "eval", "evals"]


class EvaluationRequestHandler(DuplexRequestHandler, RepeatMixin):
    """
    Handles communication to and from the Evaluation Service
    """
    @classmethod
    def get_target_service(cls) -> str:
        """
        Returns:
            A human friendly name for what service this handler should be targetting
        """
        return "Evaluation Service"

    @decorators.initializer
    def add_repeat_server_message_handler(self, *args, **kwargs):
        """
        Add a server message handler that will ferry messages from the server to the client

        Args:
            *args:
            **kwargs:
        """
        self.add_source_message_handler("send_message_to_server", self.repeat)

    @decorators.initializer
    def add_repeat_client_message_handler(self, *args, **kwargs):
        """
        Add a client message handler that will ferry messages from the client to the server

        Args:
            *args:
            **kwargs:
        """
        self.add_target_message_handler("send_message_to_client", self.repeat)
