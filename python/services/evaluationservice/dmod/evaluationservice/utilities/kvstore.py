"""
Utility functions and structures used to make it easier to work with a key value store
"""
from __future__ import annotations

import typing
import dataclasses

import redis

from service import application_values


@dataclasses.dataclass
class KVStoreArguments:
    """
    A DTO for the common arguments used to connect to a key value store
    """
    host: typing.Optional[str] = dataclasses.field(default=application_values.REDIS_HOST)
    port: typing.Optional[typing.Union[int, str]] = dataclasses.field(default=application_values.REDIS_PORT)
    username: typing.Optional[str] = dataclasses.field(default=application_values.REDIS_USERNAME)
    password: typing.Optional[str] = dataclasses.field(default=application_values.REDIS_PASSWORD)
    db: typing.Optional[int] = dataclasses.field(default=application_values.REDIS_DB)

    def get_connection(self) -> redis.Redis:
        """
        Connect to a key value store

        Returns:
            A connection to key value store
        """
        return get_kvstore_connection(self.host, self.port, self.username, self.password, self.db)

    def __str__(self):
        return f"{self.username}@{self.host}:{self.port}/{self.db}"

    def __repr__(self):
        return self.__str__()


def get_kvstore_connection(
    host: str = None,
    port: int = None,
    username: str = None,
    password: str = None,
    db: int = None
) -> redis.Redis:
    """
    Forms a connection to a redis instance. If fields are not supplied, values fall back to environment configuration

    Args:
        host: The optional host to connect to
        port: The optional port to connect to
        username: The optional username to connect to
        password: The optional password to use when connecting to the instance
        db: The optional database to connect to

    Returns:
        A connection to a redis instance
    """
    return redis.Redis(
        host=host,
        port=port,
        username=username,
        password=password,
        db=db,
    )


def get_runner_connection(
    host: str = None,
    port: int = None,
    db: str = None,
    password: str = None,
    username: str = None
) -> redis.Redis:
    """
    Forms a connection to a Key Value Store instance to the runner. If fields are not supplied,
    values fall back to environment configuration

    Args:
        host: The optional host to connect to
        port: The optional port to connect to
        username: The optional username to connect to
        password: The optional password to use when connecting to the instance
        db: The optional database to connect to

    Returns:
        A connection to a Key Value store used by the runner
    """
    return redis.Redis(
        host=host or application_values.RUNNER_HOST,
        port=port or application_values.RUNNER_PORT,
        username=username or application_values.RUNNER_USERNAME,
        password=password or application_values.RUNNER_PASSWORD,
        db=db or application_values.RUNNER_DB,
    )