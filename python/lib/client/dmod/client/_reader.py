from typing import Protocol, Union


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
