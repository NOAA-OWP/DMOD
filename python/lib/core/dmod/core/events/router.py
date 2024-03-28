"""
Mechanism for routing event data to handlers
"""
from __future__ import annotations

import typing
import inspect
import logging

from .base_function import EventFunctionParameter
from .base_function import Signature
from .base_function import EventFunctionGroup
from .base_function import Event
from .base_function import BasicParameter

SIGNATURE = typing.Union[
    Signature,
    inspect.Signature,
    typing.Sequence[EventFunctionParameter],
    typing.Callable,
    typing.Sequence[BasicParameter]
]


class EventRouter:
    """
    Routes events and their payloads to their handlers
    """
    def __init__(
        self,
        fail_on_missing_event: bool = None,
        allow_errors: bool = None,
        events: typing.Dict[str, SIGNATURE] = None,
        **handlers: typing.Union[typing.Callable, typing.Sequence[typing.Callable]]
    ):
        """
        Constructor

        Args:
            fail_on_missing_event: Whether a routing call should throw an error if no matching event was registered. Default: False
            allow_errors: Allow errors to be logged rather than halt operations. Default: True
            events: A predefined mapping linking an event and what the event's handler signature should look like
            handlers: Handlers for events that should be registered
        """
        if events is None:
            events = dict()

        self.__fail_on_missing_event: bool = fail_on_missing_event or False
        self.__allow_errors = allow_errors or True
        self.__events: typing.Dict[str, EventFunctionGroup] = dict()

        for event_name, signature in events.items():
            self.register_event(event_name, signature)

        for event_name, event_handlers in handlers.items():
            self.register_handler(event_name, event_handlers)

    def register_event(self, event: str, signature: SIGNATURE) -> EventRouter:
        """
        Register a handler signature with an event

        Args:
            event: The name of the event to register
            signature: The expected signature for functions that will handle the event

        Returns:
            The updated EventRouter
        """
        if event in self.__events:
            return self

        if isinstance(signature, typing.Callable):
            signature: Signature = Signature.from_function(signature)
        elif isinstance(signature, inspect.Signature):
            signature: Signature = Signature.from_signature(signature)
        elif isinstance(signature, typing.Sequence):
            signature = Signature(signature)

        self.__events[event] = EventFunctionGroup(signature, allow_errors=self.__allow_errors)
        return self

    def register_handler(
        self,
        event: str,
        handler: typing.Union[typing.Callable, typing.Sequence[typing.Callable]]
    ) -> EventRouter:
        if not handler:
            return self

        if not isinstance(handler, typing.Sequence):
            handler = list(handler) if isinstance(handler, typing.Iterable) else [handler]

        if not handler:
            return self

        if event not in self.__events:
            logging.debug(
                f"There is no registered event for '{event}' - "
                f"a new event is being registered but the required signatures may be incorrect."
            )
            self.register_event(event, handler[0])

        invalid_functions = list()

        for event_handler in handler:
            self.__events[event].add_function(event_handler, invalid_functions, allow_errors=self.__allow_errors)

        if len(invalid_functions) > 0:
            raise ValueError(
                f"The following handlers cannot be added for the '{event}' event: {', '.join(invalid_functions)}"
            )

        return self

    def __call__(self, event: typing.Union[str, Event], *args, **kwargs) -> typing.List[typing.Awaitable]:
        if isinstance(event, str):
            event = Event(event_name=event)

        if not (self.__fail_on_missing_event or event.event_name in self.__events):
            return list()
        elif event.event_name not in self.__events:
            raise ValueError(f"There are no registered handlers for the '{event.event_name}' event")

        return self.__events[event.event_name](event, *args, **kwargs)

    async def fire(self, event: typing.Union[str, Event], *args, **kwargs):
        if isinstance(event, str):
            event = Event(event_name=event)

        if not (self.__fail_on_missing_event or event.event_name in self.__events):
            return
        elif event.event_name not in self.__events:
            raise ValueError(f"There are no registered handlers for the '{event.event_name}' event")

        await self.__events[event.event_name].fire(event, *args, **kwargs)
