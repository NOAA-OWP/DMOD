import asyncio
import json
import logging
import websockets
from pathlib import Path
from typing import Union
from websockets import WebSocketServerProtocol
from dmod.communication import InvalidMessageResponse, PartitionRequest, PartitionResponse, WebSocketInterface
from dmod.modeldata.hydrofabric import HydrofabricFilesManager
from dmod.scheduler import SimpleDockerUtil

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)


class PartitionerHandler(WebSocketInterface, HydrofabricFilesManager):
    """
    Communication handler for the Partitioner Service, implemented with WebSocketInterface.

    To perform partitioning, an instance will run a Docker container with the partitioning executable.  Because the
    executable expects to read input files and write to an output file, a Docker volume is mounted inside the
    container.

    It is supported for an instance to itself be run inside a container.  However, it must also be able to access the
    contents of the aforementioned Docker data volume, to create the partitioner input files and extract and return the
    partitioner's output to requesters.  As such, it is assumed that management of the volume is handled externally.
    An instance only requires the name of an already-existing volume and the volume's storage directory path.  This will
    be the volume mount target of the instance's container in cases when one exists, since the volume will need to have
    been mounted by that container also in order to provide access.
    """

    def __init__(self, listen_port: int, image_name: str, data_volume_name: str, volume_storage_dir: Union[str, Path],
                 *args, **kwargs):
        """
        Initialize with data volume details and any user defined custom server config.

        Parameters
        ----------
        data_volume_name
        volume_storage_dir
        args
        kwargs

        Raises
        ----------
        docker.errors.NotFound
            Raised if the expected data volume does not exist.
        """
        super().__init__(port=listen_port, *args, **kwargs)
        HydrofabricFilesManager.__init__(self)
        self._image_name = image_name
        self._docker_util = SimpleDockerUtil()
        # TODO: probably need to check that image exists or can be pulled (and then actually pull)
        self._data_volume_name = data_volume_name
        # Don't do anything with it, but get the volume to make sure it exists (an exception occurs otherwise)
        self._docker_util.docker_client.volumes.get(self._data_volume_name)
        if isinstance(volume_storage_dir, Path):
            self._data_volume_storage_dir = volume_storage_dir
        else:
            self._data_volume_storage_dir = Path(volume_storage_dir)
        self._generated_partition_configs_dir = self._data_volume_storage_dir / 'generated_partition_configs'
        if not self._generated_partition_configs_dir.exists():
            self._generated_partition_configs_dir.mkdir()
        # Check that path exists and is directory
        if not self._data_volume_storage_dir.is_dir():
            msg = '{} requires local path to volume storage, but provided path {} is not an existing directory'.format(
                self.__class__.__name__, self._data_volume_storage_dir)
            raise RuntimeError(msg)
        # Make sure we load what hydrofabrics are supported for partitioning
        self.find_hydrofabrics()
        # Go ahead and lazy load the first one of these so it is cached
        self.get_hydrofabric_uid(0)

    def _execute_partitioner_container(self, catchment_file_relative: str, nexus_file_relative: str,
                                       output_file_relative: str, num_partitions: int, nexus_id_subset_str: str = '',
                                       catchment_id_subset_str: str = ''):
        """
        Execute the partitioner Docker container and executable.

        Execute the partitioner Docker container and executable.  This includes mounting the necessary volume, as
        indicated by ::attribute:`data_volume_name`, and constructing an appropriate ``command`` for the entrypoint from
        the function parameters.

        The image selected is based on an init parameter and stored in a "private" attribute.

        Parameters
        ----------
        catchment_file_relative : str
            The path to the input catchment data file for the partitioner, relative to the data volume mount point.
        nexus_file_relative : str
            The path to the input nexus data file for the partitioner, relative to the data volume mount point.
        output_file_relative : str
            The path to the output partition config file for the partitioner, relative to the data volume mount point.
        num_partitions : int
            The number of partitions to request of the partitioner.
        nexus_id_subset_str : str
            The comma separated string of the subset of nexuses to include in partitions, or empty string by default.
        catchment_id_subset_str : str
            The comma separated string of the subset of catchments to include in partitions, or empty string by default.

        Raises
        -------
        RuntimeError
            Raised if execution fails, containing as a nested ``cause`` the encountered, more specific error/exception.
        """
        try:
            container_data_dir = '/data'

            # args are catchment_data_file, nexus_data_file, output_file, num_partitions, nexus_subset, catchment_subset
            command = list()
            command.append(container_data_dir + '/' + catchment_file_relative)
            command.append(container_data_dir + '/' + nexus_file_relative)
            command.append(container_data_dir + '/' + output_file_relative)
            command.append(str(num_partitions))
            command.append(nexus_id_subset_str)
            command.append(catchment_id_subset_str)

            volumes = dict()
            volumes[self.data_volume_name] = container_data_dir

            self._docker_util.run_container(image=self._image_name, volumes=volumes, command=command)
        except Exception as e:
            msg = 'Could not successfully execute partitioner Docker container: {}'.format(str(e))
            raise RuntimeError(msg) from e

    async def _process_request(self, request: PartitionRequest) -> PartitionResponse:
        """
        Process a received request and return a response.

        Process a received request by attempting to run the partitioner via a Docker container.  Write partitioner input
        data from the request to the data volume first, then run the partitioner.  When successful, read the output and
        use in the created response object.

        When unsuccessful, include details on the error in the ``reason`` and ``message`` of the response.

        Parameters
        ----------
        request : PartitionRequest
            The incoming request for partitioning.

        Returns
        -------
        PartitionResponse
            The generated response based on success or failure.
        """
        try:
            hydrofabric_index = await self.async_find_hydrofabric_by_uid(request.hydrofabric_hash)
            tuple_of_files = self.get_hydrofabric_files_tuple(hydrofabric_index)

            if len(tuple_of_files) != 3:
                raise RuntimeError("Unsupported type of hydrofabric with {} files".format(len(tuple_of_files)))

            output_file_basename = 'output_{}.txt'.format(request.uuid)
            output_file_path = self.generated_partition_configs_dir / output_file_basename

            # Get relative file paths from self._data_volume_storage_dir, to use from container's mount point
            catchment_rel_path = str(tuple_of_files[0].relative_to(self._data_volume_storage_dir))
            nexus_rel_path = str(tuple_of_files[1].relative_to(self._data_volume_storage_dir))
            output_rel_path = str(output_file_path.relative_to(self._data_volume_storage_dir))

            self._execute_partitioner_container(catchment_rel_path, nexus_rel_path, output_rel_path,
                                                request.num_partitions)

            partitioner_output_json = self._read_and_serialize_partitioner_output(output_file_path)
            # TODO: should we clean up the generated file?
            #output_file_path.unlink()
            return PartitionResponse(success=True, reason='Partitioning Complete', data=partitioner_output_json)
        except RuntimeError as e:
            return PartitionResponse(success=False, reason=e.__cause__.__class__.__name__, message=str(e))

    def _read_and_serialize_partitioner_output(self, output_file: Path) -> dict:
        try:
            with output_file.open() as output_data_file:
                return json.load(output_data_file)
        except Exception as e:
            msg = 'Could not read partitioner Docker container output file: {}'.format(str(e))
            raise RuntimeError(msg) from e

    @property
    def data_volume_name(self) -> str:
        """
        The name of the Docker data volume.

        The name of the Docker volume that is to be provided to created containers that run the actual partitioning
        executable.  The volume will be mounted within containers and will be where the required catchment data file
        for the executable and the executable's output are written.

        Returns
        -------
        str
            The name of the Docker data volume for partition execution containers.
        """
        return self._data_volume_name

    @property
    def data_volume_storage_dir(self) -> Path:
        """
        The local path to the directory for the Docker data volume.

        This must exist and be a directory.

        Returns
        -------
        Path
            The local path to the directory for the Docker data volume.
        """
        return self._data_volume_storage_dir

    @property
    def generated_partition_configs_dir(self) -> Path:
        """
        The local path to the subdirectory within the Docker data volume where partition configs are generated.

        This will be the directory in which partitioner container will create partition config files.  As such, it will
        be an immediate subdirectory of ::attribute:`data_volume_storage_dir`.

        The directory is created if it does not already exist when an instance is initialized.

        Returns
        -------
        Path
            The local path to the subdirectory within the Docker data volume where partition configs are generated.
        """
        return self._generated_partition_configs_dir

    @property
    def hydrofabric_data_root_dir(self) -> Path:
        """
        Get the ancestor data directory under which files for managed hydrofabrics are located.

        For this type, this is the ::attribute:`data_volume_storage_dir`.

        Returns
        -------
        Path
            The ancestor data directory under which files for managed hydrofabrics are located, which is
            ::attribute:`data_volume_storage_dir`.
        """
        return self.data_volume_storage_dir

    async def listener(self, websocket: WebSocketServerProtocol, path):
        """
        Listen for and process partitioning requests.

        Parameters
        ----------
        websocket : WebSocketServerProtocol
            Websocket over which the request was sent and response should be sent.

        path

        Returns
        -------

        """
        try:
            message = await websocket.recv()
            request: PartitionRequest = PartitionRequest.factory_init_from_deserialized_json(json.loads(message))
            if request is None:
                err_msg = "Unrecognized message format received over {} websocket (message: `{}`)".format(
                    self.__class__.__name__, message)
                response = InvalidMessageResponse(data={'message_content': message})
                await websocket.send(str(response))
                raise TypeError(err_msg)
            else:
                response = await self._process_request(request)
                await websocket.send(str(response))

        except TypeError as te:
            logging.error("Problem with object types when processing received message", te)
        except websockets.exceptions.ConnectionClosed:
            logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
            logging.info("Cancelling listener task")
