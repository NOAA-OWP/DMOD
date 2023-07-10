import asyncio
from functools import partial
from typing import Optional, Protocol, Union


class Reader(Protocol):
    """Reader interface type.

    Example:
    ```
    def upload(data: Reader) -> None:
        ...

    with open("some_file.txt", "rb") as fp:
        upload(fp)
    ```
    """

    def read(self, size: Union[int, None] = ...) -> bytes:
        ...


class AsyncReader(Protocol):
    """
    Async Reader interface type.
    """

    async def read(self, size: Union[int, None] = ...) -> bytes:
        ...


class AsyncReadWrapper:
    """
    Wrapper object for treating a sync reader as an async reader.
    """

    def __init__(self, reader: Reader) -> None:
        self._reader = reader
        self._loop = asyncio.get_running_loop()

    async def read(self, size: Optional[int] = None) -> bytes:
        fn = partial(self._reader.read, size)
        return await self._loop.run_in_executor(None, fn)
