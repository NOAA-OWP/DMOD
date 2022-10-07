"""
Defines a `Producer` object that can produce and send messages
"""
import typing
import abc
import asyncio

from websockets import WebSocketCommonProtocol

from dmod.communication import Response

SOCKET_OR_SOCKETS = typing.Union[WebSocketCommonProtocol, typing.Sequence[WebSocketCommonProtocol]]
MESSAGE_DATA = typing.Union[str, bytes, bytearray, memoryview]

MESSAGE_PAYLOAD = typing.Union[
    str,
    bytes,
    typing.Iterable[str],
    typing.Iterable[bytes],
    typing.AsyncIterable[str],
    typing.AsyncIterable[bytes]
]


ProducerType = typing.Type["Producer"]


class Producer(abc.ABC):
    """
    A callable that may produce its own data to send to a series of source or target socket connections,
    but not read from them

    Producers cannot read from shared sockets. Reading can and will conflict with other processes/threads trying to do
    the same which is an illegal operation.
    """
    @classmethod
    def get_name(cls) -> str:
        """
        Get the name of the producer
        """
        ...

    @classmethod
    def start(cls, sources: SOCKET_OR_SOCKETS, targets: SOCKET_OR_SOCKETS, *args, **kwargs) -> asyncio.Task[Response]:
        """
        Call the Producer with the given parameters and return a Task object for outside management

        Args:
            sources: One or more socket connections that come from some a common source
            targets: One or more socket connections that go to a targetted service
            *args:
            **kwargs:

        Returns:
            The instance call wrapped in an asynchronous Task
        """
        instance = cls(sources, targets, *args, **kwargs)
        return asyncio.create_task(instance(*args, **kwargs), name=cls.get_name())

    def __init__(self, sources: SOCKET_OR_SOCKETS, targets: SOCKET_OR_SOCKETS, *args, **kwargs):
        """
        Constructor

        Under no circumstances should implementing classes have access to `__targets` or `__sources`

        Args:
            sources: One or more socket connections pointing towards the originator of this producer
            targets: One or more socket connections pointing towards the target of the originator of this producer
            *args:
            **kwargs:
        """
        self.__targets = targets if isinstance(targets, typing.Sequence) else [targets]
        self.__sources = sources if isinstance(sources, typing.Sequence) else [sources]

    async def send_to_targets(self, data: typing.Union[str, bytes]):
        """
        Send produced data to all registered target services

        Args:
            data: The data to send
        """
        if not data:
            return

        await asyncio.gather(*[
            asyncio.create_task(target.send(data))
            for target in self.__sources
        ])

    async def send_back_to_sources(self, data: MESSAGE_PAYLOAD):
        """
        Send produced data back to all registered sources

        Args:
            data: The produced data to send
        """
        if not data:
            return

        await asyncio.gather(*[
            asyncio.create_task(source.send(data))
            for source in self.__sources
        ])

    @abc.abstractmethod
    async def __call__(self, *args, **kwargs) -> Response:
        """
        Call the producer logic

        Args:
            *args:
            **kwargs:

        Returns:
            A response detailing how the producer functioned
        """
        ...

    def __str__(self):
        return f"{self.get_name()}(*args, **kwargs)"

    def __repr__(self):
        return f"{self.get_name()}(*args, **kwargs)"
