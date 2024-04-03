from typing_extensions import Protocol, runtime_checkable
from os import SEEK_SET


@runtime_checkable
class Reader(Protocol):
    def read(self, size: int = -1, /) -> bytes:
        """EOF if empty b''."""


@runtime_checkable
class Seeker(Protocol):
    def seek(self, offset: int, whence: int = SEEK_SET) -> int:
        """ Change the position to the given offset, returning the absolute position. """


class ReadSeeker(Reader, Seeker):
    """
    A :class:`Reader` capable of changing the position from which it is reading.
    """
