"""
Defines a websocket consumer that does nothing other than pass messages directly to and from another websocket
to another service
"""
import typing
import pathlib
import asyncio
import ssl
import os

from consumers import SocketConsumer

from websockets.legacy.client import WebSocketClientProtocol
from websockets.legacy.client import connect as connect_to_socket

from dmod.core import common

from maas_experiment import logging
from forwarding import ForwardingConfiguration

LOGGER = logging.ConfiguredLogger()


class ForwardingSocket(SocketConsumer):
    """
    A WebSocket Consumer that simply passes messages to and from another connection
    """
    @classmethod
    def asgi_from_configuration(
        cls,
        configuration: ForwardingConfiguration
    ) -> typing.Coroutine[typing.Any, typing.Any, None]:
        interface = cls.as_asgi(
            target_host_name=configuration.name,
            target_host_url=configuration.url,
            target_host_path=configuration.path,
            target_host_port=configuration.port,
            use_ssl=configuration.use_ssl,
            certificate_path=configuration.certificate_path
        )

        return interface

    def __init__(
        self,
        target_host_name: str,
        target_host_url: str,
        target_host_port: typing.Optional[typing.Union[str, int]],
        target_host_path: str = None,
        use_ssl: bool = False,
        certificate_path: typing.Union[str, pathlib.Path] = None,
        *args,
        **kwargs
    ):
        """
        Constructor

        Args:
            target_host_name: A helpful name for the target that this proxy leads to
            target_host_url: The URL to the target that this proxy leads to
            target_host_port: The port for the target that this proxy leads to
            target_host_path: An additional path on the target service to the desired socket endpoint
            use_ssl: Whether to utilize SSL on the websocket connection
            certificate_path: The path to an SSL certificate to use if SSL is to be employed
        """
        super().__init__(*args, **kwargs)
        self.__target_host_name: str = target_host_name
        self.__target_host_url: str = target_host_url
        self.__target_host_port: typing.Optional[typing.Union[str, int]] = target_host_port
        self.__target_host_path: typing.Optional[str] = target_host_path or ""
        self.__use_ssl = use_ssl or False

        if target_host_url.startswith("wss://"):
            self.__use_ssl = True

        self._certificate_path: str = str(certificate_path) if certificate_path else None
        self.__connection: typing.Optional[WebSocketClientProtocol] = None
        self.__listen_task: typing.Optional[asyncio.Task] = None
        self._ssl_context: typing.Optional[ssl.SSLContext] = None

    @property
    def target_host_name(self) -> str:
        """
        The name of the service to connect to
        """
        return self.__target_host_name

    @property
    def target_host_url(self) -> str:
        """
        The URL of the service to connect to
        """
        return self.__target_host_url

    @property
    def target_host_port(self) -> typing.Optional[typing.Union[str, int]]:
        """
        The port of the service to connect to
        """
        return self.__target_host_port

    @property
    def uses_ssl(self) -> bool:
        return self.__use_ssl

    @property
    def certificate_path(self) -> typing.Optional[str]:
        return self._certificate_path

    @property
    def target_connection_url(self) -> str:
        """
        The full URL for the target service to connect to
        """
        # No protocol has to be given if the target url already has it
        if self.__target_host_url.startswith("ws://") or self.__target_host_url.startswith("wss://"):
            protocol: str = ""
        else:
            protocol = "wss://" if self.__use_ssl else "ws://"

        # The port needs to be attached to the url like ":PORT_NUMBER", so add ":" if there is a port defined
        port = f":{self.__target_host_port}" if self.__target_host_port else ""

        # Remove the ending '/' if it's there
        if port and self.__target_host_url.endswith("/"):
            host_url = self.__target_host_url[:-1]
        else:
            host_url = self.__target_host_url

        # If a path is given, prepend it with a '/' if it's not there
        if self.__target_host_path and not self.__target_host_path.startswith("/"):
            path = f"/{self.__target_host_path}"
        else:
            path = self.__target_host_path

        url = f"{protocol}{host_url}{port}{path}"

        return url

    @property
    def ssl_context(self) -> typing.Optional[ssl.SSLContext]:
        if not self.__use_ssl:
            return None

        if not self._ssl_context:
            self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if not self._certificate_path:
                raise ValueError(
                    f"An SSL certificate is required to connect to {self.__target_host_name} as configured, "
                    f"but none was given."
                )
            elif not os.path.exists(self._certificate_path):
                raise ValueError(
                    f"The SSL Certificate needed to connect to {self.__target_host_name} was not "
                    f"found at {self._certificate_path}"
                )
            elif os.path.isfile(self._certificate_path):
                self._ssl_context.load_verify_locations(cafile=self._certificate_path)
            else:
                self._ssl_context.load_verify_locations(capath=self._certificate_path)

        return self._ssl_context

    async def _connect_to_target(self):
        self.__connection = await connect_to_socket(uri=self.target_connection_url, ssl=self.ssl_context)

        if self.__listen_task is None:
            self.__listen_task = asyncio.create_task(self.listen(), name=f"ListenTo{self.__target_host_name}")

    async def connect(self):
        """
        Handler for when a client connects to this socket.
        """
        await super().accept()
        await self._connect_to_target()

    async def disconnect(self, code):
        """
        Handler for when a client disconnects
        """
        # Attempt to cancel the task. This is mostly a safety measure. Cancelling here is preferred but a
        # failure isn't the end of the world
        if self.__listen_task is not None and not self.__listen_task.done():
            try:
                cancel_results: common.tasks.CancelResults = await common.cancel_task(
                    task=self.__listen_task,
                    cancel_message=f"Client disconnected from proxy to {self.target_connection_url}"
                )

                if not cancel_results.cancelled:
                    LOGGER.warn(
                        f"Could not cancel the listener task for the Proxy Client named '{self.identifier}' "
                        f"connecting from '{self.scope_data.client}' to '{self.target_connection_url}'"
                    )
            except Exception as cancel_exception:
                LOGGER.error(
                    f"Could not cancel the listener task for the Proxy Client named '{self.identifier}' "
                    f"connecting from '{self.scope_data.client}' to '{self.target_connection_url}'",
                    cancel_exception
                )

        # Attempt to close the websocket connection. As above, this is mostly a safety measure.
        # Closing here is preferred but a failure isn't the end of the world
        if self.__connection is not None and not self.__connection.closed:
            try:
                # Since the close function for the connection is async, wrap it in a task to yield more control
                # over how it's handled
                close_task: asyncio.Task = asyncio.create_task(
                    self.__connection.close(
                        reason=f"Proxy client {self.identifier} disconnected from "
                    ),
                    name=f"Waiting_to_close_connection_to_{self.target_connection_url}_on_proxy_{self.identifier}"
                )

                # Wait a brief period of time for the connection to close. Hopefully it closes but it won't be
                # debilitating if it takes too long.
                connection_closed: bool = await common.wait_on_task(
                    close_task
                )

                if not connection_closed:
                    LOGGER.warn(
                        f"The Proxy Client {self.identifier} could not disconnect from {self.target_connection_url} "
                        f"within {common.tasks.DEFAULT_TASK_WAIT_SECONDS} seconds."
                    )
            except Exception as close_exception:
                LOGGER.error(
                    f"The Proxy Client {self.identifier} could not disconnect from {self.target_connection_url}",
                    close_exception
                )

    async def listen(self):
        """
        Listen for messages from the target connection and send them through the caller connection
        """
        if self.__connection is None:
            await self._connect_to_target()

        async for message in self.__connection:
            if isinstance(message, bytes):
                await self.send(bytes_data=message)
            else:
                await self.send(message)

    async def receive(self, text_data: str = None, bytes_data: bytes = None, **kwargs):
        """
        Processes messages received via the socket.

        Called when the other end of the socket sends a message

        Args:
            text_data: Text data sent over the socket
            bytes_data: Bytes data sent over the socket
            **kwargs:
        """
        if bytes_data and not text_data:
            await self.__connection.send(bytes_data)
        elif text_data:
            await self.__connection.send(text_data)
        else:
            LOGGER.warn("A message was received from the client but not text or bytes data was received.")

    def __str__(self):
        return f"Proxy Client {self.identifier} from {self.scope_data.client} to {self.target_connection_url}"
