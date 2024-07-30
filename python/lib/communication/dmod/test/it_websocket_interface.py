import asyncio
import json
import os
import signal
import unittest
from pathlib import Path

import websockets

from ..test.test_websocket_interface import WebSocketInterfaceTestBase


class IntegrationTestWebSocketInterface(WebSocketInterfaceTestBase):

    def setUp(self):
        super().setUp()
        package_dir_name = os.getenv('PACKAGE_DIR')
        if package_dir_name is None:
            self.package_dir = Path(__file__).resolve().parent.parent.parent
        else:
            self.package_dir = Path(package_dir_name).resolve()

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._basic_listener_subproc_run_code = None
        self.sub_proc: asyncio.subprocess.Process = None

    def tearDown(self):
        super().tearDown()
        if self.sub_proc is not None:
            self._loop.run_until_complete(self._wait_for_shutdown())
        self._loop.stop()

    async def _simple_send_receive(self, send_data: dict, sleep_time: int = 2):
        await asyncio.sleep(sleep_time)
        async with websockets.connect(self.uri, ssl=self._client_ssl_context) as websocket:
            await websocket.send(json.dumps(send_data))
            response = await websocket.recv()
            return response

    async def _wait_for_shutdown(self):
        self.sub_proc.send_signal(signal.SIGTERM)
        s = 0
        code = None
        while s < 5 and code is None:
            await asyncio.sleep(1)
            s += 1
            code = self.sub_proc.returncode
        if code is None:
            self.sub_proc.send_signal(signal.SIGKILL)

    @property
    def basic_listener_subproc_run_code(self) -> str:
        """
        Property lazy getter for string property containing Python code that can be used to start a subprocess running
        the appropriate listener instance for testing, when this needs to be done in a separate process.

        Returns
        -------
        str
            Python code as a string for running a listener service instance in a separate subprocess
        """
        if self._basic_listener_subproc_run_code is None:
            self._basic_listener_subproc_run_code = 'import sys\n'
            self._basic_listener_subproc_run_code += 'from pathlib import Path\n'
            self._basic_listener_subproc_run_code += 'sys.path.insert(0, \'{}\')\n'.format(str(self.package_dir))
            self._basic_listener_subproc_run_code += 'from dmod.communication import EchoHandler\n'
            self._basic_listener_subproc_run_code += 'ssl_dir = Path(\'{}\').resolve()\n'.format(self.test_ssl_dir)
            eh_init_args = 'listen_host=\'{}\', port=\'{}\', ssl_dir=ssl_dir'.format(self.host, self.port)
            self._basic_listener_subproc_run_code += 'eh = EchoHandler({})\n'.format(eh_init_args)
            self._basic_listener_subproc_run_code += 'eh.run()'
        return self._basic_listener_subproc_run_code

    def test_listener_1a(self):
        """
        Execute an EchoHandler instance in a subprocess and test that send works over the websocket, and that it
        responds by echoing the sent data in the reply.

        The point of this test is more to test the overall design for using the listener method than the particular
        implementation for EchoHandler
        """
        self.sub_proc = self._loop.run_until_complete(self.async_run_subproc_from_code(self.basic_listener_subproc_run_code))
        test_data = {"user": "test"}
        response = asyncio.run(asyncio.wait_for(self._simple_send_receive(test_data), timeout=15))
        json_rsp = json.loads(response)
        self.assertDictEqual(test_data, json_rsp)

    def test_listener_1b(self):
        """
        Test to ensure tests in test_listener_1a() will not return false positive by confirming not equal responses are
        recognized as such.
        """
        self.sub_proc = self._loop.run_until_complete(self.async_run_subproc_from_code(self.basic_listener_subproc_run_code))
        test_data = {"user": "test"}
        not_test_data = {"notuser": "nottest"}
        response = asyncio.run(asyncio.wait_for(self._simple_send_receive(test_data), timeout=15))
        json_rsp = json.loads(response)
        self.assertNotEqual(not_test_data, json_rsp)


if __name__ == '__main__':
    unittest.main()
