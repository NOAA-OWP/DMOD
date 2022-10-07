from abc import ABC, abstractmethod
from .message import AbstractInitRequest, Response


class AbstractRequestHandler(ABC):

    @abstractmethod
    async def handle_request(self, request: AbstractInitRequest, **kwargs) -> Response:
        """
        Handle the given request message as is appropriate for the implementation, and return the resulting ``Response``
        of the appropriate type.

        Parameters
        ----------
        request: AbstractInitRequest
            A ``AbstractInitRequest`` message instance to be handled

        kwargs:
            A ``dict`` of other arguments appropriate for the particular implementation

        Returns
        -------
        response: Response
            An appropriate ``Response`` object.
        """
        pass
