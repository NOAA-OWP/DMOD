#!/usr/bin/env python3
from websockets import WebSocketServerProtocol
from typing import Tuple
from dmod.communication import WebSocketInterface, SchedulerRequestMessage, SchedulerRequestResponse
from dmod.scheduler import Scheduler, ResourceManager
from dmod.scheduler.job import RequestedJob, JobManager
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

# TODO: consider taking out loop init from WebsocketInterface implementations, instead having some "service" class own loop
# TODO: then, have WebsocketInterface implementations attach to some service


# TODO: rename to something like ExecutionHandler, and rename package as well (really goes beyond the Scheduler now)
class SchedulerHandler(WebSocketInterface):
    """
    Communication handler for the Scheduler Service, implemented with WebSocketInterface.

    Attributes
    ----------

    scheduler:
        scheduler instance to schedule requested jobs
    """

    def __init__(self, scheduler: Scheduler, job_mgr: JobManager, *args, **kwargs):
        """
            Initialize the WebSocketInterface with any user defined custom server config
        """
        super().__init__(*args, **kwargs)
        #Hold the defined scheduler instance
        self.scheduler = scheduler
        self._job_manager = job_mgr

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

            # TODO: other message types, including to start getting status info on already-made request

            # TODO: consider separating to another function, especially if info request messages are possible
            request_message = SchedulerRequestMessage.factory_init_from_deserialized_json(data)

            # Create job object for this request
            job: RequestedJob = self._job_manager.create_job(request=request_message)
            # Sanity check type
            if not isinstance(job, RequestedJob):
                obj_type = 'None' if job is None else job.__class__.__name__
                msg = "Unexpected Job object type created by job manager for request ({})".format(obj_type)
                response = SchedulerRequestResponse(success=True, reason=msg, data={'job_id': 'None'})
                await websocket.send(str(response))
                raise TypeError(msg)

            # Send request processed message back through
            response = SchedulerRequestResponse(success=True, reason='Job Request Processed',
                                                data={'job_id': job.job_id})
            await websocket.send(str(response))

            # Loop while checking for job state changes that trigger info (or data) messages back through websocket
            loop_iterations = 0
            while True:
                # Refresh data for job
                job_refreshed_copy = self._job_manager.retrieve_job(job.job_id)
                # If the job was updated ...
                if job_refreshed_copy.last_updated != job.last_updated:
                    # TODO: check to see what changed
                    # TODO: if appropriate for the change, send a status message back through the websocket
                    # Update to use the fresh copy of the job
                    job = job_refreshed_copy

                # TODO: look for some kind of break condition for leaving the loop, and for starting sending back output

                # Finally, loop maintenance
                # The first few loop iterations, sleep very briefly to catch initial updates quickly if they happen
                if loop_iterations < 2:
                    sleep_time = 0.25
                elif loop_iterations < 5:
                    sleep_time = 0.5
                else:
                    sleep_time = 60
                loop_iterations += 1
                await asyncio.sleep(sleep_time)

        except TypeError as te:
            logging.error("Problem with object types when processing received message", te)
        except websockets.exceptions.ConnectionClosed:
            logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
            logging.info("Cancelling listener task")


if __name__ == "__main__":
    raise RuntimeError('Module {} called directly; use main package entrypoint instead')
