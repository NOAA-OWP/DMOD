from abc import ABC, abstractmethod
from dmod.communication import (AuthClient, InvalidMessageResponse, ManagementAction, NGENRequest, NGENRequestResponse,
                                NgenCalibrationRequest, NgenCalibrationResponse, TransportLayerClient)
from dmod.communication.client import ConnectionContextClient
from dmod.communication.dataset_management_message import DatasetManagementMessage, DatasetManagementResponse, \
    MaaSDatasetManagementMessage, MaaSDatasetManagementResponse, QueryType, DatasetQuery
from dmod.communication.data_transmit_message import DataTransmitMessage, DataTransmitResponse
from dmod.communication.maas_request.job_message import (JobControlAction, JobControlRequest, JobControlResponse,
                                                         JobInfoRequest, JobInfoResponse, JobListRequest,
                                                         JobListResponse)
from dmod.core.exception import DmodRuntimeError
from dmod.core.meta_data import DataCategory, DataDomain
from dmod.core.serializable import BasicResultIndicator, ResultIndicator
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Type, Union

import json

#import logging
#logger = logging.getLogger("gui_log")


class JobClient:

    def __init__(self, transport_client: TransportLayerClient, auth_client: AuthClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._transport_client: TransportLayerClient = transport_client
        self._auth_client: AuthClient = auth_client

    async def _job_control_request(self, job_id, action: JobControlAction) -> JobControlResponse:
        """
        Helper function for centralizing/parameterizing different job control actions possible via the public interface.

        Parameters
        ----------
        job_id
            The job to request action on.
        action
            The type of action to request.

        Returns
        -------
        JobControlResponse
            A response object indicating success or failure of the action request, as well as relevant details.
        """
        raw_response = None
        try:
            raw_response = await self._submit_job_request(JobControlRequest(job_id=job_id, action=action))
            response = JobControlResponse.factory_init_from_deserialized_json(json.loads(raw_response))
            if response is not None:
                return response
            else:
                return JobControlResponse(job_id=job_id, action=action, success=False,
                                          reason="Response Deserializing Failed", data={"raw_response": raw_response},
                                          message="Unable to deserialize JSON to response object")
        except Exception as e:
            return JobControlResponse(job_id=job_id, action=action, success=False, reason=e.__class__.__name__,
                                      message=str(e), data={"raw_response": raw_response} if raw_response else None)

    async def _job_info_request(self, job_id: str, status_only: bool) -> JobInfoResponse:
        """
        Single central helper function for handling job info request scenarios supported by the public interface.

        Parameters
        ----------
        job_id
            The job for which to request state details.
        status_only
            Whether only the job's status is being requested, as opposed to the full state of the job object.

        Returns
        -------
        JobInfoResponse
            A response object indicating success or failure and containing the requested state info when successful.
        """
        raw_response = None
        try:
            raw_response = await self._submit_job_request(request=JobInfoRequest(job_id=job_id,
                                                                                 status_only=status_only))
            response = JobInfoResponse.factory_init_from_deserialized_json(json.loads(raw_response))
            if response is not None:
                return response
            else:
                return JobInfoResponse(job_id=job_id, status_only=status_only, success=False,
                                       reason="Response Deserializing Failed", data={"raw_response": raw_response},
                                       message=f"Unable to deserialize JSON to {JobInfoResponse.__class__.__name__}")
        except Exception as e:
            return JobInfoResponse(job_id=job_id, status_only=status_only, success=False, reason=e.__class__.__name__,
                                   message=str(e), data={"raw_response": raw_response} if raw_response else None)

    async def _submit_job_request(self, request) -> str:
        if await self._auth_client.apply_auth(request):
            # Some clients may be async context managers
            if isinstance(self._transport_client, ConnectionContextClient):
                async with self._transport_client as t_client:
                    await t_client.async_send(data=str(request))
                    return await t_client.async_recv()
            else:
                await self._transport_client.async_send(data=str(request))
                return await self._transport_client.async_recv()
        else:
            msg = f"{self.__class__.__name__} could not use {self._auth_client.__class__.__name__} to authenticate " \
                  f"{request.__class__.__name__}"
            raise DmodRuntimeError(msg)

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

    async def request_job_info(self, job_id: str, *args, **kwargs) -> JobInfoResponse:
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
        JobInfoResponse
            An indicator of success of the request that, when successful, contains the full state of the provided job,
            formatted as a JSON dictionary, in the ``data`` attribute.
        """
        return await self._job_info_request(job_id=job_id, status_only=False)

    async def request_job_release(self, job_id: str, *args, **kwargs) -> JobControlResponse:
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
        JobControlResponse
            An indicator of whether there had been allocated resources for the job, all of which are now released.
        """
        return await self._job_control_request(job_id=job_id, action=JobControlAction.RELEASE)

    async def request_job_restart(self, job_id: str, *args, **kwargs) -> JobControlResponse:
        """
        Request a job - expected be stopped - be resumed; i.e., transitioned from ``STOPPED`` to ``RUNNING` exec step.

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
        JobControlResponse
            An indicator of whether the job was restarted as requested.
        """
        return await self._job_control_request(job_id=job_id, action=JobControlAction.RESTART)

    async def request_job_status(self, job_id: str, *args, **kwargs) -> JobInfoResponse:
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
        JobInfoResponse
            An indicator that, when successful, includes as ``data`` the serialized status of the provided job.
        """
        return await self._job_info_request(job_id=job_id, status_only=True)

    async def request_job_stop(self, job_id: str, *args, **kwargs) -> JobControlResponse:
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
        JobControlResponse
            An indicator of whether the job was stopped as requested.
        """
        return await self._job_control_request(job_id=job_id, action=JobControlAction.STOP)

    async def request_jobs_list(self, jobs_list_active_only: bool, *args, **kwargs) -> JobListResponse:
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
        JobListResponse
            An indicator that, when successful, includes as ``data`` the list of ids of existing jobs.

        See Also
        -------
        get_jobs_list
        """
        raw_response = None
        try:
            raw_response = await self._submit_job_request(request=JobListRequest(only_active=jobs_list_active_only))
            response = JobListResponse.factory_init_from_deserialized_json(json.loads(raw_response))
            if response is not None:
                return response
            else:
                return JobListResponse(only_active=jobs_list_active_only, success=False,
                                       reason="Response Deserializing Failed", data={"raw_response": raw_response},
                                       message=f"Unable to deserialize JSON to {JobInfoResponse.__class__.__name__}")
        except Exception as e:
            return JobListResponse(only_active=jobs_list_active_only, success=False, reason=e.__class__.__name__,
                                   message=str(e), data={"raw_response": raw_response} if raw_response else None)

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


class DataTransferAgent(ABC):

    @abstractmethod
    async def download_dataset_item(self, dataset_name: str, item_name: str, dest: Path):
        pass

    @abstractmethod
    async def upload_dataset_item(self, dataset_name: str, item_name: str, source: Path) -> DatasetManagementResponse:
        pass

    @property
    @abstractmethod
    def uses_auth(self) -> bool:
        """
        Whether this particular agent instance uses authentication when interacting with the other party.

        Clients that use auth

        Returns
        -------
        bool
            Whether this particular agent uses authentication in interactions.
        """
        pass


class SimpleDataTransferAgent(DataTransferAgent):

    def __init__(self, transport_client: TransportLayerClient, auth_client: Optional[AuthClient] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._transport_client: TransportLayerClient = transport_client
        self._auth_client: Optional[AuthClient] = auth_client

    async def _transfer_receiver(self):
        """
        Receive a series of data transmit messages, with the transfer already initiated.

        Note that this generator expects that the first message received be the first ::class:`DataTransmitMessage`.
        Additionally, after the last ``yield``, which will be the final necessary ::class:`DataTransmitMessage` that has
        ``is_last`` value of ``True``, the transport client should expect to immediately receive the final
        ::class:`DatasetManagementResponse` message closing the request.

        Yields
        -------
        DataTransmitMessage
            The next data transmit message in the transfer series.
        """
        incoming_obj: DataTransmitMessage = None

        while incoming_obj is None or not incoming_obj.is_last:
            # TODO: may need to make messages at the transport level session aware to make this work with shared connections/client
            incoming_data = await self._transport_client.async_recv()
            incoming_obj = DataTransmitMessage.factory_init_from_deserialized_json(json.loads(incoming_data))
            if not isinstance(incoming_obj, DataTransmitMessage):
                await self._transport_client.async_send(str(InvalidMessageResponse()))
                raise DmodRuntimeError(f"{self.__class__.__name__} could not deserialize DataTransmitMessage in data "
                                       f"transfer receipt attempt")
            # TODO: confirm that this works as expected/needed after the last data message
            reply_obj = DataTransmitResponse.create_for_received(received_msg=incoming_obj)
            await self._transport_client.async_send(str(reply_obj))
            yield incoming_obj

    async def _request_prep(self, dataset_name: str, item_name: str, action: ManagementAction) -> Tuple[DatasetManagementMessage, Type[DatasetManagementResponse]]:
        """
        Prep a download or upload initial request.

        Parameters
        ----------
        dataset_name
        item_name
        action

        Returns
        -------
        Tuple[DatasetManagementMessage, Type[DatasetManagementResponse]]
            A tuple of two items:
                - the prepared initial request
                - the appropriate type for response objects, depending on whether authentication is being used
        """
        req_params = {'action': action, 'dataset_name': dataset_name, 'data_location': item_name}

        if self.uses_auth:
            # This will be replaced as soon as we call apply_auth, but some string is required for __init__
            req_params['session_secret'] = ''
            request = MaaSDatasetManagementMessage(**req_params)
            # TODO: (later) implement and use DmodAuthenticationFailure, though possibly down the apply_auth call stack
            if not await self._auth_client.apply_auth(request):
                msg = f'{self.__class__.__name__} could not apply auth to {request.__class__.__name__}'
                raise DmodRuntimeError(msg)
            else:
                return request, MaaSDatasetManagementResponse
        else:
            return DatasetManagementMessage(**req_params), DatasetManagementResponse

    async def download_dataset_item(self, dataset_name: str, item_name: str, dest: Path) -> DatasetManagementResponse:
        if dest.exists():
            reason = f'Destination File Exists'
            msg = f'{self.__class__.__name__} could not download dataset item to existing path {str(dest)}'
            return DatasetManagementResponse(success=False, reason=reason, message=msg)

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
        except:
            reason = f'Unable to Create Parent Directory'
            msg = f'{self.__class__.__name__} could not create parent directory for downloading item to {str(dest)}'
            return DatasetManagementResponse(success=False, reason=reason, message=msg)

        try:
            request, final_response_type = await self._request_prep(dataset_name=dataset_name, item_name=item_name,
                                                              action=ManagementAction.REQUEST_DATA)
        # TODO: (later) implement and use DmodAuthenticationFailure
        except DmodRuntimeError as e:
            reason = f'{self.__class__.__name__} Download Auth Failure'
            return MaaSDatasetManagementResponse(success=False, reason=reason, message=str(e))

        with dest.open('w') as file:
            # Do initial request outside of generator
            await self._transport_client.async_send(data=str(request))
            async for received_data_msg in self._transfer_receiver():
                data = received_data_msg.data
                while data:
                    bytes_written = file.write(data)
                    data = data[bytes_written:]
            final_data = await self._transport_client.async_recv()

        try:
            final_response_json = json.loads(final_data)
        except Exception as e:
            msg = f"{self.__class__.__name__} failed with {e.__class__.__name__} parsing `{final_data}` to JSON)"
            return final_response_type(success=False, reason=f"JSON Parse Failure On Final Response", message=msg)

        final_response = final_response_type.factory_init_from_deserialized_json(final_response_json)
        if final_response is None:
            return final_response_type(success=False, reason="Failed to Deserialize Final Response")
        else:
            return final_response

    async def upload_dataset_item(self, dataset_name: str, item_name: str, source: Path) -> DatasetManagementResponse:
        if not source.is_file():
            return DatasetManagementResponse(success=False, reason="Dataset Upload File Not Found",
                                             message=f"File {source!s} does not exist")
        try:
            message, final_response_type = await self._request_prep(dataset_name=dataset_name, item_name=item_name,
                                                              action=ManagementAction.ADD_DATA)
        # TODO: (later) implement and use DmodAuthenticationFailure
        except DmodRuntimeError as e:
            reason = f'{self.__class__.__name__} Upload Request Auth Failure'
            return MaaSDatasetManagementResponse(success=False, reason=reason, message=str(e))

        chunk_size = 1024

        with source.open('r') as file:
            last_send = False
            raw_chunk = file.read(chunk_size)

            while True:
                await self._transport_client.async_send(data=str(message))

                response_json = json.loads(await self._transport_client.async_recv())
                response = final_response_type.factory_init_from_deserialized_json(response_json)
                if response is not None:
                    return response
                elif last_send:
                    msg = f"{self.__class__.__name__} should have received {final_response_type.__name__} here"
                    raise DmodRuntimeError(msg)

                response = DataTransmitResponse.factory_init_from_deserialized_json(response_json)
                if response is None:
                    msg = f"{self.__class__.__name__} couldn't parse response to request to upload {source!s}"
                    return final_response_type(success=False, reason="Unparseable Upload Init", message=msg)
                elif not response.success:
                    msg = f"{self.__class__.__name__} received {response.__class__.__name__} indicating failure"
                    return final_response_type(success=False, reason="Failed Upload Transfer", message=msg)

                # Look ahead to see if this is the last transmission ...
                next_chunk = file.read(chunk_size)
                # ... keep track if it is last ...
                last_send = not bool(next_chunk)
                # ... and also note in message if it is last ...
                message = DataTransmitMessage(data=raw_chunk, series_uuid=response.series_uuid, is_last=last_send)

                # Then once that chunk is sent, bump the look-ahead to the current
                raw_chunk = next_chunk

    @property
    def uses_auth(self) -> bool:
        """
        Whether this particular agent instance uses authentication when interacting with the other party.

        Clients that use auth

        Returns
        -------
        bool
            Whether this particular agent uses authentication in interactions.
        """
        return self._auth_client is not None


class DataServiceClient:

    @classmethod
    def extract_dataset_names(cls, response: DatasetManagementResponse) -> List[str]:
        """
        Parse response object for an included list of dataset names.

        Parse a received ::class:`DatasetManagementResponse` for a list of dataset names.  Generally, this should be the
        response to a request of either the ``LIST_ALL`` or ``SEARCH`` ::class:`ManagementAction` value.

        An unsuccessful response or a response that does not container the dataset names data will return an empty list.

        Parameters
        ----------
        response : DatasetManagementResponse
            The response message from which to parse dataset names.

        Returns
        -------
        List[str]
            The list of parsed dataset names.

        Raises
        -------
        DmodRuntimeError
            Raised if the parameter is not a ::class:`DatasetManagementResponse` (or subtype) object.
        """
        if not isinstance(response, DatasetManagementResponse):
            raise DmodRuntimeError(f"{cls.__name__} can't parse list of datasets from {response.__class__.__name__}")
        # Consider these as valid cases, and treat them as just not listing any datasets
        elif not response.success or response.data is None or response.data.datasets is None:
            return []
        else:
            return response.data.datasets

    def __init__(self, transport_client: TransportLayerClient, auth_client: Optional[AuthClient] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._transport_client: TransportLayerClient = transport_client
        self._auth_client: Optional[AuthClient] = auth_client

    async def _process_request(self, request: DatasetManagementMessage) -> DatasetManagementResponse:
        """
        Reusable, general helper function to process a custom-assembled request for the data service.

        Function recreates request as auth-supporting type and applies auth when necessary, then processes the send and
        parsing of the response.

        Parameters
        ----------
        request : DatasetManagementMessage
            The assembled request message, of a type that does not yet (and cannot) have any auth applied.

        Returns
        -------
        DatasetManagementResponse
            A response to the request from the service to delete the given dataset, which may actually be a
            ::class:`MaaSDatasetManagementMessage` depending on whether this type uses auth.

        Raises
        -------
        DmodRuntimeError
            If the response from the service cannot be deserialized successfully to the expected response type.

        See Also
        -------
        uses_auth
        """
        if self.uses_auth:
            request = MaaSDatasetManagementMessage.factory_create(mgmt_msg=request, session_secret='')
            all_required_auth_is_applied = await self._auth_client.apply_auth(request)
            response_type = MaaSDatasetManagementResponse
        else:
            # If no auth was required, treat as though all required auth as applied
            all_required_auth_is_applied = True
            response_type = DatasetManagementResponse

        if not all_required_auth_is_applied:
            reason = f'{self.__class__.__name__} Request Auth Failure'
            msg = f'{self.__class__.__name__} create_dataset could not apply auth to {request.__class__.__name__}'
            return response_type(success=False, reason=reason, message=msg)

        # Some clients may be async context managers
        if isinstance(self._transport_client, ConnectionContextClient):
            async with self._transport_client as t_client:
                await t_client.async_send(data=str(request))
                response_data = await t_client.async_recv()
        else:
            await self._transport_client.async_send(data=str(request))
            response_data = await self._transport_client.async_recv()

        response_obj = response_type.factory_init_from_deserialized_json(json.loads(response_data))
        if not isinstance(response_obj, response_type):
            msg = f"{self.__class__.__name__} could not deserialize {response_type.__name__} from raw response data" \
                  f" '{response_data}'"
            raise DmodRuntimeError(msg)
        else:
            return response_obj

    # TODO: better integrate uploading initial data into the create request itself
    async def create_dataset(self, name: str, category: DataCategory, domain: DataDomain,
                             upload_paths: Optional[List[Path]] = None, data_root: Optional[Path] = None,
                             **kwargs) -> DatasetManagementResponse:
        """
        Create a dataset from the given parameters.

        Parameters
        ----------
        name : str
            The name for the dataset.
        category : DataCategory
            The category for the dataset.
        domain : DataDomain
            The defined domain for the dataset.
        upload_paths : Union[Path, List[Path]]
            List of paths of files to upload.
        data_root : Optional[Path]
            A relative data root directory, used to adjust the names for uploaded items.
        kwargs

        Returns
        -------
        DatasetManagementResponse
            A response to the request for the service to create a new dataset, which may actually be a
            ::class:`MaaSDatasetManagementMessage` depending on whether this instance uses auth.

        Raises
        -------
        DmodRuntimeError
            If the response from the service cannot be deserialized successfully to the expected response type.

        See Also
        -------
        upload_to_dataset
        uses_auth
        """
        request = DatasetManagementMessage(action=ManagementAction.CREATE, domain=domain, dataset_name=name,
                                           category=category)
        try:
            create_response = await self._process_request(request=request)
        except DmodRuntimeError as e:
            raise DmodRuntimeError(f"DMOD error when creating dataset: {str(e)}")

        if not create_response.success or not upload_paths:
            return create_response

        upload_response = await self.upload_to_dataset(dataset_name=name, paths=upload_paths, data_root=data_root)
        if upload_response.success:
            return create_response
        else:
            create_response.success = False
            create_response.reason = "Initial Uploads Failed"
            create_response.message = f"Dataset {name} was created, but upload failures occurred: `{upload_response!s}`"
            return create_response

    async def does_dataset_exist(self, dataset_name: str, **kwargs) -> bool:
        """
        Helper function to test whether a dataset of the given name/id exists.

        Parameters
        ----------
        dataset_name : str
            The hypothetical dataset name of interest.

        Returns
        -------
        bool
            Whether a dataset of the given name exists with the data service.
        """
        # FIXME: optimize this more effectively later.
        return dataset_name in await self.list_datasets()

    async def delete_dataset(self, name: str, **kwargs) -> DatasetManagementResponse:
        """
        Delete a dataset.

        Parameters
        ----------
        name : str
            The unique name of the dataset to delete.
        kwargs

        Returns
        -------
        DatasetManagementResponse
            A response to the request from the service to delete the given dataset, which may actually be a
            ::class:`MaaSDatasetManagementMessage` depending on whether this type uses auth.

        Raises
        -------
        DmodRuntimeError
            If the response from the service cannot be deserialized successfully to the expected response type.

        See Also
        -------
        uses_auth
        """
        request = DatasetManagementMessage(action=ManagementAction.DELETE, dataset_name=name)
        try:
            return await self._process_request(request=request)
        except DmodRuntimeError as e:
            raise DmodRuntimeError(f"DMOD error when deleting dataset: {str(e)}")

    # TODO: this needs a storage client instead of to figure out where/how to "put" the data
    async def get_dataset_names(self, category: Optional[DataCategory] = None, **kwargs) -> DatasetManagementResponse:
        """
        Get a list of the names of datasets, optionally filtering to a specific category.

        Parameters
        ----------
        category : DataCategory
            Optional exclusively ::class:`DataCategory` to consider.

        Returns
        -------
        DatasetManagementResponse
            The returned response object itself that, when successful, contains a list of dataset names.

        See Also
        -------
        list_datasets
        """
        action = ManagementAction.LIST_ALL if category is None else ManagementAction.SEARCH
        request = DatasetManagementMessage(action=action, category=category)
        try:
            return await self._process_request(request=request)
        except DmodRuntimeError as e:
            raise DmodRuntimeError(f"DMOD error when getting dataset names: {str(e)}")

    async def get_dataset_item_names(self, dataset_name: str, **kwargs) -> DatasetManagementResponse:
        """
        Request the name/id of all items in the given dataset.

        Parameters
        ----------
        dataset_name : str
            The name/id of the dataset of interest.

        Returns
        -------
        DatasetManagementResponse
            A response containing item names if successful, or indicating failure.
        """
        request = DatasetManagementMessage(action=ManagementAction.QUERY, dataset_name=dataset_name,
                                           query=DatasetQuery(query_type=QueryType.LIST_FILES))
        try:
            return await self._process_request(request=request)
        except DmodRuntimeError as e:
            raise DmodRuntimeError(f"DMOD error when getting dataset item: {str(e)}")

    async def list_datasets(self, category: Optional[DataCategory] = None, **kwargs) -> List[str]:
        """
        Convenience method to list datasets, optionally filtering to a specific category.

        Function simply makes a nested call to ::method:`get_dataset_names` and parses the names of the datasets using
        ::method:`extract_dataset_names`.

        Parameters
        ----------
        category : DataCategory
            Optional exclusively ::class:`DataCategory` to consider.

        Returns
        -------
        List[str]
            The list of dataset names, or an empty list if the request was not successful.

        See Also
        -------
        extract_dataset_names
        get_dataset_item_names
        """
        return self.extract_dataset_names(response=await self.get_dataset_names(category=category, **kwargs))

    async def list_dataset_items(self, dataset_name: str, **kwargs) -> List[str]:
        """
        Convenience method to get the list of items within a dataset.

        Parameters
        ----------
        dataset_name : str
            The name/id of the dataset of interest.

        Returns
        -------
        List[str]
            The list of item names, or an empty list if the request was not successful.

        See Also
        -------
        get_dataset_item_names
        """
        response = await self.get_dataset_item_names(dataset_name=dataset_name, **kwargs)
        return response.query_results.get('files', []) if response.success else []

    async def retrieve_from_dataset(self, dataset_name: str, dest_dir: Path,
                                    item_names: Optional[Union[str, Sequence[str]]] = None, **kwargs) -> ResultIndicator:
        """
        Download data from either all or specific item(s) within a dataset to a local path.

        Items are saved with the same name, relative to the ``dest`` directory.  If item names have '/' characters, it
        is assumed they were to emulate file system paths in the dataset storage location.  As such, these are separated
        and treated as nested directories within ``dest`` and created as needed.

        Parameters
        ----------
        dataset_name : str
            The dataset of interest.
        dest_dir : Path
            A local directory path under which to save the downloaded item(s).
        item_names : Optional[Union[str, Sequence[str]]] = None
            The name(s) of specific item(s) within a dataset to download; if ``None`` (the default), download all items.

        Returns
        -------
        ResultIndicator
            A result indicator indicating whether downloading was successful.
        """
        if not dest_dir.exists():
            return BasicResultIndicator(success=False, reason="No Dest Dir", message=f"'{dest_dir!s}' doesn't exist")
        elif not dest_dir.is_dir():
            return BasicResultIndicator(success=False, reason="Bad Dest", message=f"Non-dir '{dest_dir!s}' exists")
        elif not await self.does_dataset_exist(dataset_name=dataset_name):
            return BasicResultIndicator(success=False, reason="Dataset Does Not Exist",
                                        message=f"No existing dataset '{dataset_name}' was found")

        if not item_names:
            item_names = await self.list_dataset_items(dataset_name)
        else:
            unrecognized = [i for i in item_names if i not in set(await self.list_dataset_items(dataset_name))]
            if unrecognized:
                return BasicResultIndicator(success=False, reason="Can't Get Unrecognized Items", data=unrecognized)

        failed_items: Dict[str, DatasetManagementResponse] = dict()
        # TODO: see if we can perhaps have multiple agents and thread pool if multiplexing is available
        tx_agent = SimpleDataTransferAgent(transport_client=self._transport_client, auth_client=self._auth_client)

        for i in item_names:
            result = await tx_agent.download_dataset_item(dataset_name=dataset_name, item_name=i,
                                                          dest=dest_dir.joinpath(i))
            if not result.success:
                failed_items[i] = result

        if len(failed_items) == 0:
            return BasicResultIndicator(success=True, reason="Retrieval Complete")
        else:
            return BasicResultIndicator(success=False, reason=f"{len(failed_items)!s} Failures",
                                        data=failed_items)

    async def upload_to_dataset(self, dataset_name: str, paths: Union[Path, List[Path]],
                                data_root: Optional[Path] = None, **kwargs) -> ResultIndicator:
        """
        Upload data a dataset.

        A ``data_root`` param can optionally be supplied to adjust uploaded item names.  E.g., if ``paths`` contains
        the file ``/home/username/data_dir_1/file_1``, then by default its contents will be uploaded to the dataset item
        named "/home/username/data_dir_1/file_1".  However, if ``data_root`` is set to, e.g.,
        ``/home/username/data_dir_1``, then the uploaded item will instead be named simply "file_1".

        Parameters
        ----------
        dataset_name : str
            The name of the dataset.
        paths : Union[Path, List[Path]]
            Path or list of paths of files to upload.
        data_root : Optional[Path]
            A relative data root directory, used to adjust the names for uploaded items.

        Returns
        -------
        ResultIndicator
            An indicator of whether uploading was successful
        """
        # TODO: see if we can perhaps have multiple agents and thread pool if multiplexing is available
        tx_agent = SimpleDataTransferAgent(transport_client=self._transport_client, auth_client=self._auth_client)
        if isinstance(paths, Path):
            paths = [paths]

        not_exist = list()
        not_file = list()

        for p in paths:
            if not p.exists():
                not_exist.append(p)
            elif not p.is_file():
                not_file.append(p)

        if len(not_exist) > 0:
            return BasicResultIndicator(success=False, reason="Non-Existing Upload Paths", data=not_exist)
        elif len(not_file) > 0:
            return BasicResultIndicator(success=False, reason="Non-File Upload Paths", data=not_file)

        items = {str(p): p for p in paths} if data_root is None else {str(p.relative_to(data_root)): p for p in paths}

        failed_items = dict()

        for name, file in items.items():
            response = await tx_agent.upload_dataset_item(dataset_name=dataset_name, item_name=name, source=file)
            if not response.success:
                failed_items[name] = response

        if len(failed_items) == 0:
            return BasicResultIndicator(success=True, reason="Upload Complete", message=f"{len(paths)!s} items")
        else:
            return BasicResultIndicator(success=True, reason=f"{len(failed_items)!s} Failed Uploads", data=failed_items)

    @property
    def uses_auth(self) -> bool:
        """
        Whether this particular client instance uses auth when interacting with the service.

        Clients that use auth

        Returns
        -------
        bool
            Whether this particular client instance uses auth when interacting with the service.
        """
        return self._auth_client is not None
