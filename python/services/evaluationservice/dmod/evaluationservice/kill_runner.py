#!/usr/bin/env python3
import typing
import json

from argparse import ArgumentParser

import service
import utilities


class Arguments(object):
    def __init__(self, *args):
        self.__host: typing.Optional[str] = None
        self.__port: typing.Optional[str] = None
        self.__username: typing.Optional[str] = None
        self.__password: typing.Optional[str] = None
        self.__channel: typing.Optional[str] = None
        self.__db: int = 0
        self.__parse_command_line(*args)

    @property
    def host(self) -> typing.Optional[str]:
        return self.__host

    @property
    def port(self) -> typing.Optional[int]:
        return self.__port

    @property
    def username(self) -> typing.Optional[str]:
        return self.__username

    @property
    def password(self) -> typing.Optional[str]:
        return self.__password

    @property
    def db(self) -> int:
        return self.__db

    @property
    def channel(self) -> typing.Optional[str]:
        return self.__channel

    def __parse_command_line(self, *args):
        parser = ArgumentParser("Kills all evaluation runners for a given channel")

        # Add options

        parser.add_argument(
            '--redis-host',
            help='Set the host value for making Redis connections',
            dest='redis_host',
            default=None
        )

        parser.add_argument(
            '--redis-port',
            help='Set the port value for making Redis connections',
            dest='redis_port',
            default=None
        )

        parser.add_argument(
            '--redis-username',
            help='Set the username for making Redis connections',
            dest='redis_username',
            default=None
        )

        parser.add_argument(
            '--redis-pass',
            help='Set the password value for making Redis connections',
            dest='redis_pass',
            default=None
        )

        parser.add_argument(
            '--redis-db',
            help='Set the database value for making Redis connections',
            dest='redis_db',
            default=None
        )

        parser.add_argument(
            "--channel",
            help="The name of the channel to kill",
            dest="channel"
        )

        # Parse the list of args if one is passed instead of args passed to the script
        if args:
            parameters = parser.parse_args(args)
        else:
            parameters = parser.parse_args()

        # Assign parsed parameters to member variables
        self.__host = parameters.redis_host or service.RUNNER_HOST
        self.__port = parameters.redis_port or service.RUNNER_PORT
        self.__username = parameters.redis_username or service.RUNNER_USERNAME
        self.__password = parameters.redis_pass or service.RUNNER_PASSWORD
        self.__channel = parameters.channel or service.EVALUATION_QUEUE_NAME
        self.__db = parameters.db or service.REDIS_DB


def main():
    """
    Define your initial application code here
    """
    arguments = Arguments()
    connection_parameters = {
        "host": arguments.host,
        "port": arguments.port,
        "username": arguments.username,
        "password": arguments.password,
        "db": arguments.db,
    }
    with utilities.get_redis_connection(**connection_parameters) as connection:
        payload = {
            "purpose": "close"
        }
        connection.publish(arguments.channel, json.dumps(payload))


# Run the following if the script was run directly
if __name__ == "__main__":
    main()
