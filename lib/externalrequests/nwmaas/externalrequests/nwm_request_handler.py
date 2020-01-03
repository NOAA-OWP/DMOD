import logging
from pathlib import Path
from nwmaas.access import Authorizer
from nwmaas.communication import AbstractRequestHandler, FullAuthSession, NWMRequest, NWMRequestResponse, \
    SchedulerClient, SchedulerRequestMessage, SessionManager

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
        self._required_access_type = None

        self.scheduler_client_ssl_dir = scheduler_ssl_dir

        self._scheduler_client = SchedulerClient(self._scheduler_url, self.scheduler_client_ssl_dir)
        """SchedulerClient: Client for interacting with scheduler, which also is a context manager for connections."""

    async def _is_authorized(self, session: FullAuthSession):
        return self._authorizer.check_authorized(session.user, self._required_access_type)

    async def handle_request(self, request: NWMRequest, **kwargs) -> NWMRequestResponse:
        """
        Handle the given request for a new NWM job execution and return the resulting response.

        Parameters
        ----------
        request: NWMRequest
            A ``NWMRequest`` message instance with details of the job being requested.

        Other Parameters
        ----------
        session: FullAuthSession
            The session over which the request was made, used to determine if the request is sufficiently authorized.

        Returns
        -------
        response: NWMRequestResponse
            An appropriate ``NWMRequestResponse`` object.
        """
        session: FullAuthSession = kwargs['session'] if kwargs and 'session' in kwargs else None

        is_authorized = self._is_authorized(session)

        if session is not None and request.session_secret == session.session_secret and is_authorized:
            # TODO: push to redis stream, associating with this session somehow, and getting some kind of id back
            job_id = 0
            mesg = 'Awaiting implementation of handler-to-scheduler communication' if job_id == 0 else ''
            #The context manager manages a SINGLE connection to the scheduler server
            #Adhoc calls to the scheduler can be made for this connection via the scheduler_client
            #These adhoc calls will use the SAME connection the context was initialized with
            logging.debug("************* Preparing scheduler request message")
            scheduler_message = SchedulerRequestMessage(model_request=request, user_id=session.user)
            logging.debug("************* Scheduler request message ready:\n{}".format(str(scheduler_message)))
            #async with SchedulerClient(scheduler_url, self.scheduler_client_ssl_dir) as scheduler_client:
            # Should be able to do this to reuse same object/context/connection across tasks, even from other methods
            async with self._scheduler_client as scheduler_client:
                initial_response = await scheduler_client.send_to_scheduler(scheduler_message)
                logging.debug("************* Scheduler client received response:\n{}".format(str(initial_response)))
                if initial_response.success:
                    job_id = initial_response.job_id
                    # TODO: maybe here, formalize responses to a degree containing data
                    #async for response in scheduler_client.get_results():
                    #    logging.debug("************* Results:\n{}".format(str(response)))
                    #    print(response)
                #TODO loop here to receive multiple requests, try while execpt connectionClosed, let server tell us when to stop listening
            # TODO: consider registering the job and relationship with session, etc.
            success = initial_response.success
            logging.error("************* initial response: " + str(initial_response))
            reason = ('Success' if success else 'Failure') + ' starting job (returned id ' + str(job_id) + ')'
            # TODO: right now, the only supported MaaSRequest we will see is a NWMRequest, but account for other things
            response = NWMRequestResponse(success=success, reason=reason, message=mesg,
                                          data={'job_id': job_id, 'scheduler_response': initial_response.to_dict()})
        else:
            if session is None:
                msg = 'Request does not correspond to an authenticated session'
            elif session is not None and request.session_secret != session.session_secret:
                msg = 'Request does not correspond to an authenticated session: secrets do not agree'
                msg += '(' + request.session_secret + ' | ' + session.session_secret + ')'
                logging.debug("*************" + msg)
            elif not is_authorized:
                msg = 'Session {} not authorized for NWM job request {}'.format(
                    str(session.session_id), request.to_json())
                logging.debug("*************" + msg)
            # TODO: right now, the only supported MaaSRequest we will see is a NWMRequest, but account for other things
            response = NWMRequestResponse(success=False, reason='Unauthorized', message=msg)
        return response
