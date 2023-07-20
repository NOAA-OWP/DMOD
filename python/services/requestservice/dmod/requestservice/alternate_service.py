#!/usr/bin/env python3
import abc
import os
import typing
import secrets
import asyncio
import random
import json

from argparse import ArgumentParser

from datetime import datetime

import websockets
from dmod.communication import Field
from dmod.communication import Response
from websockets import WebSocketCommonProtocol

from dmod.externalrequests import duplex
from dmod.externalrequests import AuthHandler
from dmod.externalrequests import EvaluationRequestHandler
from dmod.externalrequests import OpenEvaluationMessage
from dmod.externalrequests import LaunchEvaluationMessage
from dmod.core import decorators

import dmod.communication as communication
import dmod.access as access


EVALUATION_SERVICE_NAME = os.environ.get("EVALUATION_SERVICE_NAME", "EvaluationService")


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


class TestMessage(communication.FieldedMessage):
    """
    A basic initialization message to receive for testing
    """
    @classmethod
    def _get_fields(cls) -> typing.Collection[Field]:
        return [
            communication.Field("message_id", required=True)
        ]


class Emitter(duplex.Producer):
    async def __call__(self, *args, **kwargs) -> Response:
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
                await self.send_back_to_sources(message)
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

        return duplex.DuplexResponse(
            success=success,
            message=response_message,
            reason=reason,
            data={
                "messages_sent": message_count,
                "duration": str(datetime.now() - start_time)
            }
        )


class EmitMixin:
    """
    A mixin class for adding the 'emit_message' socket handler to a service
    """
    @decorators.initializer
    def add_emitter(self, *args, **kwargs):
        self.add_producer(Emitter)


class EchoMessage(communication.FieldedMessage):
    @classmethod
    def _get_fields(cls) -> typing.Collection[Field]:
        return [
            communication.Field("message", data_type=str, required=True, description="The message to print")
        ]


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

        handler = EvaluationRequestHandler(
            target_service=EVALUATION_SERVICE_NAME,
            **handler_kwargs
        )

        setattr(self, "_evaluation_handler", handler)

    @decorators.socket_handler(**{decorators.MESSAGE_TYPE_ATTRIBUTE: OpenEvaluationMessage})
    def connect_to_evaluation(self) -> duplex.DuplexRequestHandler:
        """
        Returns:
            The handler object that handles `OpenEvaluationMessage`s
        """
        return getattr(self, "_evaluation_handler")

    @decorators.socket_handler(**{decorators.MESSAGE_TYPE_ATTRIBUTE: LaunchEvaluationMessage})
    def get_evaluation_launcher(self) -> duplex.DuplexRequestHandler:
        """
        Returns:
            The handler object that handles `LaunchEvaluationMessage`s
        """
        return getattr(self, "_evaluation_handler")


class EchoMixin:
    """
    A mixin class for adding the 'emit_message' socket handler to a service
    """
    @decorators.initializer
    def add_echo(self, *args, **kwargs):
        """
        Adds the `echo` handlers to the `BaseDuplexHandler` this gets attached to

        Args:
            *args:
            **kwargs:

        Returns:

        """
        # Set this up to echo typed messages from the source
        self.add_source_handler_route(
            EchoMessage,
            self.echo_typed_message
        )

        # Set this up to echo typed messages from the target
        self.add_target_handler_route(
            EchoMessage,
            self.echo_typed_message
        )

        # Set this up to echo untyped messages from the source
        self.add_source_message_handler(
            "echo",
            self.echo_message
        )

        # Set this up to echo untyped messages from the client
        self.add_target_message_handler(
            "echo",
            self.echo_message
        )

    async def echo_typed_message(
        self,
        message: communication.FieldedMessage,
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        *args,
        **kwargs
    ):
        """
        Takes data from an explicitly typed echo message and prints it to stdout

        Args:
            message: The typed message to print
            source: The socket where the message came from
            target: The opposing socket
            *args:
            **kwargs:

        Returns:

        """
        # Get the message variable
        message_to_print = message['message']

        print(message_to_print)

        # Create a reply to send back to the source of the message to notify it that the data was printed
        notification = {
            "info": f"printed '{message_to_print}'"
        }

        # Package it up in a string for transmission
        prepared_notification = json.dumps(notification, indent=4)
        await source.send(prepared_notification)

    async def echo_message(
        self,
        message: typing.Union[str, bytes, dict],
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ) -> None:
        """
        Prints all received messages to stdout

        Args:
            message: The message sent over the socket
            source: The socket that receives the messages
            target: The socket that is the target of the handler
            path: The path to the source socket on the server

        Returns:
            A response reporting how successful the overall operation was
        """
        # Determine if the message should actually be printed. Since this is an untyped message, this will be
        # called for every generic message that comes through its source. To avoid unnecessary printing, 'shoud'
        # print needs to be set
        should_print = True

        # Checking is easy on a dictionary because we just need to look for a value
        if isinstance(message, dict):
            try:
                should_print = bool(message.get("should_print", should_print))
                message = json.dumps(message, indent=4)
            except:
                message = str(message)
        else:
            # It's harder to check bytes or a string since it has to be deserialized. Attempt to deserialize the
            # value, but just accept the error if that doesn't work. This will handle the case where plain text comes
            # through
            try:
                data = json.loads(message)
                if 'should_print' in data:
                    should_print = bool(data.get('should_print', ))
            except:
                pass

        # Go ahead and print to stdout if there was no indication that we shouldn't
        if should_print:
            print(message)

            # Create a reply to send back to the source of the message to notify it that the data was printed
            notification = {
                "info": f"printed '{message}'"
            }

            # Package it up in a string for transmission
            prepared_notification = json.dumps(notification, indent=4)
            await source.send(prepared_notification)


class TestHandler(EmitMixin, EchoMixin, duplex.DuplexRequestHandler):
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


class EchoEmitInjector:
    """
    Mixin that injects a TestHandler instance that launches from a TestMessage
    """

    @decorators.initializer
    def initialize_echo_emit_handler(self, listen_host: str, port: typing.Union[str, int], *args, **kwargs):
        """
        Adds a handler object as a member variable that handles operations from `TestMessage`s

        Args:
            listen_host: The host for the TestService
            port: The port for the test service
            *args:
            **kwargs:
        """
        handler = TestHandler(
            target_service="TestService",
            service_host=listen_host,
            service_port=port,
            *args,
            **kwargs
        )
        setattr(self, "_test_handler", handler)

    @decorators.socket_handler(**{decorators.MESSAGE_TYPE_ATTRIBUTE: TestMessage})
    def get_test_handler(self):
        """
        Returns:
            The added `TestHandler`
        """
        return getattr(self, "_test_handler")


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


class SessionInjector:
    """
    Mixin that injects a handler for session interactions
    """
    @decorators.initializer
    def initialize_session_handler(self, *args, **kwargs):
        setattr(
            self,
            "_session_handler",
            SessionHandler(target_service="Session", *args, **kwargs)
        )

    @decorators.socket_handler(**{decorators.MESSAGE_TYPE_ATTRIBUTE: communication.SessionInitMessage})
    def get_session_handler(self):
        """
        Returns:
            The handler used a request for initializing session is requested.
        """
        return getattr(self, "_session_handler")

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
        session_handler: SessionHandler = getattr(self, "_session_handler")
        return {
            "session_manager": session_handler.session_manager
        }


class AlternateRequestService(
    communication.RegisteredWebSocketInterface,
    EchoEmitInjector,
    EvaluationInjector,
    SessionInjector
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
