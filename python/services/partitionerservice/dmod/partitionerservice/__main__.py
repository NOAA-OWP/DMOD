import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)

import sys
import argparse
from . import name as package_name
from .service import ServiceManager
from dmod.scheduler.job import DefaultJobUtilFactory
from dmod.externalrequests.maas_request_handlers import DataServiceClient
from dmod.communication import WebSocketClient
from pathlib import Path
from socket import gethostname


def _handle_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--listen-host',
                        help='Set the appropriate listening host name or address value (NOTE: must match SSL cert)',
                        dest='listen_host',
                        default=gethostname())
    parser.add_argument('--listen-port',
                        '-l',
                        help='Port that the service listens on for incoming websocket connections',
                        dest='listen_port',
                        default=3014)
    parser.add_argument('--partitioner-image',
                        '-i',
                        help='Name of the constructed Docker image in which the partitioner executable is run',
                        dest='partitioner_image',
                        default='ngen-partitioner')
    parser.add_argument('--image-tag',
                        '-t',
                        help='Image tag/version to use for partitioner image',
                        dest='image_tag',
                        default='latest')
    parser.add_argument('--ssl-dir',
                        help='Change the base directory when using SSL certificate and key files with default names',
                        dest='ssl_dir',
                        default='/ssl/partitioner-service')
    parser.add_argument('--cert',
                        help='Specify path for a particular SSL certificate file to use',
                        dest='cert_path',
                        default=None)
    parser.add_argument('--key',
                        help='Specify path for a particular SSL private key file to use',
                        dest='key_path',
                        default=None)
    parser.add_argument('--public-registry',
                        '-p',
                        help='Use public Docker image registry instead of private',
                        dest='use_public',
                        action='store_true')
    parser.add_argument('--docker-registry',
                        '-r',
                        help='Private Docker image registry to use',
                        dest='docker_registry',
                        default='127.0.0.1:5000')
    parser.add_argument('--hydrofabrics-dir',
                        help='Local root directory for hydrofabric data and datasets.',
                        dest='hydrofabrics_dir',
                        default='/hydrofabrics_data')
    parser.add_argument('--data-service-host',
                        help='Set the appropriate hostname for the data service to connect with',
                        dest='data_service_host',
                        default='localhost')
    parser.add_argument('--data-service-port',
                        help='Set the appropriate port value for the data service to connect with',
                        dest='data_service_port',
                        default='3014')
    parser.add_argument('--data-service-ssl-dir',
                        help='Set the ssl directory for data service certs, if not the same as for the request handler',
                        dest='data_service_ssl_dir',
                        default=None)
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
                        default=55873)
    parser.prog = package_name
    return parser.parse_args()


def _process_path(files_dir_arg: str, file_name: str):
    if not files_dir_arg:
        return file_name
    else:
        return files_dir_arg + "/" + file_name


def main():
    args = _handle_args()
    image = args.partitioner_image + ":" + args.image_tag

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

    if not args.use_public:
        image = args.docker_registry + "/" + image

    secrets_dir = Path('/run/secrets')

    # Figure out Redis password, trying for a Docker secret first
    if args.redis_pass_secret is not None:
        redis_pass_secret_file = secrets_dir.joinpath(args.redis_pass_secret)
        redis_pass = redis_pass_secret_file.read_text().strip()
    else:
        redis_pass = args.redis_pass

    # Initialize a job util via the default factory, which requires some Redis params
    job_util = DefaultJobUtilFactory.factory_create(redis_host=args.redis_host, redis_port=args.redis_port,
                                                    redis_pass=redis_pass)

    data_client = DataServiceClient(transport_client=WebSocketClient(endpoint_host=args.data_service_host,
                                                                     endpoint_port=args.data_service_port,
                                                                     capath=args.data_service_ssl_dir))

    service = ServiceManager(port=args.listen_port, listen_host=args.listen_host, ssl_dir=Path(args.ssl_dir),
                             cert_pem=args.cert_path, priv_key_pem=args.key_path, image_name=image, job_util=job_util,
                             data_client=data_client, hydrofabrics_dir=args.hydrofabrics_dir)

    # Setup other required async tasks
    service.add_async_task(service.manage_job_partitioning())

    service.run()


if __name__ == '__main__':
    main()
