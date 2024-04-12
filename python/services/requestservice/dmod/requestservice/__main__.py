import argparse
import sys
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
                        type=Path,
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
                        type=Path,
                        default=None)
    parser.add_argument('--data-service-host',
                        help='Set the appropriate hostname for the data service to connect with',
                        dest='data_service_host',
                        default='data-service')
    parser.add_argument('--data-service-port',
                        help='Set the appropriate port value for the data service to connect with',
                        dest='data_service_port',
                        default='3015')
    parser.add_argument('--data-service-ssl-dir',
                        help='Set the ssl directory for data service certs, if not the same as for the request handler',
                        dest='data_service_ssl_dir',
                        type=Path,
                        default=None)
    parser.add_argument('--partitioner-service-host',
                        help='Set the appropriate hostname for the partitioner service to connect with',
                        dest='partitioner_service_host',
                        default='partitioner-service')
    parser.add_argument('--partitioner-service-port',
                        help='Set the appropriate port value for the partitioner service to connect with',
                        dest='partitioner_service_port',
                        default='3014')
    parser.add_argument('--partitioner-service-ssl-dir',
                        help='Set the ssl directory for partitioner service certs, if not the same as for the request handler',
                        dest='partitioner_service_ssl_dir',
                        type=Path,
                        default=None)
    parser.add_argument('--evaluation-service-host',
                        help='Set the appropriate hostname for the evaluation service to connect with',
                        dest='evaluation_service_host',
                        default='localhost')
    parser.add_argument('--evaluation-service-port',
                        help='Set the appropriate port value for the evaluation service to connect with',
                        dest='evaluation_service_port',
                        default='3014')
    parser.add_argument('--evaluation-service-ssl-dir',
                        help='Set the ssl directory for evaluation service certs, '
                             'if not the same as for the request handler',
                        dest='evaluation_service_ssl_dir',
                        default=None)
    parser.add_argument('--pycharm-remote-debug',
                        help='Activate Pycharm remote debugging support',
                        dest='pycharm_debug',
                        action='store_true')
    parser.add_argument('--pycharm-remote-debug-egg',
                        help='Set path to .egg file for Python remote debugger util',
                        dest='remote_debug_egg_path',
                        default='/pydevd-pycharm.egg')
    parser.add_argument('--remote-debug-host',
                        help='Set remote debug host to connect back to debugger',
                        dest='remote_debug_host',
                        default='host.docker.internal')
    parser.add_argument('--remote-debug-port',
                        help='Set remote debug port to connect back to debugger',
                        dest='remote_debug_port',
                        type=int,
                        default=55870)

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


def main():
    args = _handle_args()

    if args.pycharm_debug:
        if args.remote_debug_egg_path == '':
            print('Error: set to debug with Pycharm, but no path to remote debugger egg file provided')
            sys.exit(1)
        if not Path(args.remote_debug_egg_path).exists():
            print('Error: no file at given path to remote debugger egg file "{}"'.format(args.remote_debug_egg_path))
            sys.exit(1)
        sys.path.append(args.remote_debug_egg_path)
        import pydevd_pycharm
        try:
            pydevd_pycharm.settrace(args.remote_debug_host, port=args.remote_debug_port, stdoutToServer=True,
                                    stderrToServer=True)
        except Exception as error:
            msg = 'Warning: could not set debugging trace to {} on {} due to {} - {}'
            print(msg.format(args.remote_debug_host, args.remote_debug_port, error.__class__.__name__, str(error)))

    # Sanity check any provided path arguments
    if args.ssl_dir is not None and not _sanity_check_path_arg(args.ssl_dir, is_directory=True):
        print('Error: provided SSL directory arg ' + args.ssl_dir + ' does not exist or is not valid')
        sys.exit(1)
    if args.cert_path is not None and not _sanity_check_path_arg(args.cert_path):
        print('Error: provided SSL certificate arg ' + args.cert_path + ' does not exist or is not valid')
        sys.exit(1)
    if args.key_path is not None and not _sanity_check_path_arg(args.key_path):
        print('Error: provided SSL private key arg ' + args.key_path + ' does not exist or is not valid')
        sys.exit(1)

    # Init request handler
    handler = RequestService(listen_host=args.host,
                             port=args.port,
                             ssl_dir=args.ssl_dir,
                             use_ssl=False,
                             cert_pem=args.cert_path,
                             priv_key_pem=args.key_path,
                             scheduler_host=args.scheduler_host,
                             scheduler_port=args.scheduler_port,
                             scheduler_ssl_dir=args.scheduler_ssl_dir,
                             data_service_host=args.data_service_host,
                             data_service_port=args.data_service_port,
                             data_service_ssl_dir=args.data_service_ssl_dir,
                             partitioner_host=args.partitioner_service_host,
                             partitioner_port=args.partitioner_service_port,
                             partitioner_ssl_dir=args.partitioner_service_ssl_dir,
                             evaluation_service_host=args.evaluation_service_host,
                             evaluation_service_port=args.evaluation_service_port,
                             evaluation_service_ssl_dir=args.evaluation_service_ssl_dir)
    handler.run()


if __name__ == '__main__':
    main()
