import sys
import types
from dataclasses import dataclass
from functools import wraps
from typing import TypeVar, Generic, NoReturn, Literal, Union, Callable
from typing_extensions import TypeAlias, ParamSpec

T = TypeVar("T", covariant=True)
E = TypeVar("E", covariant=True, bound=BaseException)
U = TypeVar("U")


def try_attach_traceback_to_exception(exception: E, depth: int = 0) -> bool:
    # inspiration from https://stackoverflow.com/a/54653137
    # depth of 1 means to start from the caller's frame

    # > CPython implementation detail: This function should be used for internal and specialized
    # > purposes only. It is not guaranteed to exist in all implementations of Python.
    # https://docs.python.org/3.7/library/sys.html#sys._getframe
    frame = sys._getframe(depth) if hasattr(sys, "_getframe") else None
    if frame is None:
        return False

    tb = types.TracebackType(None, frame, frame.f_lasti, frame.f_lineno)
    exception.with_traceback(tb)
    return True


@dataclass
class Ok(Generic[T]):
    value: T

    def is_ok(self) -> Literal[True]:
        return True

    def is_err(self) -> Literal[False]:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: U) -> T:
        return self.value

    def unwrap_or_else(self, fn: Callable[[E], T]) -> T:
        return self.value


@dataclass
class Err(Generic[E]):
    value: E

    def __post_init__(self):
        if self.value.__traceback__ is None:
            # start from stack depth 3 so trace starts from call to initialize Error:
            # 0: try_attach_traceback_to_exception
            # 1: __post_init__
            # 2: __init__ (implicit b.c. dataclass)
            # 3: caller that created Error
            # if successful, this mutates self.value.__traceback__
            try_attach_traceback_to_exception(self.value, depth=3)

    def is_ok(self) -> Literal[False]:
        return False

    def is_err(self) -> Literal[True]:
        return True

    def unwrap(self) -> NoReturn:
        raise ValueError("Called `Result.unwrap()` on an `Err` value") from self.value

    def unwrap_or(self, default: U) -> U:
        return default

    def unwrap_or_else(self, fn: Callable[[E], T]) -> T:
        return fn(self.value)


Result: TypeAlias = Union[Ok[T], Err[E]]

ReturnType = TypeVar("ReturnType")
Parms = ParamSpec("Parms")


def as_result(
    fn: Callable[Parms, ReturnType]
) -> Callable[Parms, Result[ReturnType, Exception]]:
    @wraps(fn)
    def inner(
        *args: Parms.args, **kwargs: Parms.kwargs
    ) -> Result[ReturnType, Exception]:
        try:
            res = fn(*args, **kwargs)
            if isinstance(res, Err):
                return res
            return Ok(res)
        except Exception as e:
            return Err(e)

    return inner
