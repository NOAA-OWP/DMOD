from abc import ABC, abstractmethod
from dmod.communication import InternalServiceClient, MaasRequestClient, ManagementAction
from dmod.communication.client import R
from dmod.communication.dataset_management_message import DatasetManagementMessage, DatasetManagementResponse, \
    MaaSDatasetManagementMessage, MaaSDatasetManagementResponse
from dmod.core.meta_data import DataCategory
from pathlib import Path
from typing import List, Optional, Tuple, Type, Union

import json
import websockets

#import logging
#logger = logging.getLogger("gui_log")


class DatasetClient(ABC):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_response = None

    def _parse_list_of_dataset_names_from_response(self, response: DatasetManagementResponse) -> List[str]:
        """
        Parse an includes list of dataset names from a received management response.

        Note that an unsuccessful response, or a response (of the correct type) that does not explicitly include the
        expected data attribute with dataset names, will result in an empty list being returned.  However, an unexpected
        type for the parameter will cause a ::class:`RuntimeError`.

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
        RuntimeError
            Raised if the parameter is not a ::class:`DatasetManagementResponse` (or subtype) object.
        """
        if not isinstance(response, DatasetManagementResponse):
            msg = "Can't parse list of datasets from non-{} (received a {} object)"
            raise RuntimeError(msg.format(DatasetManagementResponse.__name__, response.__class__.__name__))
        # Consider these as valid cases, and treat them as just not listing any datasets
        elif not response.success or response.data is None or 'datasets' not in response.data:
            return []
        else:
            return response.data['datasets']

    @abstractmethod
    async def create_dataset(self, name: str, category: DataCategory, domain: DataDomain, **kwargs) -> bool:
        pass

    @abstractmethod
    async def delete_dataset(self, name: str, **kwargs) -> bool:
        pass

    @abstractmethod
    async def list_datasets(self, category: Optional[DataCategory] = None) -> List[str]:
        pass

    @abstractmethod
    async def upload_to_dataset(self, dataset_name: str, paths: List[Path]) -> bool:
        pass


class DatasetInternalClient(DatasetClient, InternalServiceClient[DatasetManagementMessage, DatasetManagementResponse]):

    @classmethod
    def get_response_subtype(cls) -> Type[R]:
        return DatasetManagementResponse

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def create_dataset(self, name: str, category: DataCategory) -> bool:
        # TODO: (later) consider also adding param for data to be added
        request = DatasetManagementMessage(action=ManagementAction.CREATE, dataset_name=name, category=category)
        self.last_response = await self.async_make_request(request)
        return self.last_response is not None and self.last_response.success

    async def list_datasets(self, category: Optional[DataCategory] = None) -> List[str]:
        action = ManagementAction.LIST_ALL if category is None else ManagementAction.SEARCH
        request = DatasetManagementMessage(action=action, category=category)
        self.last_response = await self.async_make_request(request)
        return self._parse_list_of_dataset_names_from_response(self.last_response)

    async def upload_to_dataset(self, dataset_name: str, paths: List[Path]) -> bool:
        """
        Upload data a dataset.

        Parameters
        ----------
        dataset_name : str
            The name of the dataset.
        paths : List[Path]
            List of one or more paths of files to upload or directories containing files to upload.

        Returns
        -------
        bool
            Whether uploading was successful
        """
        # TODO: *********************************************
        raise NotImplementedError('Function upload_to_dataset not implemented')


class DatasetExternalClient(DatasetClient,
                            MaasRequestClient[MaaSDatasetManagementMessage, MaaSDatasetManagementResponse]):
    """
    Client for authenticated communication sessions via ::class:`MaaSDatasetManagementMessage` instances.
    """

    # In particular needs - endpoint_uri: str, ssl_directory: Path
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _acquire_session_info(self, use_current_values: bool = True, force_new: bool = False):
        """
        Attempt to set the session information properties needed to submit a maas request.

        Parameters
        ----------
        use_current_values : bool
            Whether to use currently held attribute values for session details, if already not None (disregarded if
            ``force_new`` is ``True``).
        force_new : bool
            Whether to force acquiring a new session, regardless of data available is available on an existing session.

        Returns
        -------
        bool
            whether session details were acquired and set successfully
        """
        #logger.info("{}._acquire_session_info:  getting session info".format(self.__class__.__name__)
        if not force_new and use_current_values and self._session_id and self._session_secret and self._session_created:
            #logger.info('Using previously acquired session details (new session not forced)')
            return True
        else:
            #logger.info("Session from JobRequestClient: force_new={}".format(force_new))
            tmp = self._acquire_new_session()
            #logger.info("Session Info Return: {}".format(tmp))
            return tmp

    async def _async_acquire_session_info(self, use_current_values: bool = True, force_new: bool = False):
        if not force_new and use_current_values and self._session_id and self._session_secret and self._session_created:
            #logger.info('Using previously acquired session details (new session not forced)')
            return True
        else:
            #logger.info("Session from JobRequestClient: force_new={}".format(force_new))
            tmp = await self._async_acquire_new_session()
            #logger.info("Session Info Return: {}".format(tmp))
            return tmp

    def _update_after_valid_response(self, response: MaaSDatasetManagementResponse):
        """
        Perform any required internal updates immediately after a request gets back a successful, valid response.

        This provides a way of extending the behavior of this type specifically regarding the ::method:make_maas_request
        function. Any updates specific to the type, which should be performed after a request receives back a valid,
        successful response object, can be implemented here.

        Parameters
        ----------
        response : MaaSDatasetManagementResponse
            The response triggering the update.

        See Also
        -------
        ::method:make_maas_request
        """
        # TODO: think about if anything is needed for this
        pass

    async def create_dataset(self, name: str, category: DataCategory) -> bool:
        await self._async_acquire_session_info()
        # TODO: (later) consider also adding param for data to be added
        request = MaaSDatasetManagementMessage(session_secret=self.session_secret, action=ManagementAction.CREATE,
                                               dataset_name=name, category=category)
        self.last_response = await self.async_make_request(request)
        return self.last_response is not None and self.last_response.success

    async def list_datasets(self, category: Optional[DataCategory] = None) -> List[str]:
        await self._async_acquire_session_info()
        action = ManagementAction.LIST_ALL if category is None else ManagementAction.SEARCH
        request = MaaSDatasetManagementMessage(session_secret=self.session_secret, action=action, category=category)
        self.last_response = await self.async_make_request(request)
        return self._parse_list_of_dataset_names_from_response(self.last_response)

    async def upload_to_dataset(self, dataset_name: str, paths: List[Path]) -> bool:
        """
        Upload data a dataset.

        Parameters
        ----------
        dataset_name : str
            The name of the dataset.
        paths : List[Path]
            List of one or more paths of files to upload or directories containing files to upload.

        Returns
        -------
        bool
            Whether uploading was successful
        """
        # TODO: *********************************************
        raise NotImplementedError('Function upload_to_dataset not implemented')

    @property
    def errors(self):
        # TODO: think about this more
        return self._errors

    @property
    def info(self):
        # TODO: think about this more
        return self._info

    @property
    def warnings(self):
        # TODO: think about this more
        return self._warnings