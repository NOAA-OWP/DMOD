from __future__ import annotations
import sys
import typing
import os
import abc
import collections
import inspect
import enum
import logging
import traceback

from datetime import datetime
from functools import total_ordering
from pprint import pprint
from collections import abc as abstract_collections

MESSAGE = typing.Union[bytes, str, typing.Dict[str, typing.Any], typing.Sequence, bool, int, float]
MessageHandler = typing.Callable[[MESSAGE], typing.NoReturn]
ReasonToWrite = typing.Union[str, typing.Dict[str, typing.Any]]


@total_ordering
class Verbosity(enum.Enum):
    """
    An enumeration detailing the density of information that may be transmitted, not to logs,
    but through things like streams and communicators
    """
    QUIET = "QUIET"
    """Emit very little information"""

    NORMAL = "NORMAL"
    """Emit a baseline amount of information"""

    LOUD = "LOUD"
    """Emit a lot of detailed (often diagnostic) information"""

    ALL = "ALL"
    """Emit everything, including raw data"""

    @classmethod
    def get_by_name(cls, name: str) -> Verbosity:
        if name:
            for member in cls:  # type: Verbosity
                if member.name.lower() == name.lower():
                    return member
        raise KeyError(f'Could not find a value named "{name}" in {cls.__name__}')

    @classmethod
    def get_by_index(cls, index: typing.Union[int, float]) -> Verbosity:
        if isinstance(index, float):
            index = int(float)

        individual_values = list(cls)

        if index > len(individual_values):
            raise ValueError(f'There is no {cls.__name__} with an index of "{index}"')

        return individual_values[index]

    @classmethod
    def get(cls, value: typing.Union[int, float, str, Verbosity]) -> Verbosity:
        if isinstance(value, Verbosity):
            return value

        if isinstance(value, (float, int)):
            return cls.get_by_index(value)

        if isinstance(value, str):
            return cls.get_by_name(value)

        raise ValueError(f'"{value} ({type(value)}" cannot be interpretted as a {cls.__name__} object')

    @property
    def index(self) -> int:
        for index, member in enumerate(self.__class__):
            if self == member:
                return index

        raise RuntimeError(f"Could not determine the index of the enum member {repr(self)}")

    def __eq__(self, other):
        if other is None:
            return False

        if isinstance(other, Verbosity):
            return self.value == other.value

        if isinstance(other, str):
            return self.value.lower() == other.lower()

        if isinstance(other, (int, float)):
            return self.index == other

        return False

    def __gt__(self, other):
        if isinstance(other, Verbosity):
            return self.index > other.index

        if isinstance(other, str):
            return self.index > self.__class__.get_by_name(other).index

        if isinstance(other, (int, float)):
            return self.index > other

        return ValueError(f"Cannot compare {self.__class__.__name__} to {other}")

    def __hash__(self):
        return hash(self.value)


@typing.runtime_checkable
class CommunicationProtocol(typing.Protocol):
    """
    A protocol setting the expectations for what methods are used for a mechanism used for communicating with
    multiple processes
    """
    def error(self, message: str, exception: Exception = None, verbosity: Verbosity = None, publish: bool = None):
        pass

    def info(self, message: str, verbosity: Verbosity = None, publish: bool = None):
        pass

    def read_errors(self) -> typing.Iterable[str]:
        pass

    def read_info(self) -> typing.Iterable[str]:
        pass

    def write(self, reason: ReasonToWrite, data: dict):
        pass

    def read(self) -> typing.Any:
        pass

    def update(self, **kwargs):
        pass

    @property
    def communicator_id(self) -> str:
        ...

    @property
    def verbosity(self) -> Verbosity:
        """
        Returns:
            How verbose this communicator is
        """
        ...


class Communicator(abc.ABC):
    """
    The base class for a tool that may be used to broadcast messages across multiple processes and services in
    the style of a logger

    For example, writing to an implementation of a Communicator might fan out a single message to multiple machines,
    each with their own processes and handlers
    """
    def __init__(
        self,
        communicator_id: str,
        verbosity: Verbosity = None,
        on_receive: typing.Union[MessageHandler, typing.Sequence[MessageHandler]] = None,
        handlers: typing.Dict[str, typing.Union[MessageHandler, typing.Sequence[MessageHandler]]] = None,
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
        handlers: typing.Union[MessageHandler, typing.Sequence[MessageHandler]]
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
    def write(self, reason: ReasonToWrite, data: dict):
        pass

    @abc.abstractmethod
    def read(self) -> typing.Any:
        pass

    @abc.abstractmethod
    def update(self, **kwargs):
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


CommunicatorImplementation = typing.TypeVar('CommunicatorImplementation', bound=Communicator, covariant=True)


class StandardCommunicator(Communicator):
    """
    A very basic communicator that operates on stdout, stderr, and stdin
    """
    def __init__(self, *args, include_timestamp: bool = True, read_message: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__errors: typing.List[str] = []
        self.__info: typing.List[str] = []
        self.__include_timestamp = bool(include_timestamp)
        self.__properties: typing.Dict[str, typing.Any] = {}
        self.__read_message = read_message if isinstance(read_message, str) else ""

    def error(self, message: str, exception: Exception = None, verbosity: Verbosity = None, publish: bool = None):
        if verbosity and self._verbosity < verbosity:
            return

        if exception and exception.__traceback__:
            formatted_exception = os.linesep.join(
                traceback.format_exception(
                    type(exception),
                    exception,
                    exception.__traceback__
                )
            )
            print(formatted_exception, file=sys.stderr)
        elif exception:
            message += f" ERROR: {exception}"

        if self.__include_timestamp:
            timestamp = datetime.now().astimezone().strftime("%Y%m%d %H:%M%z")
            message = f"[{timestamp}] {message}"

        print(message, file=sys.stderr)

        if publish:
            self.write(reason="error", data={"error": message})

        # Call every event handler for the 'error' event
        for handler in self._handlers.get("error", []):
            handler(message)

    def info(self, message: str, verbosity: Verbosity = None, publish: bool = None):
        if self.__include_timestamp:
            timestamp = datetime.now().astimezone().strftime("%Y%m%d %H:%M%z")
            message = f"[{timestamp}] {message}"

        print(message)

        if publish:
            self.write(reason="info", data={"info": message})

        # Call every event handler for the 'info' event
        for handler in self._handlers.get("info", []):
            handler(message)

    def read_errors(self) -> typing.Iterable[str]:
        return (message for message in self.__errors)

    def read_info(self) -> typing.Iterable[str]:
        return (message for message in self.__info)

    def _validate(self) -> typing.Sequence[str]:
        return []

    def write(self, reason: ReasonToWrite, data: dict):
        """
        Writes data to the communicator's channel

        Takes the form of:

        {
            "event": reason,
            "time": YYYY-mm-dd HH:MMz,
            "data": json string
        }

        Args:
            reason: The reason for data being written to the channel
            data: The data to write to the channel; will be converted to a string
        """
        message = {
            "event": reason,
            "time": datetime.now().astimezone().strftime("%Y%m%d %H:%M%z"),
            "data": data
        }

        pprint(message, indent=4)

        try:
            for handler in self._handlers.get('write', []):
                handler(message)
        except:
            # Leave room for a breakpoint
            raise

    def read(self) -> typing.Any:
        return input(self.__read_message)

    def update(self, **kwargs):
        self.__properties.update(kwargs)

    def __getitem__(self, item):
        return self.__properties[item]


class CommunicatorGroup(abstract_collections.Mapping):
    """
    A collection of Communicators clustered for group operations
    """
    def __getitem__(self, key: str) -> CommunicationProtocol:
        return self.__communicators[key]

    def __len__(self) -> int:
        return len(self.__communicators)

    def __iter__(self) -> typing.Iterator[CommunicationProtocol]:
        return iter(self.__communicators.values())

    def __contains__(self, key: typing.Union[str, CommunicationProtocol]) -> bool:
        if isinstance(key, Communicator):
            return key in self.__communicators.values()

        return key in self.__communicators

    def __init__(
        self,
        communicators: typing.Union[
            CommunicationProtocol,
            typing.Iterable[CommunicationProtocol],
            typing.Mapping[str, CommunicationProtocol]
        ] = None
    ):
        """
        Constructor

        Args:
            communicators: Communicators to be used by the collection
        """
        if isinstance(communicators, typing.Mapping):
            self.__communicators: typing.Dict[str, CommunicationProtocol] = dict(communicators.items())
        elif isinstance(communicators, typing.Sequence):
            self.__communicators: typing.Dict[str, CommunicationProtocol] = {
                communicator.communicator_id: communicator
                for communicator in communicators
            }
        elif isinstance(communicators, CommunicationProtocol):
            self.__communicators = {
                communicators.communicator_id: communicators
            }
        else:
            self.__communicators: typing.Dict[str, CommunicationProtocol] = {}

    def attach(
        self,
        communicator: typing.Union[
            CommunicationProtocol,
            typing.Sequence[CommunicationProtocol],
            typing.Mapping[typing.Any, CommunicationProtocol]
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
            self.__communicators: typing.Dict[str, CommunicationProtocol] = dict(communicator.items())
        elif isinstance(communicator, typing.Sequence):
            self.__communicators.update({
                communicator.communicator_id: communicator
                for communicator in communicator
            })
        elif isinstance(communicator, CommunicationProtocol):
            self.__communicators[communicator.communicator_id] = communicator
        else:
            self.__communicators: typing.Dict[str, CommunicationProtocol] = {}

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

    def write(self, reason: ReasonToWrite, data: dict, verbosity: Verbosity = None):
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
        except Exception as e:
            message = traceback.format_exc()

            # The message is also printed since logging sometimes forces all newlines into a single line with just
            # the "\n" character, making the error hard to read
            print(message)
            raise Exception(message) from e

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
                errors.union(set(self.__communicators[communicator_id].read_errors()))
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
                information.union(set(communicator.read_info()))
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
            communicator
            for communicator in self.__communicators.values()
            if communicator.verbosity == Verbosity.ALL
        ])

    def __str__(self):
        return f"Communicators: {', '.join([str(communicator) for communicator in self.__communicators])}"

    def __repr__(self):
        return self.__str__()

    @property
    def empty(self):
        return len(self.__communicators) == 0
