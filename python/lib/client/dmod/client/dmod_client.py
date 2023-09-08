import json

from dmod.communication import AuthClient, TransportLayerClient, WebSocketClient
from dmod.core.common import get_subclasses
from dmod.core.serializable import ResultIndicator
from dmod.core.meta_data import DataDomain
from .request_clients import DataServiceClient, JobClient
from .client_config import YamlClientConfig
from pathlib import Path
from typing import Type


def determine_transport_client_type(protocol: str,
                                    *prioritized_subtypes: Type[TransportLayerClient]) -> Type[TransportLayerClient]:
    """
    Determine the specific subclass type of ::class:`TransportLayerClient` appropriate for a specified URI protocol.

    To allow for control when there are potential multiple subtypes that would support the same protocol, specific
    ::class:`TransportLayerClient` subclasses can be given as variable positional arguments. These will be prioritized
    and examined first.  After that, the order of examined subtypes is subject to the runtime order of the search for
    concrete ::class:`TransportLayerClient` subclasses.

    Parameters
    ----------
    protocol : str
        A URI protocol substring value.
    *prioritized_subtypes : Type[TransportLayerClient]
        Specific subclass type(s) to prioritize in the event of any duplication of protocol value(s) across subtypes.

    Returns
    -------
    Type[TransportLayerClient]
        The appropriate type of ::class:`TransportLayerClient`.
    """
    if not protocol.strip():
        raise ValueError("Cannot determine transport client type for empty protocol value")
    elif any((s for s in prioritized_subtypes if not issubclass(s, TransportLayerClient))):
        raise TypeError("Bad values for prioritized types received when attempting to determine transport client type")

    def _get_subclasses(class_val):
        return set([s for s in class_val.__subclasses__() if not s.__abstractmethods__]).union(
            [s for c in class_val.__subclasses__() for s in get_subclasses(c) if not s.__abstractmethods__])

    #for subtype in (*prioritized_subtypes, *get_subclasses(TransportLayerClient)):
    for subtype in (*prioritized_subtypes, *_get_subclasses(TransportLayerClient)):
        if subtype.get_endpoint_protocol_str(True) == protocol or subtype.get_endpoint_protocol_str(False) == protocol:
            return subtype
    raise RuntimeError(f"No subclass of `{TransportLayerClient.__name__}` found supporting protocol '{protocol}'")


class DmodClient:

    def __init__(self, client_config: YamlClientConfig, bypass_request_service: bool = False, *args, **kwargs):
        self._client_config = client_config
        self._data_service_client = None
        self._job_client = None
        self._bypass_request_service = bypass_request_service

        self._transport_client: TransportLayerClient = WebSocketClient(endpoint_uri=self.requests_endpoint_uri,
                                                                       ssl_directory=self.requests_ssl_dir)
        self._auth_client: AuthClient = AuthClient(transport_client=self._transport_client)

    @property
    def client_config(self):
        return self._client_config

    async def data_service_action(self, action: str, **kwargs) -> ResultIndicator:
        """
        Perform a supported data service action.

        Parameters
        ----------
        action : str
            The action selection of interest.
        kwargs

        Returns
        -------
        ResultIndicator
            An indication of whether the requested action was performed successfully.
        """
        try:
            if action == 'create':
                # Do a little extra here to get the domain
                if 'domain' in kwargs:
                    domain = kwargs.pop('domain')
                elif 'domain_file' in kwargs:
                    with kwargs['domain_file'].open() as domain_file:
                        domain_json = json.load(domain_file)
                    domain = DataDomain.factory_init_from_deserialized_json(domain_json)
                else:
                    domain = DataDomain(**kwargs)
                return await self.data_service_client.create_dataset(domain=domain, **kwargs)
            elif action == 'delete':
                return await self.data_service_client.delete_dataset(**kwargs)
            elif action == 'upload':
                return await self.data_service_client.upload_to_dataset(**kwargs)
            elif action == 'download':
                return await self.data_service_client.retrieve_from_dataset(**kwargs)
            elif action == 'list_datasets':
                return await self.data_service_client.get_dataset_names(**kwargs)
            elif action == 'list_items':
                return await self.data_service_client.get_dataset_items(**kwargs)
            else:
                raise ValueError(f"Unsupported data service action to {self.__class__.__name__}: {action}")
        except NotImplementedError:
            raise NotImplementedError(f"Impl of supported data action {action} not yet in {self.__class__.__name__}")

    @property
    def data_service_client(self) -> DataServiceClient:
        if self._data_service_client is None:
            if self._bypass_request_service:
                if self.client_config.dataservice_endpoint_uri is None:
                    raise RuntimeError("Cannot bypass request service without data service config details")
                self._data_service_client = DataServiceClient(self._transport_client)
            else:
                self._data_service_client = DataServiceClient(self._transport_client, self._auth_client)
        return self._data_service_client

    @property
    def job_client(self) -> JobClient:
        if self._job_client is None:
            transport_client = WebSocketClient(endpoint_uri=self.requests_endpoint_uri, ssl_directory=self.requests_ssl_dir)
            self._job_client = JobClient(transport_client=transport_client, auth_client=AuthClient(transport_client))
        return self._job_client

    async def execute_job(self, workflow: str, **kwargs) -> ResultIndicator:
        """
        Submit a requested job defined by the provided ``kwargs``.

        Currently supported job workflows are:
            - ``ngen`` : submit a job request to execute a ngen model exec job
            - ``ngen_cal`` : submit a job request to execute a ngen-cal model calibration job
            - ``from_json`` : submit a provided job request, given in serialized JSON form
            - ``from_file`` : submit a provided job request, serialized to JSON form and saved in the given file

        For most supported workflows, ``kwargs`` should contain necessary params for initializing a request object of
        the correct type.  However, for ``workflow`` values ``from_json`` or ``from_file``, ``kwargs`` should instead
        contain params for deserializing the right type of request, either directly or from a provided file.

        Parameters
        ----------
        workflow: str
            The type of workflow, as a string, which should correspond to parsed CLI options.
        kwargs
            Dynamic keyword args used to produce a request object to initiate a job, which vary by workflow.

        Returns
        -------
        The result of the request to run the job.
        """
        if workflow == 'from_json':
            return await self.job_client.submit_request_from_json(**kwargs)
        if workflow == 'from_file':
            return await self.job_client.submit_request_from_file(**kwargs)
        if workflow == 'ngen':
            return await self.job_client.submit_ngen_request(**kwargs)
        elif workflow == "ngen_cal":
            return await self.job_client.submit_ngen_cal_request(**kwargs)
        else:
            raise ValueError(f"Unsupported job execution workflow {workflow}")
        
    async def job_command(self, command: str, **kwargs) -> ResultIndicator:
        """
        Submit a request that performs a particular job command.

        Supported commands are:
            - ``list`` : get a list of ids of existing jobs (supports optional ``jobs_list_active_only`` in ``kwargs``)
            - ``info`` : get information on a particular job (requires ``job_id`` in ``kwargs``)
            - ``release`` : request allocated resources for a job be released (requires ``job_id`` in ``kwargs``)
            - ``status`` : get the status of a particular job (requires ``job_id`` in ``kwargs``)
            - ``stop`` : request the provided job be stopped (requires ``job_id`` in ``kwargs``)

        Parameters
        ----------
        command : str
            A string indicating the particular job command to run.
        kwargs
            Other required/optional parameters as needed/desired for the particular job command to be run.

        Returns
        -------
        ResultIndicator
            An indicator of the results of attempting to run the command.
        """
        try:
            if command == 'info':
                return await self.job_client.request_job_info(**kwargs)
            elif command == 'list':
                return await self.job_client.request_jobs_list(**kwargs)
            elif command == 'release':
                return await self.job_client.request_job_release(**kwargs)
            elif command == 'status':
                return await self.job_client.request_job_status(**kwargs)
            elif command == 'stop':
                return await self.job_client.request_job_stop(**kwargs)
            else:
                raise ValueError(f"Unsupported job command to {self.__class__.__name__}: {command}")
        except NotImplementedError:
            raise NotImplementedError(f"Supported command {command} not yet implemented by {self.__class__.__name__}")

    @property
    def requests_endpoint_uri(self) -> str:
        return self.client_config.requests_endpoint_uri

    @property
    def requests_ssl_dir(self) -> Path:
        return self.client_config.requests_ssl_dir

    def print_config(self):
        print(self.client_config.print_config())

    def validate_config(self):
        # TODO:
        raise NotImplementedError("Function validate_config not yet implemented")
