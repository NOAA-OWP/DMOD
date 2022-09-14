#!/usr/bin/env python3
import abc
import os
import typing
import secrets
import asyncio
import random
import json

from argparse import ArgumentParser
from numbers import Number
from typing import Dict
from typing import Union

from datetime import datetime

import websockets
from dmod.communication import Field
from websockets import WebSocketServerProtocol

from dmod.communication import MessageEventType
from dmod.externalrequests import duplex
from dmod.externalrequests import AuthHandler
from dmod.externalrequests import EvaluationRequestHandler
from dmod.core import decorators

import dmod.communication as communication
import dmod.access as access


class Arguments(object):
    """
    Arguments that may be used to launch this alternative service from the command line
    """
    def __init__(self, *args):
        self.__port: typing.Optional[int] = None

        self.__parse_command_line(*args)

    @property
    def port(self) -> int:
        """
        The ports to communicate with

        :return: All local ports to talk with
        """
        return self.__port

    def __parse_command_line(self, *args):
        parser = ArgumentParser("Launch an alternative service")

        # Add options
        parser.add_argument(
            "port",
            type=str,
            help="The port to serve"
        )

        # Parse the list of args if one is passed instead of args passed to the script
        if args:
            parameters = parser.parse_args(args)
        else:
            parameters = parser.parse_args()

        # Assign parsed parameters to member variables
        self.__port = int(float(parameters.port))


class TestMessage(communication.RegisteredMessage):
    """
    A basic initialization message to receive for testing
    """
    @classmethod
    def _get_fields(cls) -> typing.Collection[Field]:
        return [
            communication.Field("message_id", required=True)
        ]


class EmitMixin(duplex.MessageHandlerMixin, abc.ABC):
    """
    A mixin class for adding the 'emit_message' socket handler to a service
    """
    @decorators.producer_message_handler
    async def emit_message(
        self,
        socket: WebSocketServerProtocol,
        *args,
        **kwargs
    ) -> communication.Response:
        """
        Sends random messages through a socket

        This serves as its own process for consuming sockets as opposed to the client and server managers that
        react to incoming data

        Args:
            socket: The socket that will have random messages sent through it

        Returns:
            A message detailing the end state for the message handler
        """
        success = True
        reason = communication.InitRequestResponseReason.UNNECESSARY
        response_message = None

        # Keep track of the number of messages so that it may be used as a return value
        message_count = 0

        # Set a minimum wait time between messages - this should be lower than the maximum wait time
        minimum_wait_seconds = 2
        maximum_wait_seconds = 10

        # Store the starting time so the runtime duration may be used as a return value
        start_time = datetime.now()
        try:
            # This handler is not reactive to outside messages. The only way to end this cycle is to encounter an
            # error or for an outside process to cancel this, both of which are desired behaviors of a 'producer'
            while True:
                message = f"The secret code is: {secrets.token_urlsafe(8)}"
                await socket.send(message)
                message_count += 1

                # Since this provides its own messages, we want to wait a seemingly random amount of time to
                # prevent the system from flooding the receiver with meaningless messages
                wait_seconds = random.randint(minimum_wait_seconds, maximum_wait_seconds)
                await asyncio.sleep(wait_seconds)
        except websockets.ConnectionClosedOK as connection_closed:
            print(f"The connection has been closed; {str(connection_closed)}")
        except asyncio.CancelledError:
            response_message = f"Message emmision cancelled. {message_count} message(s) were sent."
        except BaseException as exception:
            success = False
            response_message = f"Message emmission failed: {str(exception)}. {message_count} message(s) were sent."

        # Everything is fine if no exception was encountered, so go ahead and just detail what this process did
        if response_message is None:
            response_message = f"{message_count} messages were sent"

        return self._get_response_class()(
            success=success,
            message=response_message,
            reason=reason,
            data={
                "messages_sent": message_count,
                "duration": str(datetime.now() - start_time)
            }
        )


class EchoMixin(duplex.MessageHandlerMixin, abc.ABC):
    """
    A mixin class for adding the 'emit_message' socket handler to a service
    """
    @decorators.server_message_handler
    async def echo_message(
        self,
        message: str,
        socket: WebSocketServerProtocol,
        *args,
        **kwargs
    ) -> None:
        """
        Prints all received messages to stdout

        Args:
            message: The message sent over the socket
            socket: The socket that receives the messages

        Returns:
            A response reporting how successsful the overall operation was
        """
        print(message)
        notification = {
            "info": f"printed '{message}'"
        }
        prepared_notification = json.dumps(notification)
        await socket.send(prepared_notification)


class TestHandler(duplex.DuplexRequestHandler, EmitMixin, EchoMixin):
    """
    A connection handler that will read from a connection and display received data in stdout while sending
    messages back in semi random timing.
    """

    @classmethod
    def get_target_service(cls) -> str:
        """
        Returns:
            The name of the service that this handler targets
        """
        return "Test Service"


class EchoEmitMixin:
    """
    Mixin that injects a TestHandler instance that launches from a TestMessage
    """

    @decorators.initializer
    def initialize_echo_emit_handler(self, *args, **kwargs):
        """
        Adds a handler object as a member variable that handles operations from `TestMessage`s

        Args:
            *args:
            **kwargs:
        """
        self._test_handler = TestHandler(*args, **kwargs)

    @decorators.socket_handler(**{decorators.MESSAGE_TYPE_ATTRIBUTE: TestMessage})
    def get_test_handler(self):
        """
        Returns:
            The added `TestHandler`
        """
        return self._test_handler


# TODO: See if DummyAuthorizationMixin should be used via composition rather than mixin
class DummyAuthorizationMixin(communication.SessionInterfaceMixin, abc.ABC):
    """
    A mixin for session interfaces providing a simple 'authorizor' that just allows requests to go through without
    any extra operations
    """
    @property
    def authorization_handler(self):
        """
        Returns:
            The handler for session requests defined in `initialize_authorization`
        """
        return getattr(self, "_authorization_handler")

    @decorators.initializer
    def initialize_authorization(self, *args, **kwargs):
        """
        Assign the proper values to the authorization variables

        Args:
            *args:
            **kwargs:
        """
        setattr(self, "_authenticator", access.DummyAuthUtil())
        setattr(self, "_authorizer", access.DummyAuthUtil())
        setattr(self, "_authorization_handler", AuthHandler(
            session_manager=self.session_manager,
            authenticator=getattr(self, "_authenticator"),
            authorizer=getattr(self, "_authorizer")
        ))


# TODO: See if RedisSessionMixin should be used via composition rather than mixin
class RedisSessionMixin(communication.SessionInterfaceMixin, abc.ABC):
    """
    A mixin that provides a Redis backend for a session manager
    """
    @decorators.initializer
    def add_session_manager(self, *args, **kwargs):
        """
        Creates a session manager and attaches it to this object

        Args:
            *args:
            **kwargs:
        """
        if not hasattr(self, "_session_manager"):
            setattr(self, "_session_manager", access.RedisBackendSessionManager())

    @property
    def session_manager(self):
        """
        Returns:
            The session manager created in `add_session_manager`
        """
        return getattr(self, "_session_manager")


class SessionHandler(RedisSessionMixin, DummyAuthorizationMixin, duplex.DuplexRequestHandler):
    """
    A composition of several mixins meant to provide the handling of message requests asking for the session operations
    """
    @classmethod
    def get_target_service(cls) -> str:
        """
        Returns:
            The name of the session service
        """
        return "Session"


class SessionProviderMixin:
    """
    Mixin that injects a handler for session interactions
    """
    @decorators.initializer
    def initialize_session_handler(self, *args, **kwargs):
        self._session_handler = SessionHandler(*args, **kwargs)

    @decorators.socket_handler(**{decorators.MESSAGE_TYPE_ATTRIBUTE: communication.SessionInitMessage})
    def get_session_handler(self):
        """
        Returns:
            The handler used a request for initializing session is requested.
        """
        return self._session_handler

    @decorators.additional_parameter
    def get_session_parameter(self, *args, **kwargs):
        """
        Get an additional parameter for other handlers that will provide a session manager

        Args:
            *args:
            **kwargs:

        Returns:
            A dictionary mapping this class' session manager to the parameter named 'session_manager'
        """
        return {
            "session_manager": self._session_handler.session_manager
        }


class EvaluationMessage(communication.RegisteredMessage):
    @classmethod
    def _get_fields(cls) -> typing.Collection[Field]:
        fields: typing.List[communication.Field] = list()
        fields.append(
            Field("evaluation_id", required=True)
        )
        return fields


class EvaluationInjector:
    """
    Mixin that adds a handler for evaluation requests
    """
    @decorators.initializer
    def add_evaluation_handler(self, *args, **kwargs):
        handler_kwargs = {key: value for key, value in kwargs.items()}
        service_host = None

        if "evaluation_url" in kwargs:
            service_host = kwargs.get("evaluation_url")

        if not service_host:
            service_host = os.environ.get("EVALUATION_URL")

        if not service_host:
            raise communication.RegistrationError("No URL for the evaluation service can be found")

        handler_kwargs["service_host"] = service_host

        evaluation_port = None

        if 'evaluation_port' in kwargs:
            evaluation_port = kwargs.get("evaluation_port")

        if not evaluation_port:
            evaluation_port = os.environ.get("EVALUATION_PORT")

        handler_kwargs['service_port'] = evaluation_port

        path = None

        if 'evaluation_path' in kwargs:
            path = kwargs.get("evaluation_path")

        if not path:
            path = os.environ.get("EVALUATION_PATH")

        handler_kwargs['path'] = path

        setattr(self, "_evaluation_handler", EvaluationRequestHandler(
            **handler_kwargs
        ))

    @decorators.socket_handler(**{decorators.MESSAGE_TYPE_ATTRIBUTE: EvaluationMessage})
    def get_evaluation_handler(self):
        return getattr(self, "_evaluation_handler")


class AlternateRequestService(
    communication.RegisteredWebSocketInterface,
    EchoEmitMixin,
    EvaluationInjector,
    SessionProviderMixin
):
    """
    An example interface used to demonstrate how to create a handler for a decorated interface
    """
    ...


def main():
    """
    Define your initial application code here
    """
    arguments = Arguments()
    example_handler = AlternateRequestService(port=arguments.port, use_ssl=False)
    example_handler.run()


# Run the following if the script was run directly
if __name__ == "__main__":
    main()
