"""
Provides an action to end operations in a duplex handler
"""
import typing
import json

from websockets import WebSocketCommonProtocol

from dmod.communication import Field
from dmod.communication import FieldedMessage
from dmod.communication import FieldedActionMessage

from dmod.core.decorators import initializer

from ..exceptions import OperationComplete


CLOSE_MESSAGE = "DISCONNECT"


class EndOperationsMessage(FieldedActionMessage):
    """
    Typed message stating that operations for a handler should end
    """

    @classmethod
    def get_valid_domains(cls) -> typing.Union[str, typing.Collection[str]]:
        return "*"

    @classmethod
    def _get_action_parameters(cls) -> typing.Collection[Field]:
        return list()

    @classmethod
    def get_action_name(cls) -> str:
        """
        Returns:
            The name of the action associated with this type
        """
        return CLOSE_MESSAGE


class EndOperations:
    """
    Action mixin used to throw an exception to notify handlers that operations should complete
    """
    @initializer
    def add_end_operations(self, *args, **kwargs):
        """
        Add the `end_operations` handler to the client and
        Args:
            *args:
            **kwargs:

        Returns:

        """
        getattr(self, "add_source_handler_route")(EndOperationsMessage, self.end_operations_by_message)
        getattr(self, "add_target_handler_route")(EndOperationsMessage, self.end_operations_by_message)

        getattr(self, "add_source_message_handler")(CLOSE_MESSAGE, self.end_operations)
        getattr(self, "add_target_message_handler")(CLOSE_MESSAGE, self.end_operations)

    async def end_operations_by_message(
        self,
        message: FieldedMessage,
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ):
        """
        Throws the `OperationComplete` exception to end all operations
        """
        raise OperationComplete("Request received to disconnect.")

    async def end_operations(
        self,
        message: typing.Union[str, bytes, dict],
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ):
        """
        Ends all current handling of messages coming through the socket

        The overall loop ends when one function returns, so breaking the loop here will close all handling.

        Args:
            message: The message that triggered the function
            source: The connection that started the operations
            target: The connection that is the target of this handler's operations
            path: The path to the socket connection on the server
            *args:
            **kwargs:
        """
        if isinstance(message, dict):
            payload = message.get("event", message.get("action", ""))
        else:
            try:
                payload = json.loads(message)
                payload = payload.get("event", payload.get("action", ""))
            except:
                payload = message

        if isinstance(payload, str) and payload.upper() == CLOSE_MESSAGE:
            raise OperationComplete("Request received to disconnect.")
