"""
Classes used to organize, validate, and orchestrate function calls
"""
from __future__ import annotations

import asyncio
import typing
import inspect
import logging

try:
    from typing import ParamSpec
    from typing import Concatenate
except ImportError:
    from typing_extensions import ParamSpec
    from typing_extensions import Concatenate

from dataclasses import field
from dataclasses import dataclass

from pydantic import root_validator

PARAMS = ParamSpec("PARAMS")


class Event:
    def __init__(self, event_name: str):
        self.__event_name: str = event_name

    @property
    def event_name(self) -> str:
        return self.__event_name


EVENT_HANDLER = typing.Callable[
    Concatenate[
        Event,
        PARAMS
    ],
    typing.Union[typing.Coroutine, typing.Any]
]


class BasicParameter(typing.TypedDict):
    index: int
    name: str
    type: typing.Optional[typing.Union[type, str]]
    is_kwargs: typing.Optional[bool]
    is_args: typing.Optional[bool]
    default: typing.Optional[typing.Any]
    required: typing.Optional[bool]


@dataclass
class EventFunctionParameter:
    index: int
    name: str
    type: typing.Optional[typing.Union[type, str]] = field(default=None)
    is_kwargs: typing.Optional[bool] = field(default=False)
    is_args: typing.Optional[bool] = field(default=False)
    default: typing.Optional = field(default=None)
    required: typing.Optional[bool] = field(default=False)
    positional_only: typing.Optional[bool] = field(default=False)
    keyword_only: typing.Optional[bool] = field(default=False)

    @classmethod
    def from_basic_parameter(cls, parameter: BasicParameter) -> EventFunctionParameter:
        return cls(
            index=parameter["index"],
            name=parameter["name"],
            type=parameter.get("type"),
            is_kwargs=parameter.get("is_kwargs", False),
            is_args=parameter.get("is_args", False),
            required=parameter.get("required", False),
            default=parameter.get("default")
        )

    @classmethod
    def from_function(cls, function: EVENT_HANDLER) -> typing.Sequence[EventFunctionParameter]:
        # List out the read versions of each inspection parameter
        # exclude the self parameter since that will be called implicitly
        return cls.from_signature(inspect.signature(function))

    @classmethod
    def from_signature(cls, signature: inspect.Signature) -> typing.Sequence[EventFunctionParameter]:
        return [
            cls.from_parameter(index, parameter)
            for index, parameter in enumerate(signature.parameters.values())
        ]

    @classmethod
    def from_parameter(cls, index: int, parameter: inspect.Parameter):
        parameter_type = None if parameter.annotation is parameter.empty else parameter.annotation

        if parameter_type in globals():
            parameter_type = globals()[parameter_type]

        return EventFunctionParameter(
            index=index,
            name=parameter.name,
            type=parameter_type,
            default=None if parameter.default is parameter.empty else parameter.default,
            required=parameter.default is parameter.empty and not parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD),
            positional_only=parameter.kind is parameter.POSITIONAL_ONLY,
            keyword_only=parameter.kind is parameter.KEYWORD_ONLY,
            is_args=parameter.kind is parameter.VAR_POSITIONAL,
            is_kwargs=parameter.kind is parameter.VAR_KEYWORD
        )

    @property
    def can_use_positional_or_keyword(self) -> bool:
        return not (self.positional_only or self.keyword_only)

    @property
    def is_required_and_positional_only(self) -> bool:
        return self.required and self.positional_only

    @root_validator
    def _correct_expectations(cls, values: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        keyword_only = values.get("keyword_only", False)
        is_args = values.get("is_args", False)
        is_kwargs = values.get("is_kwargs", False)
        has_default = "default" in values

        if "required" not in values and (keyword_only or is_args or is_kwargs or has_default):
            values['required'] = False

        return values

    def is_valid(self, value) -> bool:
        if self.type is None:
            return True

        origin = typing.get_origin(self.type) or self.type

        return isinstance(value, origin)

    def __hash__(self):
        return hash((self.required, self.name, self.type, self.positional_only, self.keyword_only))

    def __str__(self):
        if self.is_args:
            return f"*{self.name}"
        elif self.is_kwargs:
            return f"**{self.name}"
        return f"{self.name}" \
               f"{': ' + str(self.type) if self.type else ''}" \
               f"{' = ' + str(self.default) if not self.required else ''}"

    def __repr__(self):
        return str(self)


class Args(EventFunctionParameter):
    """
    Shortcut class to define a parameter to fit *args
    """
    def __init__(self, index: int, name: str = None):
        if name is None:
            name = "args"

        super().__init__(
            index=index,
            name=name,
            is_args=True
        )


class Kwargs(EventFunctionParameter):
    """
    Shortcut class to define a parameter to fit **kwargs
    """
    def __init__(self, index: int, name: str = None):
        if name is None:
            name = "kwargs"

        super().__init__(
            index=index,
            name=name,
            is_kwargs=True
        )


class Signature(typing.Sequence[EventFunctionParameter]):
    """
    Details the parameters used to call a function
    """
    def __getitem__(self, index) -> EventFunctionParameter:
        return self.__parameters[index]

    def __len__(self) -> int:
        return len(self.__parameters)

    @classmethod
    def from_function(cls, function: EVENT_HANDLER) -> Signature:
        """
        Create a signature by getting the individual parameters from a function

        Args:
            function: The function to create a signature for

        Returns:
            The signature describing the parameters in the function
        """
        return cls(parameters=EventFunctionParameter.from_function(function))

    @classmethod
    def from_signature(cls, signature: inspect.Signature) -> Signature:
        """
        Create a signature by getting the individual parameters from an inspection signature

        Args:
            signature: The inspection data for a function

        Returns:
            The signature describing the parameters in the function
        """
        return cls(parameters=EventFunctionParameter.from_signature(signature))

    def __init__(self, parameters: typing.Iterable[typing.Union[BasicParameter, EventFunctionParameter]]):
        """
        Args:
            parameters: The parameters that fit within this signature
        """
        self.__parameters = list()

        for index, parameter in enumerate(parameters):
            if isinstance(parameter, EventFunctionParameter):
                self.__parameters.append(parameter)
            elif isinstance(parameter, dict):
                parameter.update({"index": index})
                self.__parameters.append(EventFunctionParameter.from_basic_parameter(parameter))
            else:
                types = ', '.join([type(param) for param in parameters])
                raise TypeError(
                    f"Cannot register an event with the proposed signature with arguments ({types}). "
                    f"Only dictionaries and EventFunctionParameters are allowed"
                )

    @property
    def parameters(self) -> typing.Sequence[EventFunctionParameter]:
        """
        The parameters within this signature
        """
        return self.__parameters

    @property
    def has_args(self):
        return bool([
            parameter
            for parameter in self.__parameters
            if parameter.is_args
        ])

    @property
    def has_kwargs(self) -> bool:
        return bool([
            parameter
            for parameter in self.__parameters
            if parameter.is_kwargs
        ])

    @property
    def keywords(self) -> typing.Set[str]:
        return {
            parameter.name
            for parameter in self.__parameters
            if not parameter.positional_only
        }

    @property
    def required_keywords(self) -> typing.Set[str]:
        return {
            parameter.name
            for parameter in self.__parameters
            if not parameter.positional_only
                and parameter.required
        }

    @property
    def is_universal(self) -> bool:
        universal = False
        if len(self.__parameters) == 2:
            universal = self.__parameters[0].is_args and self.__parameters[1].is_kwargs

        return universal

    @property
    def required_variable_count(self) -> int:
        count = 0

        for parameter in self.__parameters:
            if parameter.required:
                count += 1
            else:
                break

        return count

    def complies_with(self, other: Signature) -> bool:
        """
        Determines if this signature is valid if its matching arguments comply with the other signature

        Given:
            >>> def f(a, b, c, d=9, *args, val=4, **kwargs)

        The following are compatible:
            >>> def g(a, b, *args, **kwargs)
            >>> def h(*args, **kwargs)
            >>> def i(a, b, c, d=9, val=4, *args, **kwargs)

        The following are NOT compatible:
            >>> def j(a, b, c, d, *args, val=4, **kwargs)
            >>> def k(a, b, c, d=9, val=4, **kwargs)
            >>> def l()
            >>> def m(a)
            >>> def n(a, b, **kwargs)

        - j is not compatible because `d` is required. Other may be called without `d` anywhere, ex (1, 2, 3)
        - k is not compatible because it does not support *args, ex (1, 2, 3, 4, 5, 6, val1=5, val2="f")
        - l is not compatible because it doesn't support required parameters. a call like (1, 2, 3, 4, 5, 6, val1=5, val2="f") will fail
        - m is not compatible because it does not support all required parameters. A call like (1, 2, 3) will fail
        - n is not compatible because it does not support all required parameters and does not support *args. A call like (1, 2, 3) will fail.

        Given:
            >>> def f(a, b, *args)

        The following are compatible:
            >>> def g(a, b, c=9, *args)
            >>> def h(a, b, *args, **kwargs)
            >>> def i(a, b, *args, c=9)
            >>> def j(a, b, *args, c=9, **kwargs)
            >>> def k(*args, **kwargs)
            >>> def l(a, *args, **kwargs)

        The following are NOT compatible:
            >>> def m(a, b, c, *args, **kwargs)
            >>> def n(a, b, **kwargs)

        - m is not valid because it requires `c` which is not required to come through
        - n is not compatible because it does not have *args. A call like (1, 2, 3, 4, 5, 6) will fail

        The function:
            >>> def f(*args, **kwargs)

        Only allows functions like:
            >>> def g(*args, **kwargs)

        If `other` is the universal (only has *args and **kwargs), this MUST be (*args, **kwargs).
        If this is (*args, **kwargs), `other` may be anything.

        Parameter types are not considered due to duck typing.
        Mismatched types should only be checked when the function is called.

        Args:
            other: The signature that THIS signature must comply with

        Returns:
            Whether this signature can handle all the possible arguments passed to the other's function
        """
        # False if anything may come through the other signature but not this signature
        if other.is_universal and not self.is_universal:
            return False

        # True if this can handle any possible argument
        if self.is_universal:
            return True

        # False if this has less required variables and doesn't have args
        if self.required_variable_count > other.required_variable_count and not self.has_args:
            return False

        # False if it is expected to allow *args but this doesn't
        if not self.has_args and other.has_args:
            return False

        # False if it is expected to allow **kwargs but this doesn't
        if not self.has_kwargs and other.has_kwargs:
            return False

        # False if this doesn't have all the required keywords and this doesn't kwargs
        if not self.keywords.issubset(other.required_keywords) and not self.has_kwargs:
            return False

        # Required variables may be subverted if *args or **kwargs are supported in both. If they aren't,
        # this signature only complies if it has the same number of required variables as the other
        if not (self.has_kwargs or other.has_kwargs or self.has_args or other.has_args):
            if self.required_variable_count != other.required_variable_count:
                return False

        return True

    def __hash__(self) -> int:
        return hash(tuple(self.__parameters))

    def __iter__(self):
        return iter(self.__parameters)

    def __str__(self):
        return f"({', '.join([str(parameter) for parameter in self])})"

    def __repr__(self):
        return str(self)


class EventFunction(EVENT_HANDLER):
    def __init__(self, function: EVENT_HANDLER, ignore_extra_parameters: bool = None, allow_errors: bool = None):
        self.__function = function
        parameters: Signature = Signature.from_function(function)

        if len(parameters) == 0:
            # The first parameter cannot be valid if there ISN'T a first parameter
            first_parameter_is_valid = False
        elif parameters[0].is_args:
            # If the first parameter is *args we know that an arbitrary amount of positional parameters are allowable,
            # meaning that sticking the event in has few if any side effects
            first_parameter_is_valid = True
        elif parameters[0].type is not None and (issubclass(parameters[0].type, Event) or isinstance(parameters[0].type, Event)):
            first_parameter_is_valid = True
        elif parameters[0].type is not None and not isinstance(parameters[0].type, str):
            # If a type could be found for the first parameter but it doesn't comply with event state, fail the check.
            # Failing to find the defined type will result in a description, so a string is fine
            first_parameter_is_valid = False
        elif parameters[0].type is None:
            # If no annotation is given at all, we'll just assume an event type can be inserted due to duck typing
            first_parameter_is_valid = True
        elif "event" in parameters[0].type.lower() or 'evt' in parameters[0].type.lower():
            # We go ahead and assume a type description containing something like '.*event.*' might describe
            # something like 'MouseEvent' or 'ClickEvent' or 'BasicEvent', etc.
            # We go ahead and cross our fingers and accept it.
            first_parameter_is_valid = True
        elif "event" in parameters[0].name.lower() or 'evt' in parameters[0].name.lower():
            # Not ideal, but allow this if absolutely no type is found but the name is like 'event'
            first_parameter_is_valid = True
        else:
            # Go ahead and state that the parameter isn't valid because it was given enough chances
            first_parameter_is_valid = False

        if not first_parameter_is_valid:
            raise TypeError(
                f"'{function.__name__}' is not a valid event handler - "
                f"the first parameter MUST be an Event State-like object"
            )

        self.__parameters = parameters
        self.__ignore_extra_parameters = bool(ignore_extra_parameters)
        self.__allow_errors = bool(allow_errors)
        self.__has_positional_only = False
        self.__has_keyword_only = False
        self.__has_kwargs = False
        self.__has_args = False
        self.__args_index: typing.Optional[int] = None
        self.__kwargs_index: typing.Optional[int] = None
        self.__positional_or_keyword_count = 0
        self.__positional_count = 0
        self.__keyword_count = 0
        self.__required_parameters: typing.List[EventFunctionParameter] = list()

        signature = inspect.signature(function)

        if signature.return_annotation is not signature.empty:
            self.__return_type: typing.Optional[str] = str(signature.return_annotation)
        else:
            self.__return_type: typing.Optional[str] = None

    @property
    def required_parameters(self) -> typing.Sequence[EventFunctionParameter]:
        return self.__required_parameters

    @property
    def is_async(self) -> bool:
        return inspect.iscoroutinefunction(self.__function)

    @property
    def parameters(self) -> Signature:
        return self.__parameters

    @property
    def parameter_hash(self) -> int:
        return hash(self.__parameters)

    def __call__(self, event: Event, *args, **kwargs) -> typing.Union[typing.Coroutine, typing.Any]:
        try:
            return self.__function(event, *args, **kwargs)
        except Exception as exception:
            if self.__allow_errors:
                logging.error(str(exception), exc_info=exception)
            else:
                raise

    @property
    def parameter_descriptions(self) -> typing.Sequence[str]:
        descriptions = list()

        if self.__has_positional_only:
            descriptions.extend([
                str(parameter)
                for parameter in self.__parameters
                if parameter.positional_only
            ])
            descriptions.append("/")

        descriptions.extend([
            str(parameter)
            for parameter in self.__parameters
            if parameter.can_use_positional_or_keyword
        ])

        if self.__has_keyword_only:
            descriptions.append("*")
            descriptions.extend([
                str(parameter)
                for parameter in self.__parameters
                if parameter.keyword_only
            ])

        return descriptions

    @property
    def kwargs_index(self) -> typing.Optional[int]:
        return self.__kwargs_index

    @property
    def args_index(self) -> typing.Optional[int]:
        return self.__args_index

    @property
    def has_args(self) -> bool:
        return self.args_index is not None

    @property
    def has_kwargs(self) -> bool:
        return self.kwargs_index is not None

    def __str__(self):
        return f"{self.__function.__name__}" \
               f"({', '.join(self.parameter_descriptions)})" \
               f"{' -> ' + self.__return_type if self.__return_type else ''}"

    def __repr__(self):
        return str(self)


class EventFunctionGroup:
    def __init__(
        self,
        expected_arguments: typing.Iterable[EventFunctionParameter],
        *functions: typing.Union[EventFunction, typing.Callable],
        ignore_extra_parameters: bool = None,
        allow_errors: bool = None
    ):
        self.__expected_arguments: Signature = Signature(expected_arguments)

        invalid_functions: typing.List[str] = list()

        self.__functions: typing.List[EventFunction] = list()

        for function in (functions or []):
            self.add_function(
                function,
                invalid_functions,
                ignore_extra_parameters,
                allow_errors
            )

        if invalid_functions:
            parameter_signatures = ', '.join([str(parameter) for parameter in expected_arguments])
            raise ValueError(
                f"Attempted to create an invalid function group. The desired signature is ({parameter_signatures}), "
                f"but instead received the following non-conforming functions: {', '.join(invalid_functions)}"
            )

    def add_function(
        self,
        function: typing.Union[EventFunction, typing.Callable],
        invalid_functions: typing.List[str],
        ignore_extra_parameters: bool = None,
        allow_errors: bool = None
    ):
        if not isinstance(function, EventFunction):
            function = EventFunction(function, ignore_extra_parameters, allow_errors)

        if self.signature_matches(function):
            self.__functions.append(function)
        else:
            invalid_functions.append(str(function))

    def signature_matches(
        self,
        function: typing.Union[EventFunction, typing.Callable],
        ignore_extra_parameters: bool = None,
        allow_errors: bool = None
    ) -> bool:
        if not isinstance(function, EventFunction):
            function = EventFunction(function, ignore_extra_parameters, allow_errors)

        return function.parameters.complies_with(self.__expected_arguments)

    async def fire(self, event: Event, *args, **kwargs):
        scheduled_async_functions: asyncio.Future = asyncio.gather(*[
            function(event, *args, **kwargs)
            for function in self.__functions
            if function.is_async
        ])

        exceptions: typing.List[BaseException] = list()

        synchronous_functions: typing.List[EVENT_HANDLER] = [
            func
            for func in self.__functions
            if not func.is_async
        ]

        for function in synchronous_functions:
            function(event, *args, **kwargs)

        results = list(await scheduled_async_functions)

        # Loop through all results in a while loop rather than a for-loop
        #   awaited results will be placed back into the collection for iteration
        while results:
            result = results.pop()
            if isinstance(result, BaseException):
                exceptions.append(result)
            elif inspect.isawaitable(result):
                results.append(await result)

        if exceptions:
            raise Exception(exceptions)

    def __call__(self, event: Event, *args, **kwargs) -> typing.List[typing.Coroutine]:
        coroutines: typing.List[typing.Coroutine] = list()

        for function in self.__functions:
            result = function(event, *args, **kwargs)

            if inspect.isawaitable(result):
                coroutines.append(result)

        return coroutines


