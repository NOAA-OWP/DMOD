"""
Functions that injectable via FastAPI's dependency injection system.
"""
from functools import lru_cache

from dmod.dataservice.data_derive_util import DataDeriveUtil
from dmod.dataservice.dataset_inquery_util import DatasetInqueryUtil
from dmod.dataservice.dataset_manager_collection import DatasetManagerCollection
from dmod.dataservice.service_settings import ServiceSettings, service_settings
from dmod.scheduler.job import DefaultJobUtilFactory, JobUtil
from fastapi import Depends
from typing_extensions import Annotated


@lru_cache
def dataset_manager_collection() -> DatasetManagerCollection:
    """
    Service singleton `DatasetManagerCollection`.
    All handlers or service level background tasks that need a `DatasetManagerCollection` _should_
    use this / depend on it via FastApi's dependency injection system.
    """
    return DatasetManagerCollection()


@lru_cache
def data_derive_util(
    dmc: Annotated[DatasetManagerCollection, Depends(dataset_manager_collection)]
) -> DataDeriveUtil:
    """
    Service singleton `DataDeriveUtil`.
    All handlers or service level background tasks that need a `DataDeriveUtil` _should_
    use this / depend on it via FastApi's dependency injection system.
    """
    return DataDeriveUtil(dataset_manager_collection=dmc)


@lru_cache
def dataset_inquery_util(
    manager_collection: Annotated[
        DatasetManagerCollection, Depends(dataset_manager_collection)
    ],
    derive_util: Annotated[DataDeriveUtil, Depends(data_derive_util)],
) -> DatasetInqueryUtil:
    """
    Service singleton `DatasetInqueryUtil`.
    All handlers or service level background tasks that need a `DatasetInqueryUtil` _should_
    use this / depend on it via FastApi's dependency injection system.
    """
    return DatasetInqueryUtil(
        dataset_manager_collection=manager_collection, derive_util=derive_util
    )


@lru_cache
def job_util(
    settings: Annotated[ServiceSettings, Depends(service_settings)]
) -> JobUtil:
    """
    Service singleton `DefaultJobUtilFactory`.
    All handlers or service level background tasks that need a `DefaultJobUtilFactory` _should_
    use this / depend on it via FastApi's dependency injection system.
    """
    return DefaultJobUtilFactory.factory_create(
        redis_host=settings.redis_host,
        redis_port=settings.redis_port,
        redis_pass=settings.redis_pass,
    )
