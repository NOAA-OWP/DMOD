#!/usr/bin/env python3
import typing

from ..message import AbstractInitRequest


VARIABLE_CALLABLE = typing.Callable[[typing.Tuple, typing.Dict[str, typing.Any]], typing.NoReturn]

MESSAGE_TYPES = typing.Set[typing.Type[AbstractInitRequest]]
