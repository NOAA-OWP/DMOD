import asyncio
import datetime
import unittest
from pathlib import Path
from nwmaas.access import RedisBackendSessionManager
from nwmaas.communication import NWMRequest, NWMRequestResponse, SchedulerClient, SchedulerRequestMessage, \
    SchedulerRequestResponse, InitRequestResponseReason
from ..test import FailureTestingAuthUtil, SucceedTestAuthUtil, TestingSession, TestingSessionManager
from ..externalrequests import NWMRequestHandler


class DummySchedulerClient(SchedulerClient):

    def __init__(self, test_successful: bool = True, starting_job_id: int = 1):
        super().__init__(endpoint_uri='wss://127.0.0.1:12345', ssl_directory=Path('.'))
        self.test_successful = test_successful
        self._next_job_id = starting_job_id if isinstance(starting_job_id, int) else 1
        self._first_job_id = self._next_job_id

    @property
    def next_job_id(self):
        """
        Get and return the next job id value to use, bumping the internal value for next time.

        Returns
        -------
        The next job id value that should be used
        """
        next_id = self._next_job_id
        self._next_job_id += 1
        return next_id

    @property
    def last_job_id(self):
        """
        Get the job id value for the last job - i.e., the most recent value returned by a call to ``next_job_id`` - or
        ``None``.

        Returns
        -------
        int or None
        """
        return None if self._next_job_id == self._first_job_id else self._next_job_id - 1

    async def async_make_request(self, message: SchedulerRequestMessage) -> SchedulerRequestResponse:
        """
        Override superclass implementation with stub that returns either a generic successful response or generic
        failure response based on the :attr:`test_successful` instance attribute.

        Parameters
        ----------
        message

        Returns
        -------
        SchedulerRequestResponse
            a generic successful response if :attr:`test_successful` is ``True``; otherwise a generic failure response
        """
        return SchedulerRequestResponse(success=self.test_successful, reason='Testing Stub', message='Testing stub',
                                        data={'job_id': self.next_job_id} if self.test_successful else None)

    async def __aenter__(self):
        """
        Override superclass implementation with stub that replaces :attr:`connection` value with a dummy int, rather
        than an actual websocket connection.
        """
        # Basically, block here using await+sleep (with a timeout) if another task/event exec is opening a connection
        # Implicitly, this would mean said task is in an await, and execution went back to event loop (i.e., this call)
        # Also, for efficiency, delay datetime-related ops until first loop iteration, to avoid if the loop never runs
        timeout_limit = None
        while self._opening_connection and (timeout_limit is None or datetime.datetime.now() < timeout_limit):
            if timeout_limit is None:
                timeout_limit = datetime.datetime.now() + datetime.timedelta(seconds=15)
            await asyncio.sleep(0.25)

        # Safely conclude at this point that nothing else (worth paying attention to) is in the middle of opening a
        # connection, so check whether there already is one ...
        if self.connection is None:
            # If not, mark that this exec is opening a connection, before giving up control during the await
            self._opening_connection = True
            # Then set the stub for the connection
            self.connection = 0
            # And now, note that we are no longer in the middle of an attempt to open a connection
            self._opening_connection = False

        self.active_connections += 1
        return self

    async def __aexit__(self, *exc_info):
        """
        Override superclass implementation with stub that knows :attr:`connection` is not an actual connection, and thus
        does everything like the superclass implementation except make a call to ``close()``.
        """
        self.active_connections -= 1
        if self.active_connections < 1:
            #await self.connection.close()
            self.connection = None
            self.active_connections = 0


class IntegrationTestNWMRequestHandler(unittest.TestCase):

    def setUp(self) -> None:

        self._user_1 = 'test_user_1'
        self._user_2 = 'test_user_2'
        self._user_3 = 'test_user_3'
        self._session_ip_1 = '127.0.0.2'
        self._session_ip_2 = '127.0.0.3'
        self._session_ip_3 = '127.0.0.4'

        self.session_manager = RedisBackendSessionManager(redis_host='127.0.0.1',
                                                          redis_port=19379,
                                                          redis_pass='***REMOVED***')

        self.fail_authorizer = FailureTestingAuthUtil()
        self.success_authorizer = SucceedTestAuthUtil()

        # TODO: set these correctly
        self.scheduler_host = '127.0.0.1'
        self.scheduler_port = 19380
        self.scheduler_ssl_dir = Path('./ssl')

        #self._handler = None
        self.handler = NWMRequestHandler(session_manager=self.session_manager,
                                         authorizer=self.success_authorizer,
                                         scheduler_host=self.scheduler_host,
                                         scheduler_port=self.scheduler_port,
                                         scheduler_ssl_dir=self.scheduler_ssl_dir)

    def tearDown(self) -> None:
        pass

    def test_handle_request_1_a(self):
        """
        Test that the ``handle_request()`` method returns a failure response if the session for the secret cannot be
        found.
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        # Now, remove the session from the manager
        self.session_manager.remove_session(session)

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)
        self.assertFalse(response.success)

    def test_handle_request_1_b(self):
        """
        Test that the ``handle_request()`` method returns an appropriate failure response with the correct failure
        reason if the session for the secret cannot be found.
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        # Now, remove the session from the manager
        self.session_manager.remove_session(session)

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)
        self.assertEqual(response.reason, InitRequestResponseReason.UNRECOGNIZED_SESSION_SECRET.name)

    def test_handle_request_1_c(self):
        """
        Test that the ``handle_request()`` method returns an appropriate failure response with the correct failure
        reason if the user is not authorized.
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        #self.session_manager._authorizer = self.fail_authorizer
        self.handler._authorizer = self.fail_authorizer

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)
        self.assertEquals(response.reason, InitRequestResponseReason.UNAUTHORIZED.name)

    def test_handle_request_2_a(self):
        """
        Test that the ``handle_request()`` method returns a success response when the session and authorization are
        good, and the request to the scheduler is appropriate and successful (simulated in testing via a dummy scheduler
        client).
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        dummy_scheduler_client = DummySchedulerClient(test_successful=True)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)
        self.assertTrue(response.success)

    def test_handle_request_2_b(self):
        """
        Test that the ``handle_request()`` method returns a success response with the expected reason value when the
        session and authorization are good, and the request to the scheduler is appropriate and successful (simulated in
        testing via a dummy scheduler client).
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        dummy_scheduler_client = DummySchedulerClient(test_successful=True)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)
        expected_reason = InitRequestResponseReason.ACCEPTED.name
        self.assertEquals(response.reason, expected_reason)

    def test_handle_request_2_c(self):
        """
        Test that the ``handle_request()`` method returns a success response with the job_id value when the session and
        authorization are good, and the request to the scheduler is appropriate and successful (simulated in testing via
        a dummy scheduler client).
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        dummy_scheduler_client = DummySchedulerClient(test_successful=True)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)
        self.assertEquals(response.job_id, dummy_scheduler_client.last_job_id)

    def test_handle_request_2_d(self):
        """
        Test that the ``handle_request()`` method returns a success response with a valid serialized
        :class:`SchedulerRequestResponse` embedded in the data attribute, when the session and authorization are good,
        and the request to the scheduler is appropriate and successful (simulated in testing via a dummy scheduler
        client).
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        dummy_scheduler_client = DummySchedulerClient(test_successful=True)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)

        data_key = NWMRequestResponse.get_data_dict_key_for_scheduler_response()
        deserialized_json_dict = response.data[data_key]
        scheduler_response = SchedulerRequestResponse.factory_init_from_deserialized_json(deserialized_json_dict)

        self.assertTrue(isinstance(scheduler_response, SchedulerRequestResponse))

    def test_handle_request_2_e(self):
        """
        Test that the ``handle_request()`` method returns a success response has a valid serialized
        :class:`SchedulerRequestResponse` embedded in the data attribute, and that this scheduler response is also set
        as successful, when the session and authorization are good, and the request to the scheduler is appropriate and
        successful (simulated in testing via a dummy scheduler client).
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        dummy_scheduler_client = DummySchedulerClient(test_successful=True)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)

        data_key = NWMRequestResponse.get_data_dict_key_for_scheduler_response()
        deserialized_json_dict = response.data[data_key]
        scheduler_response = SchedulerRequestResponse.factory_init_from_deserialized_json(deserialized_json_dict)

        self.assertTrue(scheduler_response.success)

    def test_handle_request_3_a(self):
        """
        Test that the ``handle_request()`` method returns a failure response when the session and authorization are
        good, but the request to the scheduler is not successful for some reason (simulated in testing via a dummy
        scheduler client).
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        dummy_scheduler_client = DummySchedulerClient(test_successful=False)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)
        self.assertFalse(response.success)

    def test_handle_request_3_b(self):
        """
        Test that the ``handle_request()`` method returns a failure response with the expected reason value when the
        session and authorization are good, but the request to the scheduler is not successful (simulated in testing via
        a dummy scheduler client).
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        dummy_scheduler_client = DummySchedulerClient(test_successful=False)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)
        expected_reason = InitRequestResponseReason.REJECTED.name
        self.assertEquals(response.reason, expected_reason)

    def test_handle_request_3_c(self):
        """
        Test that the ``handle_request()`` method returns a failure response with the error job_id value when the
        session and authorization are good, but the request to the scheduler is not successful (simulated in testing via
        a dummy scheduler client).
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        dummy_scheduler_client = DummySchedulerClient(test_successful=False)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)
        self.assertEquals(response.job_id, -1)

    def test_handle_request_3_d(self):
        """
        Test that the ``handle_request()`` method returns a failure response with a valid serialized
        :class:`SchedulerRequestResponse` embedded in the data attribute, when the session and authorization are good,
        but the request to the scheduler are not successful (simulated in testing via a dummy scheduler client).
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        dummy_scheduler_client = DummySchedulerClient(test_successful=False)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)
        sched_resp = SchedulerRequestResponse.factory_init_from_deserialized_json(response.data['scheduler_response'])
        self.assertTrue(isinstance(sched_resp, SchedulerRequestResponse))

    def test_handle_request_3_e(self):
        """
        Test that the ``handle_request()`` method returns a failure response has a valid serialized
        :class:`SchedulerRequestResponse` embedded in the data attribute, and that this scheduler response is also
        marked as failed, when the session and authorization are good, and the request to the scheduler is not
        successful (simulated in testing via a dummy scheduler client).
        """
        ip_addr = self._session_ip_1
        user = self._user_1
        session = self.session_manager.create_session(ip_address=ip_addr, username=user)
        request = NWMRequest(session_secret=session.session_secret, version=2.0)

        dummy_scheduler_client = DummySchedulerClient(test_successful=False)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)
        sched_resp = SchedulerRequestResponse.factory_init_from_deserialized_json(response.data['scheduler_response'])
        self.assertFalse(sched_resp.success)



