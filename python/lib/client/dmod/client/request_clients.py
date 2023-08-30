from abc import ABC, abstractmethod
from dmod.communication import AuthClient, DataServiceClient, ExternalRequestClient, InvalidMessageResponse, \
    ManagementAction, NGENRequest, NGENRequestResponse, NgenCalibrationRequest, NgenCalibrationResponse, \
    TransportLayerClient
from dmod.communication.dataset_management_message import DatasetManagementMessage, DatasetManagementResponse, \
    MaaSDatasetManagementMessage, MaaSDatasetManagementResponse, QueryType, DatasetQuery
from dmod.communication.data_transmit_message import DataTransmitMessage, DataTransmitResponse
from dmod.communication.session import Session
from dmod.core.meta_data import DataCategory, DataDomain
from pathlib import Path
from typing import List, Optional, Tuple, Type, Union
from typing_extensions import Self

import json
import websockets

#import logging
#logger = logging.getLogger("gui_log")


class JobClient:

    def __init__(self, transport_client: TransportLayerClient, auth_client: AuthClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._transport_client: TransportLayerClient = transport_client
        self._auth_client: AuthClient = auth_client

    async def _submit_job_request(self, request) -> str:
        if await self._auth_client.apply_auth(request):
            await self._transport_client.async_send(data=str(request))
            return await self._transport_client.async_recv()
        else:
            msg = f"{self.__class__.__name__} could not use {self._auth_client.__class__.__name__} to authenticate " \
                  f"{request.__class__.__name__}"
            raise RuntimeError(msg)

    async def get_jobs_list(self, active_only: bool) -> List[str]:
        """
        Get a list of ids of existing jobs.

        A convenience wrapper around ::method:`request_jobs_list` that returns just the list of job ids rather than the
        full ::class:`ResultsIndicator` object.

        Parameters
        ----------
        active_only : bool
            Whether only the ids of active jobs should be included.

        Returns
        -------
        List[str]
            The list of ids of existing jobs.

        Raises
        -------
        RuntimeError
            If the indicator returned by ::method:`request_jobs_list` has ``success`` value of ``False``.

        See Also
        -------
        request_jobs_list
        """
        indicator = await self.request_jobs_list(jobs_list_active_only=active_only)
        if not indicator.success:
            raise RuntimeError(f"{self.__class__.__name__} received failure indicator getting list of jobs.")
        else:
            return indicator.data

    # TODO: this is going to need some adjustments to the type hinting
    async def request_job_info(self, job_id: str, *args, **kwargs) -> ResultIndicator:
        """
        Request the full state of the provided job, formatted as a JSON dictionary.

        Parameters
        ----------
        job_id : str
            The id of the job in question.
        args
            (Unused) variable positional args.
        kwargs
            (Unused) variable keyword args.

        Returns
        -------
        ResultIndicator
            An indicator of success of the request that, when successful, contains he full state of the provided job,
            formatted as a JSON dictionary, in the ``data`` attribute.
        """
        # TODO: implement
        raise NotImplementedError('{} function "request_job_info" not implemented yet'.format(self.__class__.__name__))

    async def request_job_release(self, job_id: str, *args, **kwargs) -> ResultIndicator:
        """
        Request the allocated resources for the provided job be released.

        Parameters
        ----------
        job_id : str
            The id of the job in question.
        args
            (Unused) variable positional args.
        kwargs
            (Unused) variable keyword args.

        Returns
        -------
        ResultIndicator
            An indicator of whether there had been allocated resources for the job, all of which are now released.
        """
        # TODO: implement
        raise NotImplementedError('{} function "request_job_release" not implemented yet'.format(self.__class__.__name__))

    async def request_job_status(self, job_id: str, *args, **kwargs) -> BasicResultIndicator:
        """
        Request the status of the provided job.

        The status value will be serialized to a string and included as the ``data`` attribute of the returned
        ::class:`ResultIndicator`.

        Parameters
        ----------
        job_id : str
            The id of the job in question.
        args
            (Unused) variable positional args.
        kwargs
            (Unused) variable keyword args.

        Returns
        -------
        BasicResultIndicator
            An indicator that, when successful, includes as ``data`` the serialized status string of the provided job.
        """
        # TODO: implement
        raise NotImplementedError('{} function "request_job_status" not implemented yet'.format(self.__class__.__name__))

    async def request_job_stop(self, job_id: str, *args, **kwargs) -> ResultIndicator:
        """
        Request the provided job be stopped; i.e., transitioned to the ``STOPPED`` exec step.

        Parameters
        ----------
        job_id : str
            The id of the job in question.
        args
            (Unused) variable positional args.
        kwargs
            (Unused) variable keyword args.

        Returns
        -------
        ResultIndicator
            An indicator of whether the job was stopped as requested.
        """
        # TODO: implement
        raise NotImplementedError('{} function "request_job_stop" not implemented yet'.format(self.__class__.__name__))

    async def request_jobs_list(self, jobs_list_active_only: bool, *args, **kwargs) -> BasicResultIndicator:
        """
        Request a list of ids of existing jobs.

        The list of ids will be included as the ``data`` attribute of the returned ::class:`ResultIndicator`.

        Parameters
        ----------
        jobs_list_active_only : bool
            Whether to exclusively include jobs with "active" status values.
        args
            (Unused) variable positional args.
        kwargs
            (Unused) variable keyword args.

        Returns
        -------
        BasicResultIndicator
            An indicator that, when successful, includes as ``data`` the list of ids of existing jobs.

        See Also
        -------
        get_jobs_list
        """
        # TODO: implement
        raise NotImplementedError('{} function "request_jobs_list" not implemented yet'.format(self.__class__.__name__))

    async def submit_ngen_request(self, **kwargs) -> NGENRequestResponse:
        return NGENRequestResponse.factory_init_from_deserialized_json(
            json.loads(await self._submit_job_request(request=NGENRequest(request_body=kwargs, **kwargs))))

    async def submit_ngen_cal_request(self, **kwargs) -> NgenCalibrationResponse:
        return NgenCalibrationResponse.factory_init_from_deserialized_json(
            json.loads(await self._submit_job_request(request=NgenCalibrationRequest(request_body=kwargs, **kwargs))))

    async def submit_request_from_file(self, job_type: str, request_file: Path, *kwargs) -> ResultIndicator:
        """
        Submit a serialized job request stored in the given file.

        Parameters
        ----------
        job_type : str
            String representation of the type of request: either ``ngen`` or ``ngen_cal``.
        request_file : Path
            The supplied file containing a JSON string, which should be a serialized, applicable request object.
        """
        return await self.submit_request_from_json(job_type=job_type, request_json=request_file.read_text())

    async def submit_request_from_json(self, job_type: str, request_json: Union[dict, str], **kwargs) -> ResultIndicator:
        """
        Submit a supplied, serialized job request.

        Parameters
        ----------
        job_type : str
            String representation of the type of request: either ``ngen`` or ``ngen_cal``.
        request_json : Union[dict, str]
            The serialized representation of a request as JSON, either as a ``str`` or already inflated to a JSON
            ``dict`` object.
        """
        if isinstance(request_json, str):
            request_json = json.loads(request_json)

        if job_type == 'ngen':
            return NGENRequestResponse.factory_init_from_deserialized_json(
                json.loads(await self._submit_job_request(NGENRequest.factory_init_from_deserialized_json(request_json))))
        elif job_type == 'ngen_cal':
            return NgenCalibrationResponse.factory_init_from_deserialized_json(
                json.loads(await self._submit_job_request(NgenCalibrationRequest.factory_init_from_deserialized_json(request_json))))
        else:
            raise RuntimeError(f"Invalid job type indicator for serialized job request: {job_type}")
