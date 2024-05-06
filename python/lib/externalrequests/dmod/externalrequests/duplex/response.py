"""
Provides a generic response for responses from duplex operations
"""
import typing
import json

import collections.abc as abstract_collections

from datetime import datetime

from dmod.core import common

from dmod.communication import Response
from dmod.communication import InitRequestResponseReason


DATETIME_FORMAT = "%Y-%m-%d %I:%M %p %Z"


class ResponseData(typing.MutableMapping):
    """
    Basic data that should be expected to return with any Duplex response
    """

    def __setitem__(self, key: str, value: typing.Any) -> None:
        self.results[key] = value

    def __delitem__(self, key: str) -> None:
        del self.results[key]

    def __getitem__(self, key: str) -> typing.Any:
        return self.results[key]

    def __len__(self) -> int:
        return len(self.results)

    def __iter__(self) -> typing.Iterator[str]:
        return self.results.__iter__()

    def __iadd__(self, count):
        self.message_count += 1
        return self

    def add(self, author: str, value: typing.Any):
        # If `result` is the first value in for `handler_name` in the response data, we can go ahead and add the value
        # with no worries
        if value is not None and author not in self.results:
            self.results[author] = value
        elif value is not None and common.is_sequence_type(self.results[author]):
            # If the value for handler data is some sort of list or set, we need to add the new value to that list
            # We create a new list by iterating rather than by calling `add` or `append` because we can't be sure what
            # type of collection either item is
            combined_collection = [value for value in self.results[author]]
            combined_collection.append(value)
            self.results[author] = combined_collection
        elif value is not None and isinstance(value, dict):
            if isinstance(self.results[author], dict):
                merged_dictionary = common.merge_dictionaries(self.results[author], value)
                self.results[author] = merged_dictionary
            else:
                self.results[author] = [self.results[author], value]
        elif value is not None and self.results[author] is not None:
            self.results[author] = [self.results[author], value]

        self.update_latest(author)

    @property
    def items(self) -> abstract_collections.ItemsView:
        """
        The items in the results mapping
        """
        return self.results.items()

    def get(self, key: str, default: typing.Any = None):
        """
        The value mapped to the key in the results

        Args:
            key: The key for the value to look up
            default: A value to return if the key is not present

        Returns:
            The value of the key if it is present, the default value otherwise
        """
        return self.results.get(key, default)

    def __init__(self):
        self.__error: typing.Optional[str] = None
        """
        A recorded error that occurred over the course of operations
        """

        self.results: typing.Dict[str, typing.Any] = dict()
        """
        Results from an operation to return
        """

        self.last_update: typing.Optional[datetime] = None
        """
        The last time this data was updated
        """

        self.last_handler: typing.Optional[str] = None
        """
        The name of the last handler to update this
        """

        self.started_at: str = datetime.now().astimezone().strftime(DATETIME_FORMAT)
        """
        When operations began
        """

        self.message_count: int = 0
        """
        The number of messages that arrived to prompt operations
        """

        self.closed_at: typing.Optional[datetime] = None
        """
        When the connection closed (if it has)
        """

    def increase_message_count(self, count: int = None):
        """
        Increase the number of messages within the results

        Args:
            count: The amount of messages to increment by. Defaults to 1
        """
        if count is None:
            count = 1
        elif count < 0:
            raise ValueError("A negative value would decrease the message count, but only increasing is allowed.")

        self.message_count += count

    def update_latest(self, author: str):
        """
        Update what last edited this and when

        Args:
            author: The entity that last updated this response data
        """
        self.last_update = datetime.now().astimezone()
        self.last_handler = author

    @property
    def error(self):
        """
        An error that occurred within this set of results
        """
        return self.__error

    @error.setter
    def error(self, error_value: typing.Union[str, BaseException]):
        self.__error = str(error_value)

    def to_dict(self):
        """
        Convert the response data into a dictionary
        """
        return {
            "error": self.error,
            "results": self.results,
            "last_update": self.last_update.strftime(DATETIME_FORMAT) if self.last_update else None,
            "last_handler": self.last_handler,
            "started_at": self.started_at,
            "message_count": self.message_count,
            "closed_at": self.closed_at.strftime(DATETIME_FORMAT) if self.closed_at else None
        }

    def close(self):
        """
        Report that the connection that this is storing data for has closed
        """
        self.closed_at = datetime.now().astimezone()

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)

    def __repr__(self):
        data = {
            "error": self.error is not None,
            "result_count": len(self.results),
            "last_update": self.last_update.strftime(DATETIME_FORMAT) if self.last_update else None,
            "last_handler": self.last_handler,
            "started_at": self.started_at,
            "message_count": self.message_count,
            "closed_at": self.closed_at.strftime(DATETIME_FORMAT) if self.closed_at else None
        }
        return json.dumps(data, indent=4)


class DuplexResponse(Response):
    """
    A general response showing the result of all tasks run within the ConsumerProducerRequestHandler
    """
    def __init__(
        self,
        success: bool,
        data: typing.Union[dict, ResponseData],
        reason: InitRequestResponseReason = None,
        message: str = None,
        *args,
        **kwargs
    ):
        """
        Constructor

        Args:
            success: Whether the operation was a success
            data: Data to be returned
            reason: A reason for the response
            message: A message to accompany the response for human interpretation
            *args:
            **kwargs:
        """
        if isinstance(reason, InitRequestResponseReason):
            reason = reason.name
        elif reason is not None:
            reason = str(reason)
        else:
            reason = InitRequestResponseReason.UNKNOWN.name

        if isinstance(data, ResponseData):
            data = data.to_dict()

        super().__init__(
            success=success,
            data=data,
            reason=reason,
            message=message,
            *args,
            **kwargs
        )