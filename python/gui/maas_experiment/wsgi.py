"""
WSGI config for maas_experiment project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maas_experiment.settings')

# Possible string representations (not accounting for case) of `True`
true_strings = ['true', '1', 't', 'yes']

# Read env var setting whether remote debugging should be turned on
is_remote_debugging = os.environ.get('PYCHARM_REMOTE_DEBUG_ACTIVE', False)

# Since the env var might have been a string representing `True`, account for that
if type(is_remote_debugging) is not bool:
    is_remote_debugging = is_remote_debugging.lower() in true_strings

# If debug is set to be on, and remote debugging server is set to be used, import and start the debugging tool
if is_remote_debugging:
    debug_egg_path_str = os.environ.get('PYCHARM_REMOTE_DEBUG_EGG_PATH', '/pydevd-pycharm.egg')
    import sys
    sys.path.append(debug_egg_path_str)

    import pydevd_pycharm
    debug_port = int(os.environ.get('MAAS_PORTAL_DEBUG_PORT', 55875))
    debug_server = os.environ.get('MAAS_PORTAL_DEBUG_HOST', 'host.docker.internal')

    try:
        pydevd_pycharm.settrace(debug_server, port=debug_port, stdoutToServer=True, stderrToServer=True)
    except Exception as error:
        msg = 'Warning: could not set GUI debugging trace to {} on {} due to {} - {}'
        print(msg.format(debug_server, debug_port, error.__class__.__name__, str(error)))


application = get_wsgi_application()
