import json

from dmod.communication import AuthClient, TransportLayerClient, WebSocketClient
from dmod.core.common import get_subclasses
from dmod.core.serializable import BasicResultIndicator, ResultIndicator
from dmod.core.meta_data import DataDomain
from .request_clients import DataServiceClient, JobClient
from .client_config import ClientConfig
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

    def __init__(self, client_config: ClientConfig, bypass_request_service: bool = False, *args, **kwargs):
        self._client_config = client_config
        self._data_service_client = None
        self._job_client = None
        self._bypass_request_service = bypass_request_service

        # TODO: this should (optionally) be a client multiplexer (once that is available) instead of a transport client
        #  (with a getter to actually get a transport client in either case)
        request_t_client_type = determine_transport_client_type(client_config.request_service.endpoint_protocol,
                                                                WebSocketClient)
        self._request_service_conn: TransportLayerClient = request_t_client_type(**client_config.request_service.dict())

        self._auth_client: AuthClient = AuthClient(transport_client=self._get_transport_client())

    @staticmethod
    def _extract_dataset_domain(**kwargs) -> DataDomain:
        """
        Extract a dataset domain implicitly or explicitly described within the given keyword args, like CLI params.

        Parameters
        ----------
        kwargs

        Other Parameters
        ----------------
        domain : DataDomain
            Optional parameter holding a complete, already existing domain object.
        domain_json : dict
            Optional parameter hold a serialized domain object.

        Returns
        -------
        DataDomain
            The extracted inflated domain object.

        Raises
        -------
        TypeError
            If a 'domain' keyword arg is present but of the wrong type.
        ValueError
            If a 'domain_file' arg is present but does not reference a file containing a serialized domain object.
        RuntimeError
            If neither 'domain' nor 'domain_file' args were present, and the keyword args as a whole could not be used
            as init params to create a domain object.
        """
        if kwargs.get('domain') is not None:
            domain = kwargs.pop('domain')
            if not isinstance(domain, DataDomain):
                raise TypeError(f"Object at 'domain' key was of type {domain.__class__.__name__}")
            else:
                return domain
        elif kwargs.get('domain_file') is not None:
            domain_file = kwargs.get('domain_file')
            try:
                if isinstance(domain_file, Path):
                    domain_file = Path(domain_file)
                with domain_file.open() as domain_file:
                    domain_json = json.load(domain_file)
            except Exception as e:
                raise ValueError(f"Failure with 'domain_file' `{domain_file!s}`; {e.__class__.__name__} - {e!s}")
            domain = DataDomain.factory_init_from_deserialized_json(domain_json)
            if not isinstance(domain, DataDomain):
                raise ValueError(f"Could not deserialize JSON in 'domain_file' `{domain_file!s}` to domain object")
            else:
                return domain
        else:
            try:
                return DataDomain(**kwargs)
            except Exception as e:
                raise RuntimeError(f"Could not inflate keyword params to object due to {e.__class__.__name__} - {e!s}")

    def _get_transport_client(self, **kwargs) -> TransportLayerClient:
        # TODO: later add support for multiplexing capabilities and spawning wrapper clients
        return self._request_service_conn

    @property
    def client_config(self) -> ClientConfig:
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
                try:
                    domain = self._extract_dataset_domain(**kwargs)
                except TypeError as e:
                    return BasicResultIndicator(success=False, reason="No Dataset Domain Provided",
                                                message=f"Invalid type provided for 'domain' param: {e!s} ")
                except (ValueError, RuntimeError) as e:
                    return BasicResultIndicator(success=False, reason="No Dataset Domain Provided", message=f"{e!s}")
                return await self.data_service_client.create_dataset(domain=domain, **kwargs)
            elif action == 'delete':
                return await self.data_service_client.delete_dataset(**kwargs)
            elif action == 'upload':
                return await self.data_service_client.upload_to_dataset(**kwargs)
            elif action == 'download':
                return await self.data_service_client.retrieve_from_dataset(**kwargs)
            elif action == 'list':
                return await self.data_service_client.get_dataset_names(**kwargs)
            elif action == 'items':
                return await self.data_service_client.get_dataset_item_names(**kwargs)
            else:
                raise ValueError(f"Unsupported data service action to {self.__class__.__name__}: {action}")
        except NotImplementedError:
            raise NotImplementedError(f"Impl of supported data action {action} not yet in {self.__class__.__name__}")

    @property
    def data_service_client(self) -> DataServiceClient:
        if self._data_service_client is None:
            if self.client_config.data_service is not None and self.client_config.data_service.active:
                t_client_type = determine_transport_client_type(self.client_config.data_service.endpoint_protocol)
                t_client = t_client_type(**self.client_config.data_service.dict())
                self._data_service_client = DataServiceClient(t_client, self._auth_client)
            else:
                self._data_service_client = DataServiceClient(self._get_transport_client(), self._auth_client)
        return self._data_service_client

    @property
    def job_client(self) -> JobClient:
        if self._job_client is None:
            self._job_client = JobClient(transport_client=self._get_transport_client(), auth_client=self._auth_client)
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

    def print_config(self):
        print(self.client_config.json(by_alias=True, exclude_none=True, indent=2))

    def validate_config(self):
        # TODO:
        raise NotImplementedError("Function validate_config not yet implemented")
