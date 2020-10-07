import argparse
from . import name as package_name
from . import MonitorService
from pathlib import Path
from os import getenv
from dmod.monitor import RedisDockerSwarmMonitor


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.prog = package_name
    return parser.parse_args()


def _sanity_check_path_arg(path_as_str, is_directory=False):
    path_value = Path(path_as_str)
    if not path_value.exists():
        return False
    if is_directory and not path_value.is_dir():
        return False
    if not is_directory and not path_value.is_file():
        return False
    return True


def _get_parsed_or_env_val(parsed_val, env_var_suffix, fallback):
    """
    Return either a passed parsed value, if it is not ``None``, the value from one of several environmental variables
    with a standard beginning to their name, if one is found with a non-``None`` value, or a given fallback value.

    When proceeding to check environment variables, the following variables are checked in the following order, with the
    first existing and non-``None`` value returned:

        - DOCKER_SECRET_REDIS_<SUFFIX>
        - REDIS_<SUFFIX>
        - DOCKER_REDIS_<SUFFIX>

    The actual names have ``<SUFFIX>`` replaced with the provided suffix parameter.

    Finally, the fallback value is returned when necessary.

    Parameters
    ----------
    parsed_val
    env_var_suffix
    fallback

    Returns
    -------
    The appropriate value, given the params and the existing environment variables.
    """
    if parsed_val is not None:
        return parsed_val
    env_prefixes = ['REDIS_', 'DOCKER_SECRET_REDIS_', 'DOCKER_REDIS_']
    for prefix in env_prefixes:
        env_var = prefix + env_var_suffix
        if getenv(env_var, None) is not None:
            return getenv(env_var)
    return fallback


def redis_params(parsed_args) -> tuple:
    """
    Return the Redis host, port, and password for connections, obtained from the parsed arguments and/or environment.

    Parameters
    ----------
    parsed_args

    Returns
    -------
    tuple
        The Redis host, port, and password for connections.
    """
    host = _get_parsed_or_env_val(parsed_args.redis_host, 'HOST', 'localhost')
    port = _get_parsed_or_env_val(parsed_args.redis_port, 'PORT', 6379)
    passwd = _get_parsed_or_env_val(parsed_args.redis_pass, 'PASS', '')
    return host, port, passwd


def main():
    args = _handle_args()

    # Obtain Redis params
    redis_host, redis_port, redis_pass = redis_params(args)

    # Sanity check any provided path arguments

    # Create a Monitor object
    # TODO: need to figure out if this can/should be parameterized, while also staying in sync with global value.
    resource_pool = "maas"
    # TODO: for now, just use this type, though look at making configureable or parameterized somehow
    monitor = RedisDockerSwarmMonitor(resource_pool=resource_pool, redis_host=redis_host, redis_port=redis_port,
                                      redis_pass=redis_pass)

    # Init monitor service
    handler = MonitorService(monitor=monitor)

    # Create the additional async task for running the actual monitoring logic
    handler.add_async_task(handler.exec_monitoring())

    handler.run()


if __name__ == '__main__':
    main()
