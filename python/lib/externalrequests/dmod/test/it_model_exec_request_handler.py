import asyncio
import datetime
import unittest
import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional
from dmod.access import RedisBackendSessionManager
from dmod.communication import NWMRequest, NWMRequestResponse, SchedulerClient, SchedulerRequestMessage, \
    SchedulerRequestResponse, InitRequestResponseReason
from dmod.externalrequests import ModelExecRequestHandler
from ..test import FailureTestingAuthUtil, SucceedTestAuthUtil


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
        if self.test_successful:
            data = {'job_id': self.next_job_id, 'output_data_id': '00000000-0000-0000-0000-000000000000'}
        else:
            data = None
        return SchedulerRequestResponse(success=self.test_successful, reason='Testing Stub', message='Testing stub',
                                        data=data)

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

    _TEST_ENV_FILE_BASENAME = ".test_env"

    @classmethod
    def find_project_root_directory(cls, current_directory: Optional[Path]) -> Optional[Path]:
        """
        Given a directory (with ``None`` implying the current directory) assumed to be at or under this project's root,
        find the project root directory.

        This implementation attempts to find a directory having both a ``.git/`` child directory and a ``.env`` file.

        Parameters
        ----------
        current_directory

        Returns
        -------
        Optional[Path]
            The project root directory, or ``None`` if it fails to find it.
        """
        abs_root = Path(current_directory.absolute().root)
        while current_directory.absolute() != abs_root:
            if not current_directory.is_dir():
                current_directory = current_directory.parent
                continue
            git_sub_dir = current_directory.joinpath('.git')
            child_env_file = current_directory.joinpath('.env')
            if git_sub_dir.exists() and git_sub_dir.is_dir() and child_env_file.exists() and child_env_file.is_file():
                return current_directory
            current_directory = current_directory.parent
        return None

    @classmethod
    def source_env_files(cls, env_file_basename: str):
        current_dir = Path().absolute()

        # Find the global .test_env file from project root, and source
        proj_root = cls.find_project_root_directory(current_dir)
        if proj_root is None:
            raise RuntimeError("Error: unable to find project root directory for integration testing.")

        global_test_env = proj_root.joinpath(env_file_basename)
        if global_test_env.exists():
            load_dotenv(dotenv_path=str(global_test_env.absolute()))

        # Also, search for any other .test_env files, but only source if they are in the same directory as this file
        this_test_file_parent_directory = Path(__file__).parent.absolute()
        for test_env_file in proj_root.glob('**/' + env_file_basename):
            if test_env_file.parent.absolute() == this_test_file_parent_directory:
                load_dotenv(dotenv_path=str(test_env_file))
                # Also, since there can be only one, go ahead and return here
                break

    @classmethod
    def source_env_property(cls, env_var_name: str):
        value = os.getenv(env_var_name, None)
        if value is None:
            cls.source_env_files(cls._TEST_ENV_FILE_BASENAME)
            value = os.getenv(env_var_name, None)
        return value

    def __init__(self, methodName='runTest'):
        super().__init__(methodName=methodName)
        self._redis_test_pass = None
        self._redis_test_port = None

    @property
    def redis_test_pass(self):
        if not self._redis_test_pass:
            self._redis_test_pass = self.source_env_property('IT_REDIS_CONTAINER_PASS')
        return self._redis_test_pass

    @property
    def redis_test_port(self):
        if not self._redis_test_port:
            self._redis_test_port = self.source_env_property('IT_REDIS_CONTAINER_HOST_PORT')
        return self._redis_test_port

    def setUp(self) -> None:

        self._user_1 = 'test_user_1'
        self._user_2 = 'test_user_2'
        self._user_3 = 'test_user_3'
        self._session_ip_1 = '127.0.0.2'
        self._session_ip_2 = '127.0.0.3'
        self._session_ip_3 = '127.0.0.4'

        self._config_data_id_1 = '1'
        self._config_data_id_2 = '2'
        self._config_data_id_3 = '3'

        self.session_manager = RedisBackendSessionManager(redis_host='127.0.0.1',
                                                          redis_port=self.redis_test_port,
                                                          redis_pass=self.redis_test_pass)

        self.fail_authorizer = FailureTestingAuthUtil()
        self.success_authorizer = SucceedTestAuthUtil()

        # TODO: set these correctly
        self.scheduler_host = '127.0.0.1'
        self.scheduler_port = 19380
        self.scheduler_ssl_dir = Path('./ssl')

        #self._handler = None
        self.handler = ModelExecRequestHandler(session_manager=self.session_manager,
                                               authorizer=self.success_authorizer,
                                               service_host=self.scheduler_host,
                                               service_port=self.scheduler_port,
                                               service_ssl_dir=self.scheduler_ssl_dir)

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
        config_data_id = self._config_data_id_1
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

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
        config_data_id = self._config_data_id_1
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

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
        config_data_id = self._config_data_id_1
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

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
        config_data_id = self._config_data_id_2
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

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
        config_data_id = self._config_data_id_2
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

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
        config_data_id = self._config_data_id_2
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

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
        config_data_id = self._config_data_id_2
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

        dummy_scheduler_client = DummySchedulerClient(test_successful=True)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)

        data_key = NWMRequestResponse.get_scheduler_response_key()
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
        config_data_id = self._config_data_id_2
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

        dummy_scheduler_client = DummySchedulerClient(test_successful=True)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)

        data_key = NWMRequestResponse.get_scheduler_response_key()
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
        config_data_id = self._config_data_id_3
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

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
        config_data_id = self._config_data_id_3
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

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
        config_data_id = self._config_data_id_3
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

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
        config_data_id = self._config_data_id_3
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

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
        config_data_id = self._config_data_id_3
        request = NWMRequest(config_data_id=config_data_id, session_secret=session.session_secret)

        dummy_scheduler_client = DummySchedulerClient(test_successful=False)
        self.handler._scheduler_client = dummy_scheduler_client

        response = asyncio.run(self.handler.handle_request(request=request), debug=True)
        sched_resp = SchedulerRequestResponse.factory_init_from_deserialized_json(response.data['scheduler_response'])
        self.assertFalse(sched_resp.success)
