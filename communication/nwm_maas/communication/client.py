import asyncio
import json
import ssl
import traceback
from abc import ABC, abstractmethod
from pathlib import Path

import websockets

from .maas_request import MaaSRequest
from .validator import NWMRequestJsonValidator

class WebSocketClient:
    """

    """
    def __init__(self, endpoint_uri: str, ssl_directory: Path):

        self.endpoint_uri = endpoint_uri

        self.client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        endpoint_pem = ssl_directory.joinpath('certificate.pem')
        self.client_ssl_context.load_verify_locations(str(endpoint_pem))
        #TODO try to connect, throw error if connection cannot be established
        self.connection = None
        self.active_connections = 0

    async def __aenter__(self):
        """
            When context is entered, use existing connection or create if none exists
        """
        if self.connection is None:
            self.connection = await websockets.client.connect(self.endpoint_uri, ssl=self.client_ssl_context)
        self.active_connections += 1
        return self

    async def __aexit__(self, *exc_info):
        """
            When context exits, decrement the connection count, when no active connections, close
        """
        self.active_connections -= 1
        if self.active_connections < 1:
            await self.connection.close()
            self.connection = None
            self.active_connections = 0

    async def async_send(self, data):
        """
            Send data to socket, wait for response

            Parameters
            ----------
            data
                string or byte array
        """
        async with self as websocket:
            #TODO ensure correct type for data???
            print("FS {}".format(data))
            await websocket.connection.send(data)

            #response = await websocket.connection.recv()
            # return json.dumps(response)
            #return response

class SchedulerClient(WebSocketClient):
    #TODO decide if this is really nessicary, it could be if structured calls
    #to and from the scheduler are required.  As it is now, it is a VERY thin
    #and probablly unnesscecary wrapper

    async def send_to_scheduler(self, data):
        """
            Ensures data is JSON encoded, and send data to the scheduler websocket endpoint.

            Parameters
            ----------
            data
                Job request data, in JSON encoded format

            Returns
            -------
            response
                string containing scheduler response. TODO this should return code and msg
        """
        try:
            data = json.loads(data)
            response = await self.async_send(str(data))
        except ValueError:
            response = "Job request not valid JSON format"
        return response

    async def get_results(self):
        async for message in self.connection:
            yield message

class MaasRequestClient(ABC):

    def __init__(self, endpoint_uri: str, ssl_directory: Path):
        self.endpoint_uri = endpoint_uri

        self.client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        endpoint_pem = ssl_directory.joinpath('certificate.pem')
        self.client_ssl_context.load_verify_locations(str(endpoint_pem))

        # TODO: get full session implementation if possible
        self._session_id, self._session_secret, self._session_created, self._is_new_session = None, None, None, None

        self._maas_job_request = None
        self._errors = None
        self._warnings = None
        self._info = None
        self.resp_as_json = None
        self.job_id = None

    async def async_send_job_request(self, maas_request: MaaSRequest):
        async with websockets.connect(self.endpoint_uri, ssl=self.client_ssl_context) as websocket:
            await websocket.send(maas_request.to_json())
            response = await websocket.recv()
            # return json.dumps(response)
            return response

    # TODO: ...
    async def authenticate_over_websocket(self):
        async with websockets.connect(self.endpoint_uri, ssl=self.client_ssl_context) as websocket:
            #async with websockets.connect(self.maas_endpoint_uri) as websocket:
            # return await EditView._authenticate_over_websocket(websocket)
            # Right now, it doesn't matter as long as it is valid
            # TODO: Fix this to not be ... fixed ...
            json_as_dict = {'username': 'someone', 'user_secret': 'something'}
            # TODO: validate before sending
            await websocket.send(json.dumps(json_as_dict))
            auth_response = json.loads(await websocket.recv())
            print('*************** Auth response: ' + json.dumps(auth_response))
            maas_session_id = auth_response['data']['session_id']
            maas_session_secret = auth_response['data']['session_secret']
            maas_session_created = auth_response['data']['created']
            return maas_session_id, maas_session_secret, maas_session_created

    @abstractmethod
    def _acquire_session_info(self, force_new: bool = False):
        """
        Attempt to set the session information properties needed to submit a maas job request.

        Note that while superclass method is fully implemented to get a new session over the websocket connection, it is
        still marked as abstract to require an override to be present (even if it is just a call to the super method).

        Parameters
        ----------
        force_new
            whether to force acquiring details for a new session, regardless of data available is available on an
            existing session

        Returns
        -------
        bool
            whether session details were acquired and set successfully
        """
        self._is_new_session = False
        try:
            auth_details = asyncio.get_event_loop().run_until_complete(self.authenticate_over_websocket())
            self._session_id, self._session_secret, self._session_created = auth_details
            self._is_new_session = True
            return True
        except:
            return False

    def _get_validation_error(self):
        is_valid, error = NWMRequestJsonValidator().validate(self.maas_job_request.to_dict())
        return error

    @abstractmethod
    def _init_maas_job_request(self):
        pass

    def _is_maas_job_request_valid(self):
        is_valid, error = NWMRequestJsonValidator().validate(self.maas_job_request.to_dict())
        return is_valid

    def _job_request_failed_due_to_expired_session(self):
        """
        Test if the response to a websocket sent request in :attr:resp_as_json failed specifically because the utilized
        session was valid, but no longer suitably authorized, indicating that it may make sense to try to authenticate a
        new session for the request and try again (i.e., it may, assuming this problem didn't occur when already using a
        freshly acquired session.)

        Returns
        -------
        bool
            whether a failure occur and it specifically was due to a lack of authorization over the used session
        """
        return self.resp_as_json is not None \
               and not self.resp_as_json['success'] \
               and self.resp_as_json['reason'] == 'Unauthorized' \
               and not self._is_new_session

    @property
    @abstractmethod
    def errors(self):
        pass

    @property
    @abstractmethod
    def info(self):
        pass

    @property
    def is_new_session(self):
        return self._is_new_session

    @property
    def maas_job_request(self):
        if self._maas_job_request is None:
            self._maas_job_request = self._init_maas_job_request()
        return self._maas_job_request

    def make_job_request(self, force_new_session: bool = False):
        self._acquire_session_info(force_new=force_new_session)
        # If able to get session details, proceed with making a job request
        if self._session_secret is not None:
            print("******************* Request: " + self.maas_job_request.to_json())
            if self._is_maas_job_request_valid():
                try:
                    req_response = asyncio.get_event_loop().run_until_complete(self.async_send_job_request(self.maas_job_request))
                    self.resp_as_json = json.loads(req_response)
                    print('***************** Response: ' + req_response)
                    if not self.validate_job_request_response():
                        raise RuntimeError('Invalid response received for requested job: ' + str(req_response))
                    # Try to get a new session if unauthorized (and we hadn't already gotten a new session)
                    elif self._job_request_failed_due_to_expired_session():
                        # Clear to we can try again with updated secret
                        self._maas_job_request = None
                        return self.make_job_request(force_new_session=True)
                    elif not self.resp_as_json['success']:
                        template = 'Request failed (reason: {}): {}'
                        raise RuntimeError(template.format(self.resp_as_json['reason'], self.resp_as_json['message']))
                    else:
                        self.job_id = self.resp_as_json['data']['job_id']
                except Exception as e:
                    # TODO: log error instead of print
                    msg = 'Encountered error submitting maas job request over session ' + str(self._session_id)
                    msg += " : \n" + str(type(e)) + ': ' + str(e)
                    print(msg)
                    traceback.print_exc()
                    self.errors.append(msg)
            else:
                msg = 'Could not submit invalid maas job request over session ' + str(self._session_id)
                msg += ' (' + str(self._get_validation_error()) + ')'
                print(msg)
                self.errors.append(msg)
        else:
            self.errors.append("Unable to acquire session details or authenticate new session for request")

    @property
    def session_created(self):
        return self._session_created

    @property
    def session_id(self):
        return self._session_id

    @property
    def session_secret(self):
        return self._session_secret

    def validate_job_request_response(self):
        # TODO: implement
        return True

    @property
    @abstractmethod
    def warnings(self):
        pass
