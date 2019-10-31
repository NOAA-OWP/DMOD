#!/usr/bin/env python3

"""
This script is the entry point for the request hanlder service
This script will:
    Parse and validate a user request
    Signal the scheduler to allocate and create the correct model service
        Signal via redis stream (publish): req_id -> req_meta
    Wait for responses to communicate back to user
    Should be threaded with async hanlders

"""
import asyncio
import websockets
import ssl
import pathlib
import json
import signal
import logging

from validator import validate_request
from jsonschema.exceptions import ValidationError

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)

class RequestHandler(object):
    """
    Request Handling class to manage async requests

    Attributes
    ----------
    loop: aysncio event loop

    signals: list-like
        List of signals (from the signal package) this handler will use to shutdown

    ssl_context:
        ssl context for websocket

    server:
        websocket server
    """

    def __init__(self, hostname='', port='3012'):
        """
            Parameters
            ----------
            hostname: str
                Hostname of the websocket server

            port: str
                port for the handler to listen on
        """

        #Async event loop
        self.loop = asyncio.get_event_loop()
        #register signals for tasks to respond to
        self.signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in self.signals:
            #Create a set of shutdown tasks, one for each signal type
            self.loop.add_signal_handler( s, lambda s=s: self.loop.create_task(self.shutdown(signal=s)))

        #add a default excpetion handler to the event loop
        self.loop.set_exception_handler(self.handle_exception)

        #Set up server/listener ssl context
        self.ssl_context = ssl.SSLContext( ssl.PROTOCOL_TLS_SERVER )
        #TODO parameterize cert and key
        localhost_pem = pathlib.Path(__file__).parent.joinpath('ssl', "certificate.pem")
        localhost_key = pathlib.Path(__file__).parent.joinpath('ssl', "privkey.pem")
        #localhost_pem = pathlib.Path(__file__).resolve().parents[1].joinpath('macbook_ssl', "certificate.pem")
        #localhost_key = pathlib.Path(__file__).resolve().parents[1].joinpath('macbook_ssl', "privkey.pem")

        self.ssl_context.load_cert_chain(localhost_pem, keyfile=localhost_key)
        print(hostname)
        #Setup websocket server
        self.server = websockets.serve(self.listener, hostname, port, ssl=self.ssl_context)

    def handle_exception(loop, context):
        message = context.get('exception', context['message'])
        logging.error(f"Caught exception: {message}")
        logging.info("Shutting down due to exception")
        asyncio.create_task(shutdown())

    async def parse(self, message):
        """
        Validate request message and push to redis
        """
        #TODO validate and push to redis stream
        data = json.loads( message )
        logging.info(f"Got payload: {data}")
        validate_request(data)
        ret = 42 + data['client_id']
        return ret

    async def listener(self, websocket, path):
        """
            Async function listening for incoming information on websocket
        """
        #TODO convert all prints to logging, enable logging
        #FIXME remove this!!!
        try:
            while True:
                 logging.debug("listener is waiting for data")
                 message = await websocket.recv()
                 logging.debug("listener is wating to parse")
                 request_id = await self.parse(message)
                 logging.debug("listener is waiting to return")
                 await websocket.send(str(request_id))

        except websockets.exceptions.ConnectionClosed:
                logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
                logging.info("Cancelling listerner task")
        except ValidationError as e:
                await websocket.send(str(e))

    async def shutdown(self, signal=None):
         """
            Wait for current task to finish, cancel all others
         """
         if signal:
             logging.info(f"Exiting on signal {signal.name}")

         #Let the current task finish gracefully
         #3.7 asyncio.all_tasks()
         tasks = [task for task in asyncio.Task.all_tasks() if task is not asyncio.current_task() ]
         for task in tasks:
             #Cancel pending tasks
             task.cancel()
         logging.info(f"Cancelling {len(tasks)} pending tasks")
         #wait for tasks to cancel
         await asyncio.gather(*tasks, return_exceptions=True)
         self.loop.stop()

    def run(self):
        """
            Run the request handler indefinitely
        """
        try:
            #Establish the websocket
            self.loop.run_until_complete(self.server)
            #Run server forever
            self.loop.run_forever( )
        finally:
            self.loop.close()
            logging.info("Request Handler Finished")


if __name__ == '__main__':
    handler = RequestHandler()
    handler.run()
