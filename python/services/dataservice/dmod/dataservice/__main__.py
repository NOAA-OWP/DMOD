import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)

import argparse
from pathlib import Path
from socket import gethostname

from dmod.scheduler.job import DefaultJobUtilFactory
from dmod.modeldata.data.filesystem_manager import FilesystemDatasetManager
from dmod.modeldata.data.object_store_manager import ObjectStoreDatasetManager
from dmod.core.dataset import DatasetType

from . import name as package_name
from .data_derive_util import DataDeriveUtil
from .dataset_inquery_util import DatasetInqueryUtil
from .dataset_manager_collection import DatasetManagerCollection
from .service import (
    Count,
    DataProvisionManager,
    RequiredDataChecksManager,
    ServiceManager,
    TempDatasetsManager,
    DockerS3FSPluginHelper,
)
from .service_settings import ServiceSettings


def main():
    args = _handle_args()

    if args.pycharm_debug:
        _setup_remote_debugging(args)
    else:
        logging.info("Skipping data service remote debugging setup.")

    listen_host = gethostname() if args.host is None else args.host
    # Flip this here to be less confusing
    use_obj_store = not args.no_obj_store
    # TODO: DataProvisionManager requires object store, so this is currently required. Add functionality to allow usage
    # without object store. fail fast for now.
    assert use_obj_store, "Object store is currently required"

    secrets_dir = Path('/run/secrets')

    # Figure out Redis password, trying for a Docker secret first
    if args.redis_pass_secret is not None:
        redis_pass_secret_file = secrets_dir.joinpath(args.redis_pass_secret)
        redis_pass = redis_pass_secret_file.read_text().strip()
    else:
        redis_pass = args.redis_pass

    # Initialize objects that will be injected and shared by service subsystems
    service_settings = ServiceSettings()
    # Initialize a job util via the default factory, which requires some Redis params
    job_util = DefaultJobUtilFactory.factory_create(redis_host=args.redis_host, redis_port=args.redis_port,
                                                    redis_pass=redis_pass)
    # Datasets creation and access go through this object
    dataset_manager_collection = DatasetManagerCollection()
    data_derive_util = DataDeriveUtil(dataset_manager_collection=dataset_manager_collection)
    dataset_inquery_util = DatasetInqueryUtil(dataset_manager_collection=dataset_manager_collection, derive_util=data_derive_util)

    # TODO: need to adjust arg groupings to allow for this to be cleaned up some
    access_key = (
        None
        if args.obj_store_access_key is None
        else (secrets_dir / args.obj_store_access_key).read_text().strip()
    )
    secret_key = (
        None
        if args.obj_store_secret_key is None
        else (secrets_dir / args.obj_store_secret_key).read_text().strip()
    )
    object_store_dataset_manager = _init_object_store_dataset_manager(
        obj_store_host=args.obj_store_host,
        port=args.obj_store_port,
        access_key=access_key,
        secret_key=secret_key,
    )
    dataset_manager_collection.add(object_store_dataset_manager)

    docker_s3fs_plugin_helper = _init_docker_s3fs_plugin_helper(
        dataset_manager_collection=dataset_manager_collection,
        access_key=access_key,
        secret_key=secret_key,
        settings=service_settings,
    )

    if args.file_dataset_config_dir is not None:
        filesystem_dataset_manager = _init_filesystem_dataset_manager(
            Path(args.file_dataset_config_dir)
        )
        dataset_manager_collection.add(filesystem_dataset_manager)


    # count is used to signal when it is okay to remove temporary datasets
    count = Count()

    # initialize background task objects
    required_data_checks_manager = RequiredDataChecksManager(
        job_util=job_util,
        dataset_manager_collection=dataset_manager_collection,
        count=count,
        dataset_inquery_util=dataset_inquery_util,
    )
    data_provision_manager = DataProvisionManager(job_util=job_util,
                                                  dataset_manager_collection=dataset_manager_collection,
                                                  docker_s3fs_helper=docker_s3fs_plugin_helper,
                                                  data_derive_util=data_derive_util,
                                                  count=count,
                                                  )
    temp_datasets_manager = TempDatasetsManager(dataset_manager_collection=dataset_manager_collection, count=count)

    # Handles websocket communication and async task loop
    service_manager = ServiceManager(
        job_util=job_util,
        listen_host=listen_host,
        port=args.port,
        ssl_dir=Path(args.ssl_dir),
        dataset_manager_collection=dataset_manager_collection,
        dataset_inquery_util=dataset_inquery_util,
    )

    # Setup other required async tasks
    service_manager.add_async_task(required_data_checks_manager.start())
    service_manager.add_async_task(data_provision_manager.start())
    service_manager.add_async_task(temp_datasets_manager.start())

    service_manager.run()


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


def _init_filesystem_dataset_manager(
    file_dataset_config_dir: Path,
) -> FilesystemDatasetManager:
    logging.info(
        "Initializing manager for {} type datasets".format(DatasetType.FILESYSTEM.name)
    )
    mgr = FilesystemDatasetManager(serialized_files_directory=file_dataset_config_dir)
    logging.info(
        "{} initialized with {} existing datasets".format(
            mgr.__class__.__name__, len(mgr.datasets)
        )
    )
    return mgr


def _init_object_store_dataset_manager(
    obj_store_host: str, access_key: str, secret_key: str, port: int = 9000
) -> ObjectStoreDatasetManager:
    host_str = "{}:{}".format(obj_store_host, port)
    logging.info("Initializing object store dataset manager at {}".format(host_str))
    mgr = ObjectStoreDatasetManager(
        obj_store_host_str=host_str, access_key=access_key, secret_key=secret_key
    )
    logging.info(
        "Object store dataset manager initialized with {} existing datasets".format(
            len(mgr.datasets)
        )
    )
    return mgr


def _init_docker_s3fs_plugin_helper(
    dataset_manager_collection: DatasetManagerCollection,
    access_key: str,
    secret_key: str,
    settings: ServiceSettings,
    *args,
    **kwargs
) -> DockerS3FSPluginHelper:
    s3fs_url_proto = settings.s3fs_url_protocol
    s3fs_url_host = settings.s3fs_url_host
    s3fs_url_port = settings.s3fs_url_port
    if s3fs_url_host is not None:
        s3fs_helper_url = "{}://{}:{}/".format(
            s3fs_url_proto, s3fs_url_host, s3fs_url_port
        )
    else:
        s3fs_helper_url = None

    docker_s3fs_helper = DockerS3FSPluginHelper(
        service_manager=dataset_manager_collection,
        obj_store_access=access_key,
        obj_store_secret=secret_key,
        docker_image_name=settings.s3fs_vol_image_name,
        docker_image_tag=settings.s3fs_vol_image_tag,
        docker_networks=[settings.s3fs_helper_network],
        docker_plugin_alias=settings.s3fs_plugin_alias,
        obj_store_url=s3fs_helper_url,
        *args,
        **kwargs
    )
    return docker_s3fs_helper



if __name__ == '__main__':
    main()
