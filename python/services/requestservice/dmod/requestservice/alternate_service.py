#!/usr/bin/env python3
import typing
import secrets
import asyncio
import random

from argparse import ArgumentParser

import websockets

from websockets.server import WebSocketServerProtocol


import dmod.communication as communication


class Arguments(object):
    def __init__(self, *args):
        self.__port: typing.Optional[int] = None

        self.__parse_command_line(*args)

    @property
    def port(self) -> int:
        """
        The ports to communicate with

        :return: All local ports to talk with
        """
        return self.__port

    def __parse_command_line(self, *args):
        parser = ArgumentParser("Launch the example handler")

        # Add options
        parser.add_argument(
            "port",
            type=str,
            help="The port to serve"
        )

        # Parse the list of args if one is passed instead of args passed to the script
        if args:
            parameters = parser.parse_args(args)
        else:
            parameters = parser.parse_args()

        # Assign parsed parameters to member variables
        self.__port = int(float(parameters.port))


class AlternateRequestService(communication.DecoratedWebSocketInterface):
    """
    An example interface used to demonstrate how to create a handler for a decorated interface
    """

    @classmethod
    def get_parseable_request_types(cls) -> typing.List[typing.Type[communication.AbstractInitRequest]]:
        return [

        ]

    @communication.consumer
    async def echo(self, websocket: WebSocketServerProtocol, path=None):
        if isinstance(websocket, str):
            return
        async for message in websocket:
            print(message)

    @communication.producer
    async def emit_message(self, websocket: WebSocketServerProtocol, path=None):
        if isinstance(websocket, str):
            return
        minimum_wait_seconds = 2
        maximum_wait_seconds = 10

        try:
            while True:
                wait_seconds = random.randint(minimum_wait_seconds, maximum_wait_seconds)
                await asyncio.sleep(wait_seconds)

                message = f"The secret code is: {secrets.token_urlsafe(8)}"
                await websocket.send(message)
        except websockets.ConnectionClosed as connection_closed:
            print(f"The connection has been closed; {str(connection_closed)}")


def main():
    """
    Define your initial application code here
    """
    arguments = Arguments()
    example_handler = AlternateRequestService(port=arguments.port, use_ssl=False)
    example_handler.run()


# Run the following if the script was run directly
if __name__ == "__main__":
    main()
