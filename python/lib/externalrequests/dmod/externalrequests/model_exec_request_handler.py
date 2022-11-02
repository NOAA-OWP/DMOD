import logging
import os
from pathlib import Path
from dmod.access import Authorizer
from dmod.communication import FullAuthSession, InitRequestResponseReason, ModelExecRequest, ModelExecRequestResponse, \
    NGENRequest, NGENRequestResponse, NWMRequest, NWMRequestResponse, SchedulerClient, SchedulerRequestMessage, \
    SchedulerRequestResponse, SessionManager
from .maas_request_handlers import MaaSRequestHandler
from typing import Optional

logging.basicConfig(
    level=logging.getLevelName(os.environ.get("DEFAULT_LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)


class ModelExecRequestHandler(MaaSRequestHandler):

    def __init__(self, *args, **kwargs):
        """

        Parameters
        ----------
        args
        kwargs

        Other Parameters
        ----------
        session_manager
        authorizer
        service_host
        service_port
        service_ssl_dir

        """
        super().__init__(*args, **kwargs)

        # TODO: implement properly
        self._default_required_access_type = None

        self._scheduler_client = None
        """SchedulerClient: Client for interacting with scheduler, which also is a context manager for connections."""

    def _generate_request_response(self, exec_request: ModelExecRequest, success: bool, reason: str, message: str,
                                   scheduler_response: Optional[SchedulerRequestResponse]) -> ModelExecRequestResponse:
        """
        Generate a response message of the appropriate type for the given model exec request message.

        Parameters
        ----------
        exec_request : ModelExecRequest
            The originating ::class:`ModelExecRequest` message requiring a response.
        success : bool
            Whether the request was successful.
        reason : string
            A summary of why the request was successful or not.
        message : string
            A more detailed description of why the request was successful or not.
        scheduler_response : Optional[SchedulerRequestResponse]
            Response message from the scheduler when processing the exec request resulted in a scheduler request.
        Returns
        -------
        ModelExecRequestResponse
            A generated response object of the appropriate type.
        """
        try:
            model_name = exec_request.model_name
        except Exception as e:
            model_name = '(n/a; was this a ModelExecRequest instance?)'

        if model_name == NGENRequest.model_name:
            return NGENRequestResponse(success=success, reason=reason, message=message, scheduler_response=scheduler_response)
        elif model_name == NWMRequest.model_name:
            return NWMRequestResponse(success=success, reason=reason, message=message, scheduler_response=scheduler_response)
        else:
            raise RuntimeError("Unrecognized model '{}'; cannot generate ModelExecRequestResponse".format(model_name))

    async def _is_authorized(self, request: ModelExecRequest, session: FullAuthSession) -> bool:
        """
        Determine whether the initiating user/session for a received request is currently authorized to submit such a
        request for processing.

        Parameters
        ----------
        request
        session

        Returns
        -------

        """
        # TODO: implement more completely (and implement actual authorizer)
        # TODO: in particular, finish implementation of utilized determine_required_access_types()
        required_access_types = await self.determine_required_access_types(request, session.user)
        for access_type in required_access_types:
            if not await self._authorizer.check_authorized(session.user, access_type):
                return False
        return True

    async def determine_required_access_types(self, request: ModelExecRequest, user) -> tuple:
        """
        Determine what access is required for this request from this user to be accepted.

        Determine the necessary access types for which the given user needs to be authorized in order for the user to
        be allow to submit this request, in the context of the current state of the system.

        Parameters
        ----------
        request
        user

        Returns
        -------
        A tuple of required access types required for authorization for the given request at this time.
        """
        # TODO: implement; in particular, consider things like current job count for user, and whether different access
        #   types are required at different counts.
        # FIXME: for now, just use the default type (which happens to be "everything")
        return self._default_required_access_type,

    async def handle_request(self, request: ModelExecRequest, **kwargs) -> ModelExecRequestResponse:
        """
        Handle the given request for a new NWM job execution and return the resulting response.

        Parameters
        ----------
        request: ModelExecRequest
            A ``ModelExecRequest`` message instance with details of the job being requested.

        Returns
        -------
        response: ModelExecRequestResponse
            An appropriate ``NWMRequestResponse`` object.
        """
        session, is_authorized, reason, msg = await self.get_authorized_session(request)
        if not is_authorized:
            return self._generate_request_response(exec_request=request, success=False, reason=reason.name, message=msg,
                                                   scheduler_response=None)

        # The context manager manages a SINGLE connection to the scheduler server
        # Adhoc calls to the scheduler can be made for this connection via the scheduler_client
        # These adhoc calls will use the SAME connection the context was initialized with
        logging.debug("************* Preparing scheduler request message")
        scheduler_message = SchedulerRequestMessage(model_request=request, user_id=session.user)
        logging.debug("************* Scheduler request message ready:\n{}".format(str(scheduler_message)))
        # Should be able to do this to reuse same object/context/connection across tasks, even from other methods
        async with self.service_client as scheduler_client:
            initial_response = await scheduler_client.async_make_request(scheduler_message)
            logging.debug("************* Scheduler client received response:\n{}".format(str(initial_response)))

        # TODO: consider registering the job and relationship with session, etc.
        success = initial_response.success
        success_str = 'Success' if success else 'Failure'
        reason = InitRequestResponseReason.ACCEPTED if success else InitRequestResponseReason.REJECTED
        msg = '{} submitting job to scheduler (returned id {})'.format(success_str, str(initial_response.job_id))

        return self._generate_request_response(exec_request=request, success=success, reason=reason.name, message=msg,
                                               scheduler_response=initial_response)

    @property
    def service_client(self) -> SchedulerClient:
        if self._scheduler_client is None:
            self._scheduler_client = SchedulerClient(self.service_url, self.service_ssl_dir)
        return self._scheduler_client
