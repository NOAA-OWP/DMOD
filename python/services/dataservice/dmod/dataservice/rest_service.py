import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dmod.core.dataset import DatasetType
from dmod.dataservice.dataset_inquery_util import DatasetInqueryUtil
from dmod.dataservice.dataset_manager_collection import DatasetManagerCollection
from dmod.dataservice.service import (
    ActiveOperationTracker,
    DataProvisionManager,
    DockerS3FSPluginHelper,
    RequiredDataChecksManager,
    ServiceManager,
    TempDataTaskManager,
)
from dmod.dataservice.service_settings import ServiceSettings, service_settings
from dmod.modeldata.data.object_store_manager import ObjectStoreDatasetManager
from dmod.scheduler.job import JobUtil
from fastapi import Depends, FastAPI, Request, UploadFile, WebSocket, status
from fastapi.responses import JSONResponse
from typing_extensions import Annotated

from . import _injectable as dep
from ._version import __version__ as version
from .errors import Error as Errors
from .exceptions import ErrorResponseException
from .models import Error
from .service_settings import service_settings

app = FastAPI(
    title="DMOD Data Service",
    version=version,
    terms_of_service="https://github.com/NOAA-OWP/DMOD/blob/4677879c07bc6534b4aa3fd434804b51dc579ace/TERMS.md",
    license_info={
        "name": "USDOC",
        "url": "https://raw.githubusercontent.com/NOAA-OWP/owp-open-source-project-template/ed3e23a203153c4e00c4f95893f5e45631620481/LICENSE",
    },
)


# TODO: add feature flags for toggling background tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This coroutine conducts service setup and tear down tasks. This includes setting up and starting
    background tasks. It is split into two logical sections divided by an empty `yield` statement.
    Everything before the `yeild` statement runs prior to the server startup. Everything after the
    yield statement runs _during_ server shutdown.
    """
    # NOTE: for better or worse, this function is and probably will remain very procedural. The goal
    # is to err on the side of clarity and locality. That likely will mean this function is a
    # little long, but crucially does not require jumping to several different files to
    # understand what is going on.
    settings = service_settings()

    # Initialize objects that will be injected and shared by service subsystems
    # Initialize a job util via the default factory, which requires some Redis params
    job_util = dep.job_util(settings)

    # Datasets creation and access go through this object
    dataset_manager_collection = dep.dataset_manager_collection()

    # add dataset managers to manager collection
    object_store_dataset_manager = _init_object_store_dataset_manager(
        obj_store_host=settings.object_store_host,
        port=settings.object_store_port,
        access_key=settings.object_store_username,
        secret_key=settings.object_store_passwd,
    )
    dataset_manager_collection.add(object_store_dataset_manager)

    data_derive_util = dep.data_derive_util(dataset_manager_collection)
    dataset_inquery_util = dep.dataset_inquery_util(
        dataset_manager_collection, data_derive_util
    )

    docker_s3fs_plugin_helper = _init_docker_s3fs_plugin_helper(
        dataset_manager_collection=dataset_manager_collection,
        access_key=settings.object_store_username,
        secret_key=settings.object_store_passwd,
        settings=settings,
    )

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

    # Setup other required async tasks
    # create single future (gather) for running background tasks
    # this is done so it is easier to cancel them all at once
    futs = asyncio.gather(
        required_data_checks_manager.start(),
        data_provision_manager.start(),
        temp_datasets_manager.start(),
    )
    # create a task that runs tasks in background
    background_tasks = asyncio.create_task(asyncio.wait_for(futs, timeout=None))

    # use future like condition variable. once background tasks are done / cancelled,
    # set its result, so whatever is awaiting it can proceed
    done_fut = asyncio.Future()

    def done_callback(_: asyncio.Task):
        done_fut.set_result(None)

    background_tasks.add_done_callback(done_callback)

    yield
    # everything after yield is run _during_ service shutdown, bearing it is not a SIGKILL

    # ensure that background tasks can run any cleanup work
    # 1. cancel tasks
    # 2. done_callback will be called once this completes
    # 3. done_callback sets done_fut result
    # 4. done_fut's result is returned
    background_tasks.cancel()
    await done_fut


app = FastAPI(lifespan=lifespan)


DatasetManagementCollectionDep = Annotated[
    DatasetManagerCollection, Depends(dep.dataset_manager_collection)
]


@app.exception_handler(ErrorResponseException)
async def error_response_exception_handler(_: Request, exc: ErrorResponseException):
    """Transforms ErrorResponseException's thrown during a request into a JSONResponse with status
    code and error information from the ErrorResponseException's inner ErrorEnum member, `error`.

    Example:
    ```
    from dmod.dataservice.errors import Error as ErrorEnum
    from dmod.dataservice.exceptions import Error as ErrorResponseException

    @app.get("/create")
    def create_dataset_handler(name: str):
        # ...
        raise ErrorResponseException(ErrorEnum.DATASET_EXISTS)
        # response (response status code is same as status):
        # {
        #     "type": "/errors/dataset_exists",
        #     "title": "DATASET_EXISTS",
        #     "status": 403,
        #     "detail": "Dataset already exists"
        # }
        #
        # or
        # if detail not supplied, detail from ErrorEnum variant used
        raise ErrorResponseException(ErrorEnum.DATASET_EXISTS, detail=f"A dataset already exists with name: {name}")
    ```
    """
    return JSONResponse(
        status_code=exc.error.status,
        content=Error.from_error_enum(error_enum=exc.error, detail=exc.detail).dict(),
    )


# NOTE: not sure if an optional `DataDomain` should be provided
# NOTE: the object name should also be optional. meaning we should be able to infer it from the upload
# NOTE: add a way to specify content type
@app.post(
    "/add_object",
    tags=["datasets"],
    description="Upload a file to an existing dataset.",
)
async def add_object_handler(
    dataset_name: str,
    object_name: Path,
    obj: UploadFile,
    service_manager: DatasetManagementCollectionDep,
):
    """
    Add a file to an existing dataset.
    Overwrites existing object with identical `object_name`.

    201 created returned on success
    """
    success = service_manager.manager(DatasetType.OBJECT_STORE).add_data(
        dataset_name=dataset_name, dest=object_name.as_posix(), data=obj.file
    )
    if not success:
        raise ErrorResponseException(Errors.PUT_OBJECT_FAILURE)
    return status.HTTP_201_CREATED


def _service_manager(
    util: Annotated[JobUtil, Depends(dep.job_util)],
    service_manager: DatasetManagementCollectionDep,
    inquery: Annotated[DatasetInqueryUtil, Depends(dep.dataset_inquery_util)],
) -> ServiceManager:
    """
    return an injectable `ServiceManager` (websocket handler)
    """
    return ServiceManager(
        job_util=util,
        dataset_manager_collection=service_manager,
        dataset_inquery_util=inquery,
    )


@app.websocket("/")
async def websocket_handler(
    websocket: WebSocket, manager: Annotated[ServiceManager, Depends(_service_manager)]
):
    await manager.listener(websocket)


# initialization helper functions
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
        dataset_manager_collection=dataset_manager_collection,
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
