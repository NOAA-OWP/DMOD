import typing
import re
import string

from multiprocessing import Lock


INVALID_CHARACTER_PATTERN = re.compile(r"[^\w_]")


class HandlerState:
    """
    Provides thread safe, generic state management
    """
    def __init__(self, **kwargs):
        self._state_lock = Lock()
        self.__internal_state: typing.Dict[str, typing.Any] = dict()

        for key, value in kwargs.items():
            self.__assign_value(key, value)

    def get(self, key: str, default: typing.Any = None):
        with self._state_lock:
            return self.__internal_state.get(key, default)

    def __getitem__(self, key: str):
        with self._state_lock:
            return self.__internal_state[key]

    def __setitem__(self, key: str, value: typing.Any):
        self.__assign_value(key, value)

    def __assign_value(self, key: str, value: typing.Any):
        """
        Adds the value to the internal state AND adds it so that values may be accessed like `state.key`

        Args:
            key: The key to the value to add or update
            value:

        Returns:

        """
        with self._state_lock:
            if not key or not isinstance(key, str) or INVALID_CHARACTER_PATTERN.search(key) or key[0] in string.digits:
                raise ValueError(f"'{key}' is not a valid state key")

            setattr(self, key, value)
            self.__internal_state[key] = value

    def __contains__(self, item: str):
        with self._state_lock:
            return item in self.__internal_state

    def __iter__(self):
        with self._state_lock:
            return iter([(key, value) for key, value in self.__internal_state.items()])

    def __len__(self):
        with self._state_lock:
            return len(self.__internal_state)

    def __delitem__(self, key):
        with self._state_lock:
            if key in self.__internal_state:
                del self.__internal_state[key]
            if hasattr(self, key):
                delattr(self, key)

