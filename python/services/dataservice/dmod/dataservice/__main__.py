import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)

import argparse
from . import name as package_name
from .service import ServiceManager
from .service_settings import ServiceSettings
from dmod.scheduler.job import DefaultJobUtilFactory
from pathlib import Path
from socket import gethostname


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--host',
                        help='Set the appropriate listening host name or address value (NOTE: must match SSL cert)',
                        dest='host',
                        default=None)
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
    parser.add_argument('--file-dataset-config-dir',
                        help='Path to directory containing serialized, filesystem-based Dataset objects',
                        dest='file_dataset_config_dir',
                        default=None)
    parser.add_argument('--object-store-host',
                        help='Set hostname for connection to object store',
                        dest='obj_store_host',
                        default='minio-proxy')
    parser.add_argument('--object-store-port',
                        help='Set port for connection to object store',
                        dest='obj_store_port',
                        default=9000)
    parser.add_argument('--object-store-user-secret-name',
                        help='Set name of the Docker secret containing the object store user access key',
                        dest='obj_store_access_key',
                        default=None)
    parser.add_argument('--object-store-passwd-secret-name',
                        help='Set name of the Docker secret containing the object store user secret key',
                        dest='obj_store_secret_key',
                        default=None)
    parser.add_argument('--no-object-store',
                        help='Disable object store functionality and do not try to connect to one',
                        dest='no_obj_store',
                        action='store_true',
                        default=False)
    parser.add_argument('--redis-host',
                        help='Set the host value for making Redis connections',
                        dest='redis_host',
                        default='myredis')
    parser.add_argument('--redis-port',
                        help='Set the port value for making Redis connections',
                        dest='redis_port',
                        default=6379)
    parser.add_argument('--redis-pass',
                        help='Set the password value for making Redis connections',
                        dest='redis_pass',
                        default='noaaOwp')
    parser.add_argument('--redis-pass-secret-name',
                        help='Set the name of the Docker secret containing the password for Redis connections',
                        dest='redis_pass_secret',
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
                        default=55871)

    parser.prog = package_name
    return parser.parse_args()

def _setup_remote_debugging(args: argparse.Namespace):
    logging.info("Preparing remote debugging connection for data service.")
    if args.remote_debug_egg_path == '':
        print('Error: set to debug with Pycharm, but no path to remote debugger egg file provided')
        exit(1)
    if not Path(args.remote_debug_egg_path).exists():
        print('Error: no file at given path to remote debugger egg file "{}"'.format(args.remote_debug_egg_path))
        exit(1)
    import sys
    sys.path.append(args.remote_debug_egg_path)
    import pydevd_pycharm
    try:
        pydevd_pycharm.settrace(args.remote_debug_host, port=args.remote_debug_port, stdoutToServer=True,
                                stderrToServer=True)
    except Exception as error:
        msg = 'Warning: could not set debugging trace to {} on {} due to {} - {}'
        print(msg.format(args.remote_debug_host, args.remote_debug_port, error.__class__.__name__, str(error)))

def main():
    args = _handle_args()

    if args.pycharm_debug:
        _setup_remote_debugging(args)
    else:
        logging.info("Skipping data service remote debugging setup.")

    listen_host = gethostname() if args.host is None else args.host
    # Flip this here to be less confusing
    use_obj_store = not args.no_obj_store

    secrets_dir = Path('/run/secrets')

    # Figure out Redis password, trying for a Docker secret first
    if args.redis_pass_secret is not None:
        redis_pass_secret_file = secrets_dir.joinpath(args.redis_pass_secret)
        redis_pass = redis_pass_secret_file.read_text().strip()
    else:
        redis_pass = args.redis_pass

    service_settings = ServiceSettings()

    # Initialize a job util via the default factory, which requires some Redis params
    job_util = DefaultJobUtilFactory.factory_create(redis_host=args.redis_host, redis_port=args.redis_port,
                                                    redis_pass=redis_pass)

    # Initiate a service manager WebsocketHandler implementation for primary messaging and async task loops
    service_manager = ServiceManager(job_util=job_util, listen_host=listen_host, port=args.port,
                                     ssl_dir=Path(args.ssl_dir), settings=service_settings)

    # If we are set to use the object store ...
    if use_obj_store:
        # TODO: need to adjust arg groupings to allow for this to be cleaned up some
        access_key_file = None if args.obj_store_access_key is None else secrets_dir.joinpath(args.obj_store_access_key)
        secret_key_file = None if args.obj_store_secret_key is None else secrets_dir.joinpath(args.obj_store_secret_key)
        service_manager.init_object_store_dataset_manager(obj_store_host=args.obj_store_host,
                                                          port=args.obj_store_port,
                                                          access_key=access_key_file.read_text().strip(),
                                                          secret_key=secret_key_file.read_text().strip())
    if args.file_dataset_config_dir is not None:
        service_manager.init_filesystem_dataset_manager(Path(args.file_dataset_config_dir))

    # Setup other required async tasks
    service_manager.add_async_task(service_manager.manage_required_data_checks())
    service_manager.add_async_task(service_manager.manage_data_provision())
    service_manager.add_async_task(service_manager.manage_temp_datasets())

    service_manager.run()


if __name__ == '__main__':
    main()
