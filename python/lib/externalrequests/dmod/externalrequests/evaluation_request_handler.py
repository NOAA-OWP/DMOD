import logging
import typing
from pathlib import Path
import dmod.access as access
import dmod.communication as communication
import dmod.communication.evaluation_request as evaluation_requests
from .maas_request_handlers import MaaSRequestHandler


class EvaluationRequestHandler(MaaSRequestHandler):

    def __init__(
        self,
        session_manager: communication.SessionManager,
        authorizer: access.Authorizer,
        evaluation_service_host: str,
        evaluation_service_port: int,
        evaluation_service_ssl_dir: Path
    ):
        super().__init__(session_manager=session_manager,
                                                    authorizer=authorizer,
                                                    service_host=evaluation_service_host,
                                                    service_port=evaluation_service_port,
                                                    service_ssl_dir=evaluation_service_ssl_dir)

        # TODO: implement properly
        self._default_required_access_type = None

        self._service_client = None

    async def determine_required_access_types(self, request: evaluation_requests.EvaluationRequest, user) -> tuple:
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

    async def handle_request(self, request: evaluation_requests.EvaluationRequest, **kwargs) -> communication.Response:
        # Need receiver websocket (i.e. DMOD client side) as kwarg
        session, is_authorized, reason, msg = await self.get_authorized_session(request)
        if not is_authorized:
            return evaluation_requests.EvaluationConnectionRequestResponse(
                success=False,
                reason=reason.name,
                message=msg
            )
        # In this case, we actually can pass the request as-is straight through (i.e., after confirming authorization)
        async with self.service_client as client:
            response = await client.async_make_request(request)
            logging.debug("************* {} received response:\n{}".format(self.__class__.__name__, str(response)))
        # Likewise, can just send back the response from the internal service client
        return response

    @property
    def service_client(self) -> DataServiceClient:
        if self._service_client is None:
            self._service_client = DataServiceClient(self.service_url, self.service_ssl_dir)
        return self._service_client
