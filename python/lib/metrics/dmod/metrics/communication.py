import typing
import os
import abc
import collections
import inspect
import enum
import logging
import traceback

from collections import abc as abstract_collections

MESSAGE = typing.Union[bytes, str, typing.Dict[str, typing.Any], typing.Sequence, bool, int, float]
MESSAGE_HANDLER = typing.Callable[[MESSAGE], typing.NoReturn]
REASON_TO_WRITE = typing.Union[str, typing.Dict[str, typing.Any]]


class Verbosity(enum.IntEnum):
    """
    An enumeration detailing the density of information that may be transmitted, not to logs,
    but through things like streams and communicators
    """
    QUIET = enum.auto()
    """Emit very little information"""

    NORMAL = enum.auto()
    """Emit a baseline amount of information"""

    LOUD = enum.auto()
    """Emit a lot of detailed (often diagnostic) information"""

    ALL = enum.auto()
    """Emit everything, including raw data"""


class Communicator(abc.ABC):
    def __init__(
        self,
        communicator_id: str,
        verbosity: Verbosity = None,
        on_receive: typing.Union[MESSAGE_HANDLER, typing.Sequence[MESSAGE_HANDLER]] = None,
        handlers: typing.Dict[str, typing.Union[MESSAGE_HANDLER, typing.Sequence[MESSAGE_HANDLER]]] = None,
        **kwargs
    ):
        self.__communicator_id = communicator_id
        self._handlers = collections.defaultdict(list)
        self._verbosity = verbosity or Verbosity.QUIET

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
        """
        Register event handlers

        Args:
            event_name: The name of the event
            handlers: one or more handlers for said event
        """
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
    def error(self, message: str, exception: Exception = None, verbosity: Verbosity = None, publish: bool = None):
        pass

    @abc.abstractmethod
    def info(self, message: str, verbosity: Verbosity = None, publish: bool = None):
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

    @property
    def verbosity(self) -> Verbosity:
        """
        Returns:
            How verbose this communicator is
        """
        return self._verbosity


class CommunicatorGroup(abstract_collections.Mapping):
    """
    A collection of Communicators clustered for group operations
    """
    def __getitem__(self, key: str) -> Communicator:
        return self.__communicators[key]

    def __len__(self) -> int:
        return len(self.__communicators)

    def __iter__(self) -> typing.Iterator[Communicator]:
        return iter(self.__communicators.values())

    def __contains__(self, key: typing.Union[str, Communicator]) -> bool:
        if isinstance(key, Communicator):
            return key in self.__communicators.values()

        return key in self.__communicators

    def __init__(
        self,
        communicators: typing.Union[
            Communicator,
            typing.Iterable[Communicator],
            typing.Mapping[str, Communicator]
        ] = None
    ):
        """
        Constructor

        Args:
            communicators: Communicators to be used by the collection
        """
        if isinstance(communicators, typing.Mapping):
            self.__communicators: typing.Dict[str, Communicator] = {
                key: value
                for key, value in communicators.items()
            }
        elif isinstance(communicators, typing.Sequence):
            self.__communicators: typing.Dict[str, Communicator] = {
                communicator.communicator_id: communicator
                for communicator in communicators
            }
        elif isinstance(communicators, Communicator):
            self.__communicators = {
                communicators.communicator_id: communicators
            }
        else:
            self.__communicators: typing.Dict[str, Communicator] = dict()

    def attach(
        self,
        communicator: typing.Union[
            Communicator,
            typing.Sequence[Communicator],
            typing.Mapping[typing.Any, Communicator]
        ]
    ) -> int:
        """
        Adds one or more communicators to the collection

        Args:
            communicator: The communicator(s) to add

        Returns:
            The number of communicators now in the collection
        """
        if isinstance(communicator, typing.Mapping):
            self.__communicators: typing.Dict[str, Communicator] = {
                key: value
                for key, value in communicator.items()
            }
        elif isinstance(communicator, typing.Sequence):
            self.__communicators.update({
                communicator.communicator_id: communicator
                for communicator in communicator
            })
        elif isinstance(communicator, Communicator):
            self.__communicators[communicator.communicator_id] = communicator
        else:
            self.__communicators: typing.Dict[str, Communicator] = dict()

        return len(self.__communicators)

    def error(self, message: str, exception: Exception = None, verbosity: Verbosity = None, publish: bool = None):
        """
        Send an error to all communicators

        Args:
            message:
            exception:
            verbosity:
            publish:
        """
        if self.empty:
            logging.getLogger().error(message, exc_info=exception)

        for communicator in self.__communicators.values():
            communicator.error(
                message=message,
                exception=exception,
                verbosity=verbosity,
                publish=publish
            )

    def info(self, message: str, verbosity: Verbosity = None, publish: bool = None):
        """
        Send basic information to all communicators

        Args:
            message:
            verbosity:
            publish:
        """
        if self.empty:
            logging.log(level=logging.DEBUG, msg=message)

        for communicator in self.__communicators.values():
            communicator.info(message=message, verbosity=verbosity, publish=publish)

    def write(self, reason: REASON_TO_WRITE, data: dict, verbosity: Verbosity = None):
        """
        Write to all communicators

        If verbosity is passed, only communicators whose verbosity meets or exceeds the indicated
        verbosity will be written to

        Args:
            reason:
            data:
            verbosity:
        """
        try:
            for communicator in self.__communicators.values():
                if not verbosity or verbosity and communicator.verbosity >= verbosity:
                    communicator.write(reason=reason, data=data)
        except:
            message = traceback.format_exc()
            logging.error(message)

            # The message is also printed since logging sometimes forces all newlines into a single line with just
            # the "\n" character, making the error hard to read
            print(message)
            raise

    def update(self, communicator_id: str = None, **kwargs):
        """
        Update one or all communicators

        Args:
            communicator_id:
            **kwargs:
        """
        if communicator_id:
            self.__communicators[communicator_id].update(**kwargs)
        else:
            for communicator in self.__communicators.values():
                communicator.update(**kwargs)

    def sunset(self, seconds: float = None):
        """
        Set an expiration for all communicators

        Args:
            seconds:
        """
        for communicator in self.__communicators.values():
            communicator.sunset(seconds)

    def read_errors(self, *communicator_ids: str) -> typing.Iterable[str]:
        """
        Read all error messages from either a select few or all communicators

        Calling without communicator ids will result in all errors from all communicators

        Args:
            communicator_ids:

        Returns:
            All error messages
        """
        errors = set()

        if communicator_ids:
            for communicator_id in communicator_ids:
                errors.union({error for error in self.__communicators[communicator_id].read_errors()})
        else:
            for communicator in self.__communicators.values():
                errors.union(communicator.read_errors())

        return errors

    def read_info(self, *communicator_ids: str) -> typing.Iterable[str]:
        """
        Read all basic information from either a select few or all communicators

        Calling without communicator ids will result in all information from all communicators

        Args:
            communicator_ids:

        Returns:
            All information from the indicated communicators
        """
        information = set()

        if communicator_ids:
            communicators = [
                communicator
                for key, communicator in self.__communicators.items()
                if key in communicator_ids
            ]
            for communicator in communicators:
                information.union({message for message in communicator.read_info()})
        else:
            for communicator in self.__communicators.values():
                information.union(communicator.read_info())

        return information

    def read(self, communicator_id: str):
        """
        Read data from a specific communicator

        Args:
            communicator_id: The communicator to read from

        Returns:
            The read data
        """
        return self.__communicators[communicator_id].read()

    def send_all(self) -> bool:
        """
        Returns:
            True if there is a communicator that expects all data
        """
        return bool([
            communicator for communicator in self.__communicators.values() if communicator.verbosity == Verbosity.ALL
        ])

    def __str__(self):
        return f"Communicators: {', '.join([str(communicator) for communicator in self.__communicators])}"

    def __repr__(self):
        return self.__str__()

    @property
    def empty(self):
        return len(self.__communicators) == 0
