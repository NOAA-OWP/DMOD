import logging
from pathlib import Path
from dmod.access import Authorizer
from dmod.communication import AbstractRequestHandler, FullAuthSession, NWMRequest, NWMRequestResponse, \
    SchedulerClient, SchedulerRequestMessage, SessionManager, InitRequestResponseReason

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)


class NWMRequestHandler(AbstractRequestHandler):

    def __init__(self, session_manager: SessionManager, authorizer: Authorizer, scheduler_host: str,
                 scheduler_port: int, scheduler_ssl_dir: Path):
        self._session_manager = session_manager
        self._authorizer = authorizer
        self._scheduler_host = scheduler_host
        self._scheduler_port = scheduler_port
        self._scheduler_url = "wss://{}:{}".format(self._scheduler_host, self._scheduler_port)

        # TODO: implement properly
        self._default_required_access_type = None

        self.scheduler_client_ssl_dir = scheduler_ssl_dir

        self._scheduler_client = SchedulerClient(self._scheduler_url, self.scheduler_client_ssl_dir)
        """SchedulerClient: Client for interacting with scheduler, which also is a context manager for connections."""

    async def _is_authorized(self, request: NWMRequest, session: FullAuthSession) -> bool:
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

    async def determine_required_access_types(self, request: NWMRequest, user) -> tuple:
        """
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

    async def handle_request(self, request: NWMRequest, **kwargs) -> NWMRequestResponse:
        """
        Handle the given request for a new NWM job execution and return the resulting response.

        Parameters
        ----------
        request: NWMRequest
            A ``NWMRequest`` message instance with details of the job being requested.

        Returns
        -------
        response: NWMRequestResponse
            An appropriate ``NWMRequestResponse`` object.
        """
        session = self._session_manager.lookup_session_by_secret(request.session_secret)
        if session is None:
            reason = InitRequestResponseReason.UNRECOGNIZED_SESSION_SECRET
            msg = 'Request {} does not correspond to a known authenticated session'.format(request.to_json())
        elif not await self._is_authorized(request=request, session=session):
            reason = InitRequestResponseReason.UNAUTHORIZED
            msg = 'User {} in session [{}] not authorized for NWM job request {}'.format(
                session.user, str(session.session_id), request.to_json())
            logging.debug("*************" + msg)
        else:
            # The context manager manages a SINGLE connection to the scheduler server
            # Adhoc calls to the scheduler can be made for this connection via the scheduler_client
            # These adhoc calls will use the SAME connection the context was initialized with
            logging.debug("************* Preparing scheduler request message")
            scheduler_message = SchedulerRequestMessage(model_request=request, user_id=session.user)
            logging.debug("************* Scheduler request message ready:\n{}".format(str(scheduler_message)))
            # Should be able to do this to reuse same object/context/connection across tasks, even from other methods
            async with self._scheduler_client as scheduler_client:
                initial_response = await scheduler_client.async_make_request(scheduler_message)
                logging.debug("************* Scheduler client received response:\n{}".format(str(initial_response)))
                if initial_response.success:
                    job_id = initial_response.job_id
                    #async for response in scheduler_client.get_results():
                    #    logging.debug("************* Results:\n{}".format(str(response)))
                    #    print(response)
            # TODO: consider registering the job and relationship with session, etc.
            success = initial_response.success
            success_str = 'Success' if success else 'Failure'
            reason = InitRequestResponseReason.ACCEPTED if success else InitRequestResponseReason.REJECTED
            mesg = '{} submitting job to scheduler (returned id {})'.format(success_str, str(initial_response.job_id))
            # TODO: right now, the only supported MaaSRequest we will see is a NWMRequest, but account for other things
            return NWMRequestResponse(success=success, reason=reason.name, message=mesg, scheduler_response=initial_response)

        # If we didn't just return by executing 'else' condition above (i.e., we don't have an authorized session) ...
        return NWMRequestResponse(success=False, reason=reason.name, message=msg)
