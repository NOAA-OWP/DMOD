#!/usr/bin/env python3

"""
Request Handler unit tests
"""
import unittest
import asyncio
import websockets
import logging
import ssl
import pathlib
import json
from socket import gethostname

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
#TODO make these real tests, for now, hacky thing to try output


#For testing, set up client ssl context
client_ssl_context = ssl.SSLContext( ssl.PROTOCOL_TLS_CLIENT )
localhost_pem = pathlib.Path(__file__).parent.joinpath('ssl', "certificate.pem")
host_name = 'request-test'
#localhost_pem = pathlib.Path(__file__).resolve().parents[1].joinpath('macbook_ssl', "certificate.pem")
#hostname = 'localhost'
client_ssl_context.load_verify_locations(localhost_pem)
server_test = 0
client_test = 0

async def data_test(ssl_context=None):
    """
        Function to emulate incoming data
    """

    with open("./schemas/request.json", "r") as test_file:
        test_data = json.load(test_file)
    test_request = {
         'model':'nwm-2.0',
         'domain':'test-domain',
         'cores':20,
         'user':'test-user'
         }
    test_request = test_data
    #print("Testing")
    if ssl_context:
        uri = 'wss://{}:3012'.format(host_name)
    else:
        uri = 'ws://localhost:3012'
    try:

        for i in range(10):
            async with websockets.connect(uri, ssl=ssl_context) as websocket:
                client_test = i
                logging.info("Sending data")
                test_request['client_id'] = i
                await websocket.send( json.dumps(test_request) )
                logging.info("Data sent")
                response = await websocket.recv()
                logging.info("Producer got response: {}, expected {}".format(response, client_test))
                assert( int(response) == 42 + client_test)

    except websockets.exceptions.ConnectionClosed:
        logging.info("Connection Closed at Publisher")
    except Exception as e:
        logging.error("FS {}".format(e))
        raise(e)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(data_test(client_ssl_context))
