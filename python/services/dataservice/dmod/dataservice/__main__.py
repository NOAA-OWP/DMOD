import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


from dmod.modeldata.data.object_store_manager import ObjectStoreDatasetManager
from dmod.scheduler.job import DefaultJobUtilFactory

from .data_derive_util import DataDeriveUtil
from .dataset_inquery_util import DatasetInqueryUtil
from .dataset_manager_collection import DatasetManagerCollection
from .service import (
    ActiveOperationTracker,
    DataProvisionManager,
    DockerS3FSPluginHelper,
    RequiredDataChecksManager,
    ServiceManager,
    TempDataTaskManager,
)
from .service_settings import ServiceSettings, debug_settings, service_settings


def main():
    settings = service_settings()

    if settings.pycharm_debug:
        _setup_remote_debugging()
    else:
        logging.info("Skipping data service remote debugging setup.")

    # Initialize objects that will be injected and shared by service subsystems
    # Initialize a job util via the default factory, which requires some Redis params
    job_util = DefaultJobUtilFactory.factory_create(
        redis_host=settings.redis_host,
        redis_port=settings.redis_port,
        redis_pass=settings.redis_pass,
    )
    # Datasets creation and access go through this object
    dataset_manager_collection = DatasetManagerCollection()
    data_derive_util = DataDeriveUtil(
        dataset_manager_collection=dataset_manager_collection
    )
    dataset_inquery_util = DatasetInqueryUtil(
        dataset_manager_collection=dataset_manager_collection,
        derive_util=data_derive_util,
    )

    object_store_dataset_manager = _init_object_store_dataset_manager(
        obj_store_host=settings.object_store_host,
        port=settings.object_store_port,
        access_key=settings.object_store_exec_user_name,
        secret_key=settings.object_store_exec_user_passwd,
    )
    dataset_manager_collection.add(object_store_dataset_manager)

    docker_s3fs_plugin_helper = _init_docker_s3fs_plugin_helper(
        dataset_manager_collection=dataset_manager_collection,
        access_key=settings.object_store_exec_user_name,
        secret_key=settings.object_store_exec_user_passwd,
        settings=settings,
    )

    # TODO: Add functionality to allow usage with other backend storage providers

    # count is used to signal when it is okay to remove temporary datasets
    count = ActiveOperationTracker()

    # initialize background task objects
    required_data_checks_manager = RequiredDataChecksManager(
        job_util=job_util,
        dataset_manager_collection=dataset_manager_collection,
        checks_underway_tracker=count,
        dataset_inquery_util=dataset_inquery_util,
    )
    data_provision_manager = DataProvisionManager(
        job_util=job_util,
        dataset_manager_collection=dataset_manager_collection,
        docker_s3fs_helper=docker_s3fs_plugin_helper,
        data_derive_util=data_derive_util,
        provision_underway_tracker=count,
    )
    temp_datasets_manager = TempDataTaskManager(
        dataset_manager_collection=dataset_manager_collection,
        safe_to_exec_tracker=count,
    )

    # Handles websocket communication and async task loop
    service_manager = ServiceManager(
        job_util=job_util,
        listen_host=settings.host,
        port=settings.port,
        ssl_dir=settings.ssl_dir,
        dataset_manager_collection=dataset_manager_collection,
        dataset_inquery_util=dataset_inquery_util,
    )

    # Setup other required async tasks
    service_manager.add_async_task(required_data_checks_manager.start())
    service_manager.add_async_task(data_provision_manager.start())
    service_manager.add_async_task(temp_datasets_manager.start())

    service_manager.run()


def _setup_remote_debugging():
    settings = debug_settings()
    logging.info("Preparing remote debugging connection for data service.")
    if not settings.pycharm_remote_debug_egg.exists():
        print(
            f'Error: no file at given path to remote debugger egg file "{settings.pycharm_remote_debug_egg!s}"',
            file=sys.stderr,
        )
        sys.exit(1)
    sys.path.append(str(settings.pycharm_remote_debug_egg))
    import pydevd_pycharm

    try:
        pydevd_pycharm.settrace(
            settings.remote_debug_host,
            port=settings.remote_debug_port,
            stdoutToServer=True,
            stderrToServer=True,
        )
    except Exception as error:
        msg = "Warning: could not set debugging trace to {} on {} due to {} - {}"
        print(
            msg.format(
                settings.remote_debug_host,
                settings.remote_debug_port,
                error.__class__.__name__,
                str(error),
            ),
            file=sys.stderr,
        )


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
    **kwargs,
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
        **kwargs,
    )
    return docker_s3fs_helper


if __name__ == "__main__":
    main()
