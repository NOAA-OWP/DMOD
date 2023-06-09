from typing import Protocol, Union


class Reader(Protocol):
    def read(self, size: Union[int, None] = ...) -> bytes:
        ...
