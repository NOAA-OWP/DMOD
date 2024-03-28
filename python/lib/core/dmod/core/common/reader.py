from typing_extensions import Protocol, runtime_checkable


@runtime_checkable
class Reader(Protocol):
    def read(self, size: int = -1, /) -> bytes:
        """EOF if empty b''."""


class RepeatableReader(Reader):
    """
    Extension of ::class:`Reader` that provides a reset mechanism that allows its data can be read multiple times.
    """

    def reset(self):
        """ Reset such that ::method:`read` returns to the start of the data this instance reads. """
