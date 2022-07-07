import typing
import os
import abc
import collections
import inspect

MESSAGE = typing.Union[bytes, str, typing.Dict[str, typing.Any], typing.Sequence, bool, int, float]
MESSAGE_HANDLER = typing.Callable[[MESSAGE], typing.NoReturn]
REASON_TO_WRITE = typing.Union[str, typing.Dict[str, typing.Any]]


class Communicator(abc.ABC):
    def __init__(
        self,
        communicator_id: str,
        on_receive: typing.Union[MESSAGE_HANDLER, typing.Sequence[MESSAGE_HANDLER]] = None,
        handlers: typing.Dict[str, typing.Union[MESSAGE_HANDLER, typing.Sequence[MESSAGE_HANDLER]]] = None,
        **kwargs
    ):
        self.__communicator_id = communicator_id
        self._handlers = collections.defaultdict(list)

        if handlers:
            if not isinstance(handlers, typing.Mapping):
                raise ValueError(
                    f"The handlers object passed to the communicator for {communicator_id} was not some form of mapping"
                )

            for event_name, handler in handlers.items():
                self._register_handler(event_name, handler)

        if on_receive:
            self._register_handler('receive', on_receive)

        validation_messages = self._validate()

        if validation_messages:
            joined_messages = os.linesep + os.linesep.join(validation_messages)
            raise ValueError(f"Communication with {communicator_id} could not be established: {joined_messages}")

    def _register_handler(
        self,
        event_name: str,
        handlers: typing.Union[MESSAGE_HANDLER, typing.Sequence[MESSAGE_HANDLER]]
    ):
        if isinstance(handlers, typing.Sequence) and handlers:
            for handler in handlers:
                if not isinstance(handler, typing.Callable):
                    raise ValueError(
                        f"A handler for {event_name} was passed for the communicator {self.communicator_id} was "
                        f"not a function"
                    )

                signature = inspect.signature(handler)
                if len(signature.parameters) == 0:
                    raise ValueError(
                        f"All event handlers for the {self.communicator_id} communicator must have "
                        f"at least one argument"
                    )
                self._handlers[event_name].append(handler)
        elif isinstance(handlers, typing.Callable):
            self._handlers[event_name].append(handlers)
        elif handlers is not None:
            raise ValueError(
                f"The item passed as a handler for the {event_name} event for the {self.communicator_id} "
                f"communicator cannot be used as a function"
            )

    @abc.abstractmethod
    def error(self, message: str, exception: Exception = None, publish: bool = None):
        pass

    @abc.abstractmethod
    def info(self, message: str, publish: bool = None):
        pass

    @abc.abstractmethod
    def read_errors(self) -> typing.Iterable[str]:
        pass

    @abc.abstractmethod
    def read_info(self) -> typing.Iterable[str]:
        pass

    @abc.abstractmethod
    def _validate(self) -> typing.Sequence[str]:
        pass

    @abc.abstractmethod
    def write(self, reason: REASON_TO_WRITE, data: dict):
        pass

    @abc.abstractmethod
    def read(self) -> typing.Any:
        pass

    @abc.abstractmethod
    def update(self, **kwargs):
        pass

    @abc.abstractmethod
    def sunset(self, seconds: float = None):
        pass

    @property
    def communicator_id(self) -> str:
        return self.__communicator_id
