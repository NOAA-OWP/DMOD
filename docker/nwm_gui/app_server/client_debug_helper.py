import sys
import os
sys.path.append('/pydevd-pycharm.egg')
import pydevd_pycharm
import dmod.client
from dmod.client.__main__ import main

gui_debug_port = int(os.environ.get('MAAS_PORTAL_DEBUG_PORT', 55875))
debug_port = gui_debug_port + 1
debug_server = 'host.docker.internal'

# Support an ENV var "NO_DEBUG" for not doing this
skip_debug = os.getenv('NO_DEBUG')

try:
    if skip_debug is None:
        pydevd_pycharm.settrace(debug_server, port=debug_port, stdoutToServer=True, stderrToServer=True)
    main()
except Exception as error:
    msg = 'Warning: could not set GUI debugging trace to {} on {} due to {} - {}'
    print(msg.format(debug_server, debug_port, error.__class__.__name__, str(error)))
