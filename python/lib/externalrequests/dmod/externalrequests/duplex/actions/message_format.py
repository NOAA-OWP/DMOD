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

from ..types import *


ACTION_MESSAGE = "ACTIONS"


class ActionGet(HandlerProtocol):
    """
    Action mixin used to throw an exception to notify handlers that operations should complete
    """
    @initializer
    def add_get_actions(self, *args, **kwargs):
        """
        Add the `end_operations` handler to the client and
        Args:
            *args:
            **kwargs:

        Returns:

        """
        self.add_source_handler_route(GetActionsMessage, self.get_source_actions_by_message)
        getattr(self, "add_source_handler_route")(GetActionsMessage, self.get_source_actions_by_message)
        getattr(self, "add_target_handler_route")(GetActionsMessage, self.get_target_actions_by_message)

        getattr(self, "add_source_message_handler")(ACTION_MESSAGE, self.get_source_actions)
        getattr(self, "add_target_message_handler")(ACTION_MESSAGE, self.get_target_actions)

    async def get_source_actions(
        self,
        message: typing.Union[str, bytes],
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ):
        """
        Get all formal typed operations that the application communicating via the server may invoke

        Args:
            message: The message sent through the server socket
            source: The web socket connection from the server
            target: The web socket connection to the target service
            path: The path to the source on the server
            *args:
            **kwargs:
        """
        # Get the data that came through the server
        try:
            action_declaration = json.loads(message)
            action_declaration = action_declaration.get("event") or action_declaration.get("action")
        except:
            action_declaration = message.decode() if isinstance(message, bytes) else message

        # Return if the action wasn't deemed a call for action descriptions
        if not isinstance(action_declaration, str) or action_declaration.upper() != ACTION_MESSAGE:
            return

        accepted_actions = list()

        source_handler_routes: HANDLER_ROUTING_TABLE = getattr(self, "get_source_handler_routes")()

        # Go through every registered action and store its description
        for message_type, handlers in source_handler_routes.items():
            message_type_handler_definitions = {
                "request": message_type.get_message_layout(),
                "handlers": [handler.__name__ for handler in handlers]
            }

            accepted_actions.append(message_type_handler_definitions)

        # Send the combined description of the actions to the server socket
        message = json.dumps(accepted_actions, indent=4)
        await source.send(message)

    async def get_target_actions(
        self,
        message: typing.Union[str, bytes],
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ):
        """
        Get all operations that the application communicating via the server may invoke

        Args:
            message: The message sent through the server socket
            source: The web socket connection from the server
            target: The web socket connection to the target service
            path: The path to the source on the server
            *args:
            **kwargs:
        """
        try:
            payload = json.loads(message)
            payload = payload.get("event") or payload.get("action")
        except:
            payload = message.decode() if isinstance(message, bytes) else message

        if not isinstance(payload, str) or payload.upper() != ACTION_MESSAGE:
            return

        accepted_actions = list()

        target_handler_routes: HANDLER_ROUTING_TABLE = getattr(self, "get_target_handler_routes")()

        for message_type, handlers in target_handler_routes.items():
            message_type_handler_definitions = {
                "request": message_type.get_message_layout(),
                "handlers": [handler.__name__ for handler in handlers]
            }

            accepted_actions.append(message_type_handler_definitions)

        message = json.dumps(accepted_actions, indent=4)
        await target.send(message)

    async def get_source_actions_by_message(
        self,
        message: FieldedMessage,
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ):
        """
        Get all formal typed operations that the application communicating via the server may invoke

        Args:
            message: The message sent through the server socket
            source: The web socket connection from the server
            target: The web socket connection to the target of the handler
            path: The path to the source socket on the server
            *args:
            **kwargs:
        """
        accepted_actions = list()

        source_handler_routes: HANDLER_ROUTING_TABLE = getattr(self, "get_source_handler_routes")()

        # Go through every registered action and store its description
        for message_type, handlers in source_handler_routes.items():
            message_type_handler_definitions = {
                "request": message_type.get_message_layout(),
                "handlers": [handler.__name__ for handler in handlers]
            }

            accepted_actions.append(message_type_handler_definitions)

        # Send the combined description of the actions to the server socket
        message = json.dumps(accepted_actions, indent=4)
        await source.send(message)

    async def get_target_actions_by_message(
        self,
        message: FieldedMessage,
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ):
        """
        Get all formal typed operations that the application communicating via the server may invoke

        Args:
            message: The message sent through the server socket
            source: The web socket connection from the server
            target: The web socket connection to the target of the handler
            path: The path to the source socket on the server
            *args:
            **kwargs:
        """
        accepted_actions = list()

        target_handler_routes: HANDLER_ROUTING_TABLE = getattr(self, "get_target_handler_routes")()

        # Go through every registered action and store its description
        for message_type, handlers in target_handler_routes.items():
            message_type_handler_definitions = {
                "request": message_type.get_message_layout(),
                "handlers": [handler.__name__ for handler in handlers]
            }

            accepted_actions.append(message_type_handler_definitions)

        # Send the combined description of the actions to the server socket
        message = json.dumps(accepted_actions, indent=4)
        await target.send(message)




class GetActionsMessage(FieldedActionMessage):
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
        return ACTION_MESSAGE


class GetActions:
    """
    Action mixin used to throw an exception to notify handlers that operations should complete
    """
    @initializer
    def add_get_actions(self, *args, **kwargs):
        """
        Add the `end_operations` handler to the client and
        Args:
            *args:
            **kwargs:

        Returns:

        """
        getattr(self, "add_source_handler_route")(GetActionsMessage, self.get_source_actions_by_message)
        getattr(self, "add_target_handler_route")(GetActionsMessage, self.get_target_actions_by_message)

        getattr(self, "add_source_message_handler")(ACTION_MESSAGE, self.get_source_actions)
        getattr(self, "add_target_message_handler")(ACTION_MESSAGE, self.get_target_actions)

    async def get_source_actions(
        self,
        message: typing.Union[str, bytes],
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ):
        """
        Get all formal typed operations that the application communicating via the server may invoke

        Args:
            message: The message sent through the server socket
            source: The web socket connection from the server
            target: The web socket connection to the target service
            path: The path to the source on the server
            *args:
            **kwargs:
        """
        # Get the data that came through the server
        try:
            action_declaration = json.loads(message)
            action_declaration = action_declaration.get("event") or action_declaration.get("action")
        except:
            action_declaration = message.decode() if isinstance(message, bytes) else message

        # Return if the action wasn't deemed a call for action descriptions
        if not isinstance(action_declaration, str) or action_declaration.upper() != ACTION_MESSAGE:
            return

        accepted_actions = list()

        source_handler_routes: HANDLER_ROUTING_TABLE = getattr(self, "get_source_handler_routes")()

        # Go through every registered action and store its description
        for message_type, handlers in source_handler_routes.items():
            message_type_handler_definitions = {
                "request": message_type.get_message_layout(),
                "handlers": [handler.__name__ for handler in handlers]
            }

            accepted_actions.append(message_type_handler_definitions)

        # Send the combined description of the actions to the server socket
        message = json.dumps(accepted_actions, indent=4)
        await source.send(message)

    async def get_target_actions(
        self,
        message: typing.Union[str, bytes],
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ):
        """
        Get all operations that the application communicating via the server may invoke

        Args:
            message: The message sent through the server socket
            source: The web socket connection from the server
            target: The web socket connection to the target service
            path: The path to the source on the server
            *args:
            **kwargs:
        """
        try:
            payload = json.loads(message)
            payload = payload.get("event") or payload.get("action")
        except:
            payload = message

        if not isinstance(payload, str) and payload.upper() == ACTION_MESSAGE:
            return

        accepted_actions = list()

        target_handler_routes: HANDLER_ROUTING_TABLE = getattr(self, "get_target_handler_routes")()

        for message_type, handlers in target_handler_routes.items():
            message_type_handler_definitions = {
                "request": message_type.get_message_layout(),
                "handlers": [handler.__name__ for handler in handlers]
            }

            accepted_actions.append(message_type_handler_definitions)

        message = json.dumps(accepted_actions, indent=4)
        await target.send(message)

    async def get_source_actions_by_message(
        self,
        message: FieldedMessage,
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ):
        """
        Get all formal typed operations that the application communicating via the server may invoke

        Args:
            message: The message sent through the server socket
            source: The web socket connection from the server
            target: The web socket connection to the target of the handler
            path: The path to the source socket on the server
            *args:
            **kwargs:
        """
        accepted_actions = list()

        source_handler_routes: HANDLER_ROUTING_TABLE = getattr(self, "get_source_handler_routes")()

        # Go through every registered action and store its description
        for message_type, handlers in source_handler_routes.items():
            message_type_handler_definitions = {
                "request": message_type.get_message_layout(),
                "handlers": [handler.__name__ for handler in handlers]
            }

            accepted_actions.append(message_type_handler_definitions)

        # Send the combined description of the actions to the server socket
        message = json.dumps(accepted_actions, indent=4)
        await source.send(message)

    async def get_target_actions_by_message(
        self,
        message: FieldedMessage,
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ):
        """
        Get all formal typed operations that the application communicating via the server may invoke

        Args:
            message: The message sent through the server socket
            source: The web socket connection from the server
            target: The web socket connection to the target of the handler
            path: The path to the source socket on the server
            *args:
            **kwargs:
        """
        accepted_actions = list()

        target_handler_routes: HANDLER_ROUTING_TABLE = getattr(self, "get_target_handler_routes")()

        # Go through every registered action and store its description
        for message_type, handlers in target_handler_routes.items():
            message_type_handler_definitions = {
                "request": message_type.get_message_layout(),
                "handlers": [handler.__name__ for handler in handlers]
            }

            accepted_actions.append(message_type_handler_definitions)

        # Send the combined description of the actions to the server socket
        message = json.dumps(accepted_actions, indent=4)
        await target.send(message)
