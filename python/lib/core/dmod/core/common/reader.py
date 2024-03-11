from typing_extensions import Protocol, runtime_checkable


@runtime_checkable
class Reader(Protocol):
    def read(self, size: int = -1, /) -> bytes:
        """EOF if empty b''."""
