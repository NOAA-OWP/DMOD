#!/usr/bin/env python3
from websockets import WebSocketServerProtocol
from typing import List, Type
from dmod.communication import InvalidMessageResponse, Message, SchedulerRequestMessage, SchedulerRequestResponse, \
    UpdateMessage, UpdateMessageResponse, WebSocketInterface
from dmod.scheduler import Scheduler, ResourceManager
from dmod.scheduler.job import RequestedJob, Job, JobManager, JobStatus
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

    async def _handle_scheduler_request(self, message: SchedulerRequestMessage, websocket: WebSocketServerProtocol):
        """
        Async logic for processing after receiving an incoming websocket connection with an opening message that is an
        ::class:`SchedulerRequestMessage` object.

        Parameters
        ----------
        message : SchedulerRequestMessage
            The initial message over the websocket, requesting a job be scheduled.
        websocket : WebSocketServerProtocol
            The websocket connection.

        Raises
        ----------
        TypeError
            Raised if the ::class:`Job` object deserialized from the message is not a ::class:`RequestedJob`.
        """

        # Create job object for this request
        job: RequestedJob = self._job_manager.create_job(request=message)
        # Sanity check type
        if not isinstance(job, RequestedJob):
            obj_type = 'None' if job is None else job.__class__.__name__
            msg = "Unexpected Job object type created by job manager for request ({})".format(obj_type)
            response = SchedulerRequestResponse(success=True, reason=msg, data={'job_id': 'None'})
            await websocket.send(str(response))
            raise TypeError(msg)

        # Send request processed message back through
        response = SchedulerRequestResponse(success=True, reason='Job Request Processed', data={'job_id': job.job_id})
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

    async def _handle_update_message(self, message: UpdateMessage, websocket: WebSocketServerProtocol):
        # Only accept updates to Job objects, so verify the type
        if message.object_type != Job and not issubclass(message.object_type, Job):
            msg = 'The update message type `{}` is not a Job subtype, which is required for {}'.format(
                message.object_type_string, self.__class__.__name__)
            response = UpdateMessageResponse(digest=message.digest, object_found=False, success=False,
                                             reason='Unrecognized Type', response_text=msg)
            await websocket.send(str(response))
            raise TypeError(msg)

        # Get current persisted copy of Job object
        job: RequestedJob = self._job_manager.retrieve_job(message.object_id)

        # Only accept updates to active Jobs, so verify the Job is active
        if not job.status.is_active:
            msg = 'The given `{}` no longer has an active status, and thus cannot be updated.'.format(
                message.object_type_string)
            response = UpdateMessageResponse(digest=message.digest, object_found=True, success=False,
                                             reason='Job Not Active', response_text=msg)
            await websocket.send(str(response))
            return

        # Names of actual properties, but properties that can't be updated like this via an update message.
        real_but_unsupported_properties = {'allocation_paradigm', 'allocations', 'job_id', 'originating_request', 'parameters'}
        # TODO: Second set for things that are not updateable now, but perhaps we should consider allowing
        real_but_unsupported_for_now_properties = {'cpu_count', 'memory_size', 'rsa_key_pair'}

        # Track whether something actually changed
        was_modified = False
        for property_key in message.updated_data:
            if property_key in real_but_unsupported_properties:
                msg = 'Cannot update `{}` property for `{}` objects.'.format(property_key, message.object_type_string)
                response = UpdateMessageResponse(digest=message.digest, object_found=True, success=False,
                                                 reason='Immutable Property Update', response_text=msg)
                await websocket.send(str(response))
                return
            elif property_key in real_but_unsupported_for_now_properties:
                msg = 'Cannot update `{}` property for `{}` objects.'.format(property_key, message.object_type_string)
                response = UpdateMessageResponse(digest=message.digest, object_found=True, success=False,
                                                 reason='Immutable Property Update', response_text=msg)
                await websocket.send(str(response))
                return
            elif property_key == 'status':
                new_status = JobStatus.get_for_name(message.updated_data[property_key])
                if job.status != new_status:
                    job.status = new_status
                    was_modified = True
            else:
                msg = 'Unrecognized `{}` property for `{}` objects.'.format(property_key, message.object_type_string)
                response = UpdateMessageResponse(digest=message.digest, object_found=True, success=False,
                                                 reason='Unrecognized Property Update', response_text=msg)
                await websocket.send(str(response))
                return

        # Save updates if something was actually modified
        if was_modified:
            self._job_manager.save_job(job)
        response = UpdateMessageResponse(digest=message.digest, object_found=True, success=True,
                                         reason='Successful Update')
        await websocket.send(str(response))

    async def listener(self, websocket: WebSocketServerProtocol, path):
        """
        Process incoming messages, for things like ::class:`Job` requests or updates, via a listened-for websocket,
        kicking off the appropriate actions and sending the appropriate response or responses back via the websocket.

        Note that this particular implementation does not perform any access-like checking on the incoming messages.
        Any message received is assumed to be something that should be process so long as the message is valid
        syntactically and semantically.
        """
        print("Scheduler Listener")

        try:
            message = await websocket.recv()
            logging.info(f"Got message: {message}")
            data = json.loads(message)
            logging.info(f"Got payload: {data}")

            # TODO: perhaps add this functionality below to the actual abstract interface
            # Define the types of initial messages we can receive, and the specific function that handles the rest of
            # processing when such a message comes in
            supported_init_message_types: List[Type[Message]] = [SchedulerHandler, UpdateMessage]

            # Deserialize the message to the appropriate type if possible
            for init_message_class_type in supported_init_message_types:
                message = init_message_class_type.factory_init_from_deserialized_json(data)
                # If successfully deserialized to something non-None, break here and process the message
                if message is not None:
                    break
            # Once message is deserialized (or potential supported types are exhausted), handle appropriately
            if isinstance(message, SchedulerRequestMessage):
                await self._handle_scheduler_request(message=message, websocket=websocket)
            elif isinstance(message, UpdateMessage):
                await self._handle_update_message(message=message, websocket=websocket)
            # TODO: add something for reconnecting to monitor progress of job after being disconnected
            # TODO: potentially add something for restarting a stopped job (if the workflow requires)
            # If not some supported message type ...
            else:
                content = str(data)
                msg = "Unrecognized message format received over {} websocket (message: `{}`)".format(
                    self.__class__.__name__, content)
                response = InvalidMessageResponse(data={'message_content': content})
                await websocket.send(str(response))
                raise TypeError(msg)

        except TypeError as te:
            logging.error("Problem with object types when processing received message", te)
        except websockets.exceptions.ConnectionClosed:
            logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
            logging.info("Cancelling listener task")


if __name__ == "__main__":
    raise RuntimeError('Module {} called directly; use main package entrypoint instead')
