#!/usr/bin/env python3
#TOTAL HACK to import sibling package code
#import os,sys,inspect
#current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
#parent_dir = os.path.dirname(current_dir)
#sys.path.insert(0, parent_dir)
#END PATH HACK

from websockets import WebSocketServerProtocol
from nwmaas.communication import WebSocketInterface, SchedulerRequestMessage, SchedulerRequestResponse
from nwmaas.scheduler import Scheduler
from pathlib import Path
import json
import logging
import asyncio
import websockets

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler()]
)


class SchedulerHandler(WebSocketInterface):
    """
    Communication handler for the Scheduler Service, implemented with WebSocketInterface

    Attributes
    ----------

    scheduler:
        scheduler instance to schedule requested jobs
    """

    def __init__(self, scheduler, *args, **kwargs):
        """
            Initialize the WebSocketInterface with any user defined custom server config
        """
        super().__init__(*args, **kwargs)
        #Hold the defined scheduler instance
        self.scheduler = scheduler

    async def listener(self, websocket: WebSocketServerProtocol, path):
        """
            Listen for job requests, valid requests are scheduled by scheduler
            and <FIXME> is sent back to requester.
        """
        print("Scheduler Listener")

        try:
            # TODO: think about, if this was in an async loop, whether that makes sense, and exactly what it would be doing
            message = await websocket.recv()
            #TODO here we should handle already running jobs, as well as any cached
            #Do this by associating metadata in the request message with existing
            #metadata tracked by scheduler
            logging.info(f"Gor message: {message}")
            data = json.loads(message)
            logging.info(f"Got payload: {data}")
            request_message = SchedulerRequestMessage.factory_init_from_deserialized_json(data)
            test = self.scheduler.fromRequest(request_message, 0)
            #FIX THIS INTERFACE test.startJobs()
            #FIXME one of the first scheduler interface changes will be a domain
            #identity which services will have to mount to run
            #initial cpu/mem will be static, bound to domain ID

            # Initial response ...
            response = SchedulerRequestResponse(success=True, reason='Job Scheduled',
                                                data={'job_id': self.scheduler.return42()})
            await websocket.send(str(response))

            # Then some "data" for testing purpose
            #for i in range(3):
            #    await websocket.send(str(self.scheduler.return42()))

        except websockets.exceptions.ConnectionClosed:
            logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
            logging.info("Cancelling listener task")


if __name__ == "__main__":
    #TODO add args to allow different service definition,
    #i.e. dev test
    #if args.dev:
    #   run_dev_stuff()
    #else: run_prod()
    # instantiate the scheduler
    scheduler = Scheduler()

    # initialize redis client
    scheduler.clean_redisKeys()
    # build resource database
    #scheduler.create_resources()

    #Instansite the handle_job_request
    handler = SchedulerHandler(scheduler, ssl_dir=Path("./ssl/scheduler"), port=3013)
    #keynamehelper.set_prefix("stack0")
    handler.run()
