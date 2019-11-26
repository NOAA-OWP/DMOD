#!/usr/bin/env python3

"""
communication integration tests.
"""
import asyncio
import json
import logging
import pathlib
import ssl
import websockets
from socket import gethostname

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)

# TODO make these real tests, for now, hacky thing to try output

# For testing, set up client ssl context
current_dir = pathlib.Path(__file__).resolve().parent


client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
localhost_pem = current_dir.parent.joinpath('ssl', 'certificate.pem')
host_name = gethostname()
# localhost_pem = Path(__file__).resolve().parents[1].joinpath('macbook_ssl', "certificate.pem")
# host_name = 'localhost'
client_ssl_context.load_verify_locations(localhost_pem)
server_test = 0
client_test = 0
port = 3013

async def connection_test(ssl_context=None):
    """
        Function to emulate connection
    """
    if ssl_context:
        uri = 'wss://{}:{}'.format(host_name, port)
    else:
        uri = 'ws://localhost:{}'.format(port)
    try:
            async with websockets.connect(uri, ssl=ssl_context) as websocket:
                logging.debug("Sending data")

                await websocket.send( json.dumps({"user":"test"}) )
                logging.debug("Data sent")
                response = await websocket.recv()
                logging.debug("Data Rec")
                logging.debug(response)
    except websockets.exceptions.ConnectionClosed:
        logging.info("Connection Closed at Publisher")
    except Exception as e:
        logging.error("FS {}".format(e))
        raise(e)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(connection_test(client_ssl_context))
