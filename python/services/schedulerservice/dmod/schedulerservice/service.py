#!/usr/bin/env python3
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)

from websockets import WebSocketServerProtocol
from typing import Awaitable, Callable, Dict, List, Type, TypeVar
from dmod.core.exception import DmodRuntimeError
from dmod.core.serializable import BasicResultIndicator
from dmod.communication import AbstractInitRequest, InvalidMessageResponse, Message, SchedulerRequestMessage, \
    SchedulerRequestResponse, UpdateMessage, UpdateMessageResponse, WebSocketInterface
from dmod.communication.maas_request.job_message import (JobControlAction, JobControlRequest, JobControlResponse,
                                                         JobInfoRequest, JobInfoResponse, JobListRequest,
                                                         JobListResponse)
from dmod.scheduler.job import Job, JobExecStep, JobManager, JobStatus
import json

import asyncio
import websockets
from datetime import datetime, timedelta

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

    @staticmethod
    async def _update_client_on_requested_job(previous_job_state: Job, updated_job_state: Job,
                                              websocket: WebSocketServerProtocol):
        """
        Send an update message back to the client that initiated a scheduler request when the associated job updates it
        state, and await a valid response to the update message.

        Note that if an invalid response comes back, either because it isn't a response at all or the digest is wrong,
        an error is logged, but processing otherwise continues.

        Parameters
        ----------
        previous_job_state : Job
            An object representing the updated job in its prior state.
        updated_job_state : Job
            An object representing the updated job in its updated state.
        websocket : WebSocketServerProtocol
            The websocket for client communication.
        """
        updates = dict()
        # For now, the only relevant change should be a change in status
        if updated_job_state.status != previous_job_state.status:
            updates['status'] = str(updated_job_state.status)

        # Exit without doing anything if no relevant updates were made
        if len(updates) == 0:
            return

        # Otherwise, send update message over socket and await response
        # TODO: should any retries be considered?
        update_message = UpdateMessage(previous_job_state.job_id, previous_job_state.__class__, updates)
        await websocket.send(str(update_message))
        # Then wait for the next message
        response_raw = await websocket.recv()
        response = UpdateMessageResponse.factory_init_from_deserialized_json(json.loads(response_raw))

        if response is None or not isinstance(response, UpdateMessageResponse):
            logging.error('Expected response to update message {}, but got something else: {}'.format(
                update_message.digest, response_raw))
        elif isinstance(response, UpdateMessageResponse) and response.digest != update_message.digest:
            logging.error('Expected response to update message {}, but response digest {}'.format(
                update_message.digest, response.digest))

    _REQ_C = TypeVar('_REQ_C', bound=Type[AbstractInitRequest])
    """Type var needed for the bounds of keys for :meth:`_get_parseable_request_funcs` (`TypeVar`)."""
    _REQ_T = TypeVar('_REQ_T', bound=AbstractInitRequest)
    """Type var needed for the bounds of callable values for :meth:`_get_parseable_request_funcs` (`TypeVar`)."""

    # TODO: perhaps add this functionality below to the actual abstract interface
    @classmethod
    def _get_parseable_request_funcs(cls) -> Dict[_REQ_C, Callable[[_REQ_T, WebSocketServerProtocol], Awaitable[None]]]:
        """
        Get the collection of handled :class:`AbstractInitRequest` subtypes mapped to handler funcs.

        Get a dictionary whose keys are all :class:`AbstractInitRequest` subtypes for which this type supports parsing
        when handling incoming messages in :meth:`listener`.  The keys are mapped to the particular instance function
        of this type that the type's :meth:`listener` uses to handle the processing of a message of the key's type.

        Returns
        -------
        Dict[_REQ_C, Callable[[_REQ_T, WebSocketServerProtocol], Awaitable[None]]]
            The collection of handled :class:`AbstractInitRequest` subtypes mapped to handler funcs.

        See Also
        --------
        listener
        """
        # TODO: add something for reconnecting to monitor progress of job after being disconnected
        return {
            JobControlRequest: cls._handle_job_control_request,
            JobInfoRequest: cls._handle_job_info_request,
            JobListRequest: cls._handle_job_list_request,
            SchedulerRequestMessage: cls._handle_scheduler_request,
            UpdateMessage: cls._handle_update_message
        }

    @classmethod
    def get_parseable_request_types(cls) -> List[Type[AbstractInitRequest]]:
        """
        Get the ::class:`AbstractInitRequest` subtypes this type supports parsing when handling incoming messages.

        Returns
        -------
        List[Type[AbstractInitRequest]]
            The ::class:`AbstractInitRequest` subtypes this type supports parsing when handling incoming messages.

        See Also
        --------
        get_parseable_request_funcs
        """
        return sorted(k for k in cls._get_parseable_request_funcs())

    def __init__(self, job_mgr: JobManager, *args, **kwargs):
        """
            Initialize the WebSocketInterface with any user defined custom server config
        """
        super().__init__(*args, **kwargs)
        self._job_manager = job_mgr

    async def _handle_job_control_request(self, message: JobControlRequest, websocket: WebSocketServerProtocol):
        try:
            if message.action == JobControlAction.INVALID:
                raise DmodRuntimeError(f"Can't request scheduler service to perform {message.action!s} action on job.")
            elif message.action == JobControlAction.STOP:
                response = await self._request_job_stop(job_id=message.job_id)
            elif message.action == JobControlAction.RELEASE:
                response = await self._request_job_release(job_id=message.job_id)
            elif message.action == JobControlAction.RESTART:
                response = await self._request_job_restart(message.job_id)
            else:
                raise NotImplementedError(f"Scheduler service unable to handle {message.action!s} job control action.")
        except Exception as e:
            response = BasicResultIndicator(action=message.action, job_id=message.job_id, success=False,
                                            reason=f"{e.__class__.__name__}", message=f"Error message was: `{e!s}`")
        await websocket.send(str(response))

    async def _handle_job_info_request(self, message: JobInfoRequest, websocket: WebSocketServerProtocol):
        # Get current persisted copy of Job object
        job = self._job_manager.retrieve_job(message.job_id)
        response = JobInfoResponse(job_id=message.job_id, status_only=message.status_only,
                                   data=job.status.to_dict() if message.status_only else job.to_dict())
        await websocket.send(str(response))

    async def _handle_job_list_request(self, message: JobListRequest, websocket: WebSocketServerProtocol):
        response = JobListResponse(only_active=message.only_active,
                                   data=self._job_manager.get_job_ids(message.only_active))
        await websocket.send(str(response))

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
        """

        # Create job object for this request
        job = self._job_manager.create_job(request=message)

        # Send request processed message back through
        response = SchedulerRequestResponse(success=True, reason='Job Request Processed', data={'job_id': job.job_id})
        await websocket.send(str(response))

        loop_iterations = 0
        # Check for job state changes that trigger info (or data) messages back through websocket
        # Loop for as long as the job is in some active state
        while job.status.is_active:
            # Sleep after first time through the loop, though more briefly the first few times to catch initial updates
            # Have sleep logic at top of loop so loop condition is checked immediately after any chance for it to change
            if loop_iterations == 1:
                await asyncio.sleep(0.25)
            elif 0 < loop_iterations < 5:
                await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(60)
            loop_iterations += 1

            # Refresh data for job
            job_refreshed_copy = self._job_manager.retrieve_job(job.job_id)
            # If the job was updated ...
            if job_refreshed_copy.last_updated != job.last_updated:
                # Send an update message as needed
                await self._update_client_on_requested_job(previous_job_state=job, updated_job_state=job_refreshed_copy,
                                                           websocket=websocket)
                # Update to use the fresh copy of the job
                job = job_refreshed_copy

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
        job = self._job_manager.retrieve_job(message.object_id)

        # Only accept updates to active Jobs, so verify the Job is active
        if not job.status.is_active:
            msg = 'The given `{}` no longer has an active status, and thus cannot be updated.'.format(
                message.object_type_string)
            response = UpdateMessageResponse(digest=message.digest, object_found=True, success=False,
                                             reason='Job Not Active', response_text=msg)
            await websocket.send(str(response))
            return

        # TODO: Refactor this in a way that is more extensible and also lends itself better to unit testing
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

    async def _request_job_release(self, job_id: str) -> JobControlResponse:
        mgr_result = self._job_manager.release_allocations(job_id)
        return JobControlResponse(action=JobControlAction.RELEASE, job_id=job_id, success=mgr_result.success,
                                  reason=mgr_result.reason, message=mgr_result.message)

    async def _request_job_restart(self, job_id: str) -> JobControlResponse:
        mgr_result = self._job_manager.request_restart(job_id)
        return JobControlResponse(action=JobControlAction.RESTART, job_id=job_id, success=mgr_result.success,
                                  reason=mgr_result.reason, message=mgr_result.message)

    async def _request_job_stop(self, job_id: str, timeout: timedelta = timedelta(minutes=1)) -> JobControlResponse:
        """
        Request that the job manager stop a job, then watch to see that a job enters the ``STOPPED`` step.

        Parameters
        ----------
        job_id: str
            The id of the job in question.
        timeout: timedelta
            An amount of time to wait before considering the operation to have failed (by default, 1 minute)

        Returns
        ----------
        JobControlResponse
            An response to the original request indicating whether the stop was successful.
        """
        mgr_result = self._job_manager.request_stop(job_id)
        if not mgr_result.success:
            return JobControlResponse(action=JobControlAction.STOP, job_id=job_id, success=False,
                                      reason=f"Manager Rejected: {mgr_result.reason}", message=mgr_result.message)

        deadline = datetime.now() + timeout
        while datetime.now() < deadline:
            if self._job_manager.retrieve_job(job_id).status_step == JobExecStep.STOPPED:
                return JobControlResponse(action=JobControlAction.STOP, job_id=job_id, success=True,
                                            reason="Job Stopped")
            await asyncio.sleep(2)
        return JobControlResponse(action=JobControlAction.STOP, job_id=job_id, success=False,
                                  reason="Timeout Wait For Stop", message=f"Timeout of {timedelta!s} reached.")

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

            found_type = None
            # Deserialize the message to the appropriate type if possible
            for init_message_class_type in self._get_parseable_request_funcs():
                message = init_message_class_type.factory_init_from_deserialized_json(data)
                # If successfully deserialized to something non-None, break here and process the message
                if message is not None:
                    found_type = init_message_class_type
                    break
            # If not some supported message type ...
            if found_type is None:
                msg = f"Unrecognized message received over {self.__class__.__name__} websocket (message: `{message}`)"
                response = InvalidMessageResponse(data={'message_content': message})
                await websocket.send(str(response))
                raise TypeError(msg)

            # Once message type is found and instance is deserialized handle appropriately
            await self._get_parseable_request_funcs()[found_type](message, websocket)

        except TypeError as te:
            logging.error("Problem with object types when processing received message", te)
        except websockets.exceptions.ConnectionClosed:
            logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
            logging.info("Cancelling listener task")


if __name__ == "__main__":
    raise RuntimeError('Module {} called directly; use main package entrypoint instead')
