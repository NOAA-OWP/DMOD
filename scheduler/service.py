#!/usr/bin/env python3
#TOTAL HACK to import sibling package code
import os,sys,inspect
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
#END PATH HACK

from websockets import WebSocketServerProtocol
from communication.communication.websocket_interface import WebSocketInterface
from scheduler.src.scheduler import Scheduler
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
            message = await websocket.recv()
            #TODO here we should handle already running jobs, as well as any cached
            #Do this by associating metadata in the request message with existing
            #metadata tracked by scheduler
            logging.info(f"Gor message: {message}")
            data = json.loads(message)
            logging.info(f"Got payload: {data}")
            #FIX THIS INTERFACE test.startJobs()
            #FIXME one of the first scheduler interface changes will be a domain
            #identity which services will have to mount to run
            #initial cpu/mem will be static, bound to domain ID
            job_id = self.scheduler.job_allocation_and_setup("Testing", 4 , 0) 
            await websocket.send( str(job_id) )
            await websocket.send( "Results Pending" )

        except websockets.exceptions.ConnectionClosed:
            logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
            logging.info("Cancelling listerner task")



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
    handler = SchedulerHandler(scheduler, ssl_dir=Path("./ssl/"), port=3013)
    #keynamehelper.set_prefix("stack0")
    handler.run()
