"""
Provides an easy interface for retrieving redis connections without the
need for indepth knowledge of how to use redis
"""
import typing

import redis

from maas_experiment import application_values


def get_redis_connection(
    host: str = None,
    port: int = None,
    db: str = None,
    password: str = None,
    username: str = None,
    **kwargs
) -> redis.Redis:
    """
    Forms a connection to a redis instance. If fields are not supplied, values fall back to environment configuration

    Args:
        host: The optional host to connect to
        port: The optional port to connect to
        db: The optional redis db to connect to
        password: The optional password to use when connecting to the instance
        username: The optional username to use when connecting
        **kwargs:

    Returns:
        A connection to a redis instance
    """
    construction_arguments = {
        "host": host or application_values.REDIS_HOST,
        "port": port or application_values.REDIS_PORT,
        **kwargs
    }

    if password or application_values.REDIS_PASSWORD:
        construction_arguments["password"] = password or application_values.REDIS_PASSWORD

    if db or application_values.REDIS_DB:
        construction_arguments['db'] = db or application_values.REDIS_DB

    if username or application_values.REDIS_USERNAME:
        construction_arguments['username'] = username or application_values.REDIS_USERNAME

    try:
        return redis.Redis(**construction_arguments)
    except Exception as e:
        failing_address = construction_arguments['host']

        if construction_arguments['port']:
            failing_address += f":{construction_arguments['port']}"

        if "username" in construction_arguments:
            failing_address = f"{construction_arguments['username']}@{failing_address}"

        raise Exception(
            f"Could not connect to redis instance at {failing_address}. "
            f"Make sure it is running and ready to receive connections."
        ) from e
