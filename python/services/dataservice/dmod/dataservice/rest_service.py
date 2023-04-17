from pathlib import Path
from fastapi import FastAPI, Depends, Request, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from ._version import __version__ as version
from .errors import Error as ErrorEnum
from .exceptions import ErrorResponseException
from .models import (
    Option,
    Error,
    DataCategory,
    DataDomain,
    DatasetObjectMetadata,
    DatasetPutObjectMultipleRequest,
    DatasetQueryResponse,
    DatasetShortInfo,
    QueryType,
)

from typing import List, Optional
from typing_extensions import Annotated


app = FastAPI(
    title="DMOD Data Service",
    version=version,
    terms_of_service="https://github.com/NOAA-OWP/DMOD/blob/4677879c07bc6534b4aa3fd434804b51dc579ace/TERMS.md",
    license_info={
        "name": "USDOC",
        "url": "https://raw.githubusercontent.com/NOAA-OWP/owp-open-source-project-template/ed3e23a203153c4e00c4f95893f5e45631620481/LICENSE",
    },
)


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


@app.post("/create")
async def create_dataset(
    dataset_name: str,
    data_category: DataCategory,
    data_domain: DataDomain,
) -> DatasetShortInfo:
    """Create an empty dataset"""
    ...


@app.get("/get_object")
async def get_object(dataset_name: str, object_path: Path) -> StreamingResponse:
    """Download object from dataset."""
    ...


@app.put("/put_object")
async def pub_object(
    dataset_name: str,
    object_name: Path,
    object: UploadFile,
    extract: bool = Query(
        False,
        description="If true, .tar.gz and .gz archive files will be extracted",
    ),
):
    """Add a file or archive to an existing dataset. `.tar.gz` and `.gz` archive files will be
    extracted if 'extract' parameter is true. Overwrites existing object with identical object_name.
    """
    ...


@app.put("/put_objects")
async def pub_objects(data: Annotated[DatasetPutObjectMultipleRequest, Depends()]):
    """Add multiple files and add them to existing dataset. Overwrites existing objects with
    identical object_names."""
    ...


@app.get("/list_objects")
async def list_objects(
    dataset_name: str, prefix: Optional[Path] = None, recursive: bool = True
) -> List[DatasetObjectMetadata]:
    """List a dataset's objects."""
    ...


@app.get("/query", response_model_exclude_none=True)
async def query(dataset_name: str, q: List[QueryType]) -> DatasetQueryResponse:
    """Inquire a dataset's metadata attributes."""
    ...


@app.delete("/delete")
async def delete(dataset_name: str):
    """Delete a dataset."""
    ...


@app.get("/search", response_model_exclude_none=True)
async def search(
    data_domain: DataDomain, data_category: DataCategory
) -> Option[DatasetShortInfo]:
    """Search for a dataset that satisfies the given `data_domain` and `data_category`
    requirements."""
    ...


@app.get("/list_datasets")
async def list_all() -> List[DatasetShortInfo]:
    """List all datasets and their guids."""
    ...


@app.get("/error/{variant_name}")
async def error(variant_name: ErrorEnum):
    ...
