import asyncio
import hashlib
import json
import os
import signal
import ssl
import sys
import unittest
from ..communication.message import MessageEventType
from dmod.communication import ModelExecRequest, SessionInitMessage
from dmod.communication.dataset_management_message import MaaSDatasetManagementMessage
from ..communication.websocket_interface import NoOpHandler
from pathlib import Path
from socket import gethostname
import websockets


class WebSocketInterfaceTestBase(unittest.TestCase):

    _current_dir = Path(__file__).resolve().parent
    _json_schemas_dir = _current_dir.parent.joinpath('communication', 'schemas')
    _valid_request_json_file = _json_schemas_dir.joinpath('request.json')
    _valid_auth_json_file = _json_schemas_dir.joinpath('auth.json')

    @staticmethod
    def run_coroutine(coroutine):
        """
        Helper function to run asynchronous coroutines.

        :param coroutine: The asynchronous coroutine to run
        :return: The result of the asynchronous coroutine
        """
        return asyncio.get_event_loop().run_until_complete(coroutine)

    @staticmethod
    async def async_run_subproc_from_code(sub_proc_code: str) -> asyncio.subprocess.Process:
        """
        Helper function for creating and running a Python subprocess executing the given string as Python code.

        Parameters
        ----------
        sub_proc_code: str
            Python code to execute in the subprocess

        Returns
        -------
        The started subprocess object
        """
        return await asyncio.create_subprocess_exec(sys.executable, '-c', sub_proc_code, stdout=asyncio.subprocess.PIPE)

    def _dir_contains(self, directory: Path, file_names: list, files_are_sub_dirs: bool = False):
        if isinstance(file_names, list):
            for file_name_str in file_names:
                child = directory.joinpath(file_name_str)
                if not child.exists():
                    return False
                if files_are_sub_dirs and not child.is_dir():
                    return False
        return True

    def find_proj_root(self, descendant: Path, file_names: list, dir_names: list, max_levels: int = 25):
        """
        Try to find the project root directory based on expected lists of files and/or directories it contains,
        recursively ascending from a given starting directory.

        Given a starting file assumed to be a descendent of the project root directory (or the root directory itself),
        examine that file to see if it is the project root.  Determine this by checking if it is a directory with all of
        a specified list of child files and or child directories.  If it is the project root, return it; if not,
        recursively perform the same steps on the file's parent directory, until this has been done for a maximum number
        of levels or the filesystem root is reached (in which case ``None`` is returned).

        Parameters
        ----------
        descendant : Path
            A starting point to being searching from, expected to either be or be a descendent of the sought directory

        file_names : list of str
            A list of the names of non-directory child files that are expected in the sought directory, as a means of
            identifying it

        dir_names : list of str
            A list of the names of child directories that are expected in the sought directory, as a means of
            identifying it

        max_levels : int
            A limit on the number of levels that should be traverse before giving up, with a value less than 1
            indicating the search should proceed until the root of the filesystem/drive.

        Returns
        -------
        Path
            The sought project root directory if it can be found, or ``None``
        """
        count_test_files = len(file_names) if isinstance(file_names, list) else 0
        count_test_files += len(dir_names) if isinstance(dir_names, list) else 0
        if count_test_files == 0:
            raise RuntimeError("_find_proj_root() must be given at least one expected file/dir in project root")
        levels = 0
        if descendant.is_dir() and self._dir_contains(descendant, file_names) and self._dir_contains(descendant, dir_names, True):
            return descendant
        for d in descendant.parents:
            if max_levels < 1 or levels < max_levels:
                levels += 1
            else:
                break
            if self._dir_contains(d, file_names) and self._dir_contains(d, dir_names, True):
                return d
        return None

    def setUp(self):
        test_dir_name = os.getenv('TEST_SSL_CERT_DIR')
        # First, try the old way
        if test_dir_name is None:
            try:
                self.test_ssl_dir = Path(__file__).resolve().parent.parent.parent.joinpath('ssl')
            except:
                self.test_ssl_dir = None
        else:
            self.test_ssl_dir = Path(test_dir_name).resolve()

        # But if this isn't a valid, search the new way
        if self.test_ssl_dir is None or not self.test_ssl_dir.exists() or not self.test_ssl_dir.is_dir():
            # Find the project root to then get the SSL dir
            expected_files = ['.gitignore', 'example.env']
            expected_sub_dirs = ['.git', 'ssl']
            proj_root = self.find_proj_root(Path(__file__).resolve().parent, expected_files, expected_sub_dirs)
            if proj_root is None:
                msg = 'Unable to find project root with expected files [{}] and sub dirs [{}]; cannot locate SSL dir'
                raise RuntimeError(msg.format(str(expected_files), str(expected_sub_dirs)))
            self.test_ssl_dir = proj_root.joinpath('ssl').joinpath('local')

        self._client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._client_ssl_context.load_verify_locations(str(self.test_ssl_dir.joinpath('certificate.pem')))

        self.port = '3012'
        self.host = gethostname()

        self.uri = 'wss://{}:'.format(self.host) + self.port

    def tearDown(self):
        pass


class TestWebSocketInterface(WebSocketInterfaceTestBase):

    def setUp(self):
        super().setUp()

        self.example_request_data = []
        self.example_request_data.append({"username": "someone", "user_secret": "something"})

        self.example_request_data.append({
            "model": {
                "nwm": {
                    "allocation_paradigm": "ROUND_ROBIN",
                    "config_data_id": "1",
                    "cpu_count": 2,
                    "data_requirements": [{
                        "category": "CONFIG",
                        "is_input": True,
                        "domain": {"data_format": "NWM_CONFIG", "continuous": [],
                                                      "discrete": [{"variable": "data_id", "values": ["1"]}]}}]
                }
            },
            "session-secret": "3fc9b689459d738f8c88a3a48aa9e33542016b7a4052e001aaa536fca74813cb",
        })

        self.example_request_data.append(
            {'action': 'LIST_ALL', 'read_only': False, 'pending_data': False,
             'session_secret': '409770e8cc4bfd10e276b98aff1d3817c8848e1747b3ad2e13f88ca45252e67e'})

        self._parse_return_offset = 42

        self.session_secret = hashlib.sha256('blah'.encode('utf-8')).hexdigest()
        self.request_handler = NoOpHandler(listen_host=self.host, port=self.port, ssl_dir=self.test_ssl_dir)

    def test__deserialize_message_0_a(self):
        """
        Test that example 0 parses to a ::class:`SessionInitMessage`.
        """
        ex_indx = 0
        data = self.example_request_data[ex_indx]
        event = MessageEventType.SESSION_INIT
        expected_request_type = SessionInitMessage

        request = self.request_handler._deserialized_message(message_data=data)
        self.assertIsInstance(request, expected_request_type)

    def test__deserialize_message_1_a(self):
        """
        Test that example 1 parses to a ::class:`ModelExecRequest`.
        """
        ex_indx = 1
        data = self.example_request_data[ex_indx]
        event = MessageEventType.MODEL_EXEC_REQUEST
        expected_request_type = ModelExecRequest

        request = self.request_handler._deserialized_message(message_data=data)
        self.assertIsInstance(request, expected_request_type)

    def test__deserialize_message_2_a(self):
        """
        Test that example 2 parses to a ::class:`MaaSDatasetManagementMessage`.
        """
        ex_indx = 2
        data = self.example_request_data[ex_indx]
        event = MessageEventType.DATASET_MANAGEMENT
        expected_request_type = MaaSDatasetManagementMessage

        request = self.request_handler._deserialized_message(message_data=data)
        self.assertIsInstance(request, expected_request_type)

    def test__deserialize_message_2_b(self):
        """
        Test that example 2 parses to a ::class:`MaaSDatasetManagementMessage`, even with no ``event_type`` param passed.
        """
        ex_indx = 2
        data = self.example_request_data[ex_indx]
        expected_request_type = MaaSDatasetManagementMessage

        request = self.request_handler._deserialized_message(message_data=data)
        self.assertIsInstance(request, expected_request_type)

    def test__parse_request_type_0_a(self):
        """
        Test that example 0 parses the expected ``SESSION_INIT`` ::class:`MessageEventType`.
        """
        ex_indx = 0
        data = self.example_request_data[ex_indx]
        expected_event = MessageEventType.SESSION_INIT

        event_type, errors = self.request_handler._parse_request_type(data=data, check_for_auth=True)

        self.assertEqual(expected_event, event_type)

    # Skip unless/until we re-add formal validators for all types
    @unittest.skip
    def test_parse_request_type_0_b(self):
        """
        Test that example 0 parses the expected ``INVALID`` ::class:`MessageEventType` if modified to be invalid.

        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        with a modified, too short username
        """
        ex_indx = 0
        data = self.example_request_data[ex_indx]
        expected_event = MessageEventType.INVALID

        data['username'] = 'short'
        event_type, errors = self.request_handler._parse_request_type(data=data, check_for_auth=False)

        self.assertEqual(expected_event, event_type)

    # Skip unless/until we re-add formal validators for all types
    @unittest.skip
    def test_parse_request_type_0_c(self):
        """
        Test that example 0 parses the expected ``INVALID`` ::class:`MessageEventType` if modified to be invalid.

        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        with a modified, too short user_secret
        """
        ex_indx = 0
        data = self.example_request_data[ex_indx]
        expected_event = MessageEventType.INVALID

        data['user_secret'] = 'short'
        event_type, errors = self.request_handler._parse_request_type(data=data, check_for_auth=False)

        self.assertEqual(expected_event, event_type)

    def test_parse_request_type_0_e(self):
        """
        Test that example 0 parses the expected ``INVALID`` ::class:`MessageEventType` if modified to be invalid.

        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        modified to be missing username
        """
        ex_indx = 0
        data = self.example_request_data[ex_indx]
        expected_event = MessageEventType.INVALID

        data.pop('username')
        event_type, errors = self.request_handler._parse_request_type(data=data, check_for_auth=True)

        self.assertEqual(expected_event, event_type)

    def test_parse_request_type_0_f(self):
        """
        Test that example 0 parses the expected ``INVALID`` ::class:`MessageEventType` if modified to be invalid.

        Test the parse_request_type method of the RequestHandler on the basic test AUTHENTICATION request example, but
        modified to be missing user_secret
        """
        ex_indx = 0
        data = self.example_request_data[ex_indx]
        expected_event = MessageEventType.INVALID

        data.pop('user_secret')
        event_type, errors = self.request_handler._parse_request_type(data=data, check_for_auth=True)

        self.assertEqual(expected_event, event_type)

    def test__parse_request_type_1_a(self):
        """
        Test that example 1 parses the expected ``MODEL_EXEC_REQUEST`` ::class:`MessageEventType`.
        """
        ex_indx = 1
        data = self.example_request_data[ex_indx]
        expected_event = MessageEventType.MODEL_EXEC_REQUEST

        event_type, errors = self.request_handler._parse_request_type(data=data, check_for_auth=False)
        self.assertEqual(expected_event, event_type)

    # Skip unless/until we re-add formal validators for all types
    @unittest.skip
    def test_parse_request_type_1_b(self):
        """
        Test that example 1 parses the expected ``INVALID`` ::class:`MessageEventType` if altered to be invalid.

        Test the parse_request_type method of the RequestHandler on the basic test JOB request example, but with a
        modified invalid session-secret.
        """
        ex_indx = 1
        data = self.example_request_data[ex_indx]
        expected_event = MessageEventType.INVALID

        data['session-secret'] = 'some_string'
        event_type, errors = self.request_handler._parse_request_type(data=data, check_for_auth=False)

        self.assertEqual(event_type, expected_event)

    def test_parse_request_type_1_c(self):
        """
        Test that example 1 parses the expected ``INVALID`` ::class:`MessageEventType` if altered to be invalid.

        Test the parse_request_type method of the RequestHandler on the basic test JOB request example, but modified
        to be without model.
        """
        ex_indx = 1
        data = self.example_request_data[ex_indx]
        expected_event = MessageEventType.INVALID

        data.pop('model')
        event_type, errors = self.request_handler._parse_request_type(data=data, check_for_auth=False)

        self.assertEqual(event_type, expected_event)

    def test__parse_request_type_2_a(self):
        """
        Test that example 2 parses the expected ``DATASET_MANAGEMENT`` ::class:`MessageEventType`.
        """
        ex_indx = 2
        data = self.example_request_data[ex_indx]
        expected_event = MessageEventType.DATASET_MANAGEMENT

        event_type, errors = self.request_handler._parse_request_type(data=data, check_for_auth=False)
        self.assertEqual(expected_event, event_type)


if __name__ == '__main__':
    unittest.main()
