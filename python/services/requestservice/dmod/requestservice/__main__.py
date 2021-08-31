import argparse
import os
from . import name as package_name
from . import RequestService
from pathlib import Path
from socket import gethostname


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--host',
                        help='Set the appropriate listening host name or address value (NOTE: must match SSL cert)',
                        dest='host',
                        default=gethostname())
    parser.add_argument('--port',
                        help='Set the appropriate listening port value',
                        dest='port',
                        default='3012')
    parser.add_argument('--ssl-dir',
                        help='Change the base directory when using SSL certificate and key files with default names',
                        dest='ssl_dir',
                        default=None)
    parser.add_argument('--cert',
                        help='Specify path for a particular SSL certificate file to use',
                        dest='cert_path',
                        default=None)
    parser.add_argument('--key',
                        help='Specify path for a particular SSL private key file to use',
                        dest='key_path',
                        default=None)
    parser.add_argument('--scheduler-host',
                        help='Set the appropriate hostname for the scheduler to connect with',
                        dest='scheduler_host',
                        default='localhost')
    parser.add_argument('--scheduler-port',
                        help='Set the appropriate port value for the scheduler to connect with',
                        dest='scheduler_port',
                        default='3013')
    parser.add_argument('--scheduler-ssl-dir',
                        help='Set the ssl directory for scheduler certs, if not the same as for the request handler',
                        dest='scheduler_ssl_dir',
                        default='3013')
    parser.add_argument('--remote-debug',
                        help='Activate remote debugging (implied when --debug-host or --debug-port)',
                        dest='remote_debug',
                        action="store_true")
    parser.add_argument('--debug-host',
                        help='Set the debugging host when using remote debugging',
                        dest='debug_host',
                        default=None)
    parser.add_argument('--debug-port',
                        help='Set the debugging port when using remote debugging',
                        dest='debug_port',
                        default=None)

    parser.prog = package_name
    return parser.parse_args()


def _sanity_check_path_arg(path_as_str, is_directory=False):
    path_value = Path(path_as_str)
    if not path_value.exists():
        return False
    if is_directory and not path_value.is_dir():
        return False
    if not is_directory and not path_value.is_file():
        return False
    return True


def _activate_remote_debugging(debug_host: str, debug_port: int):
    # This is a list of strings that might be considered as False
    false_options = ['false', '0', 'f', 'no']

    # Read the setting for whether remote debugging should be turned on, again accounting for string instead of bool
    is_remote_debugging = os.environ.get('PYCHARM_REMOTE_DEBUG_ACTIVE', False)
    if type(is_remote_debugging) is not bool:
        is_remote_debugging = is_remote_debugging.lower() not in false_options

    # If debug is set to be on, and remote debugging server is set to be used, import and start the debugging tool
    if is_remote_debugging:
        import pydevd_pycharm
        pydevd_pycharm.settrace(debug_host, port=debug_port, stdoutToServer=True, stderrToServer=True)


def main():
    args = _handle_args()

    is_remote_debug = args.remote_debug
    if is_remote_debug:
        _activate_remote_debugging(debug_host='host.docker.internal' if args.debug_host is None else args.debug_host,
                                   debug_port=55875 if args.debug_port is None else int(args.debug_port))

    # Sanity check any provided path arguments
    if args.ssl_dir is not None and not _sanity_check_path_arg(args.ssl_dir, is_directory=True):
        print('Error: provided SSL directory arg ' + args.ssl_dir + ' does not exist or is not valid')
        exit(1)
    if args.cert_path is not None and not _sanity_check_path_arg(args.cert_path):
        print('Error: provided SSL certificate arg ' + args.cert_path + ' does not exist or is not valid')
        exit(1)
    if args.key_path is not None and not _sanity_check_path_arg(args.key_path):
        print('Error: provided SSL private key arg ' + args.key_path + ' does not exist or is not valid')
        exit(1)

    # Init request handler
    handler = RequestService(listen_host=args.host,
                             port=args.port,
                             ssl_dir=Path(args.ssl_dir),
                             cert_pem=args.cert_path,
                             priv_key_pem=args.key_path,
                             scheduler_host=args.scheduler_host,
                             scheduler_port=args.scheduler_port,
                             scheduler_ssl_dir=Path(args.scheduler_ssl_dir))
    handler.run()


if __name__ == '__main__':
    main()
