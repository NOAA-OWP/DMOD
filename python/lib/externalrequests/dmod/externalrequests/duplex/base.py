"""
Defines the base class for duplex handlers
"""
import abc

from dmod.communication import AbstractInitRequest
from dmod.communication import AbstractRequestHandler
from .producer import ProducerType
from .response import DuplexResponse
from .types import *


class BaseDuplexHandler(AbstractRequestHandler, abc.ABC):
    """
    Base class for full handler implementations and mixins that feature bidirectional communication
    """
    @property
    @abc.abstractmethod
    def target_service(self) -> str:
        """
        Returns:
            A human friendly name for what service this handler should be targetting
        """
        ...

    @classmethod
    def _get_response_class(cls) -> typing.Type[Response]:
        """
        Get the type of default response that this class will return from the handler

        Override for custom response types

        Returns:
            The type of default Response that this handler should use
        """
        return DuplexResponse

    @property
    @abc.abstractmethod
    def has_initialized(self) -> bool:
        """
        Whether the initialization function for this handler was successfully run
        """
        ...

    @abc.abstractmethod
    def add_producer(self, producer: ProducerType):
        """
        Add a function that produces messages to send through the client and/or server connections without their
        prompting

        Args:
            producer: The function that will produce messages
        """
        ...

    @abc.abstractmethod
    def add_source_message_handler(self, handler_name: str, handler: MESSAGE_HANDLER):
        """
        Add a basic handler that will act on a string that arrives through the server connection

        Args:
            handler_name: The name of the handler to add
            handler: The handler to add
        """
        ...

    @abc.abstractmethod
    def get_source_handler_routes(self) -> typing.Dict[typing.Type[FieldedMessage], typing.Iterable[TYPED_MESSAGE_HANDLER]]:
        """
        Get all typed handlers for source messages
        """
        ...

    @abc.abstractmethod
    def add_source_handler_route(self, message_type: typing.Type[FieldedMessage], handler: TYPED_MESSAGE_HANDLER):
        """
        Adds a typed message handler that acts on specific messages coming through the server connection

        Args:
            message_type: The type of message that the handler expects
            handler: The function that acts on the given type of message
        """
        ...

    @abc.abstractmethod
    def add_target_message_handler(self, handler_name: str, handler: MESSAGE_HANDLER):
        """
        Add a basic handler that will act on a string that arrives through the client connection

        Args:
            handler_name: The name of the handler to add
            handler: The handler to add
        """
        ...

    @abc.abstractmethod
    def get_target_handler_routes(self) -> typing.Dict[typing.Type[FieldedMessage], typing.Iterable[TYPED_MESSAGE_HANDLER]]:
        """
        Get all typed handlers for messages from the target
        """
        ...

    @abc.abstractmethod
    def add_target_handler_route(self, message_type: typing.Type[FieldedMessage], handler: TYPED_MESSAGE_HANDLER):
        """
        Adds a typed message handler that acts on specific messages coming through the client connection

        Args:
            message_type: The type of message that the handler expects
            handler: The function that acts on the given type of message
        """
        ...

    @abc.abstractmethod
    def add_initial_message_handler(self, handler: MESSAGE_HANDLER):
        """
        Add a message handler that will attempt to act on a message when this handler first accepts a connection

        Args:
            handler: A function that might handle a message
        """
        ...

    async def __call__(
        self,
        request: AbstractInitRequest,
        source: WebSocketCommonProtocol,
        path: str = None,
        **kwargs
    ) -> Response:
        """
        Turn the class into a callable that just calls the required `handle_request`

        Args:
            request: The request for the handler to handler
            source: The socket through which the message arrived
            path: The path to the entry point of this socket
            **kwargs:

        Returns:
            The results of the required `handle_request`
        """
        return await self.handle_request(request=request, source=source, path=path, **kwargs)
