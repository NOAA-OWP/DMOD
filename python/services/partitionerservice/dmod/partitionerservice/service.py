import asyncio
import json
import logging
import websockets
from pathlib import Path
from typing import Union
from websockets import WebSocketServerProtocol
from dmod.communication import InvalidMessageResponse, PartitionRequest, PartitionResponse, WebSocketInterface
from dmod.scheduler import SimpleDockerUtil

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)


class PartitionerHandler(WebSocketInterface):
    """
    Communication handler for the Partitioner Service, implemented with WebSocketInterface.

    To perform partitioning, an instance will run a Docker container with the partitioning executable.  Because the
    executable expects to read an input file and write to an output file, a Docker volume is mounted inside the
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
        # Check that path exists and is directory
        if not self._data_volume_storage_dir.is_dir():
            msg = '{} requires local path to volume storage, but provided path {} is not an existing directory'.format(
                self.__class__.__name__, self._data_volume_storage_dir)
            raise RuntimeError(msg)

    def _execute_partitioner_container(self, catchment_file_basename: str, output_file_basename: str,
                                       num_partitions: int, num_catchments: int):
        """
        Execute the partitioner Docker container and executable.

        Execute the partitioner Docker container and executable.  This includes mounting the necessary volume, as
        indicated by ::attribute:`data_volume_name`, and constructing an appropriate ``command`` for the entrypoint from
        the function parameters.

        The image selected is based on an init parameter and stored in a "private" attribute.

        Parameters
        ----------
        catchment_file_basename : str
            The basename of the input catchment data file for the partitioner, which should exist in the data volume.

        output_file_basename : str
            The basename of the output file from the partitioner, which will be written to the mounted data volume.

        num_partitions : int
            The number of partitions to request of the partitioner.

        num_catchments : int
            The number of catchments in the data, which is a required arg when running the partitioner.

        Raises
        -------
        RuntimeError
            Raised if execution fails, containing as a nested ``cause`` the encountered, more specific error/exception.
        """
        try:
            container_data_dir = '/data'

            # args are catchment_data_file, output_file, num_partitions, num_catchments
            command = list()
            command.append(container_data_dir + '/' + catchment_file_basename)
            command.append(container_data_dir + '/' + output_file_basename)
            command.append(str(num_partitions))
            command.append(str(num_catchments))

            volumes = dict()
            volumes[self.data_volume_name] = container_data_dir

            self._docker_util.run_container(image=self._image_name, volumes=volumes, command=command)
        except Exception as e:
            msg = 'Could not successfully execute partitioner Docker container: {}'.format(str(e))
            raise RuntimeError(msg) from e

    def _process_request(self, request: PartitionRequest) -> PartitionResponse:
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
            cat_data_basename = 'catchment_data_{}.geojson'.format(request.uuid)
            output_file_basename = 'output_{}.txt'.format(request.uuid)
            self._write_catchment_data_to_volume(request.catchment_data, cat_data_basename)
            self._execute_partitioner_container(cat_data_basename, output_file_basename, request.num_partitions,
                                                request.num_catchments)
            partitioner_output_json = self._read_and_serialize_partitioner_output(output_file_basename)
            return PartitionResponse(success=True, reason='Partitioning Complete', data=partitioner_output_json)
        except RuntimeError as e:
            return PartitionResponse(success=False, reason=e.__cause__.__class__.__name__, message=str(e))

    def _read_and_serialize_partitioner_output(self, output_file_basename: str) -> dict:
        try:
            with open(self.data_volume_storage_dir.joinpath(output_file_basename)) as output_data_file:
                return json.load(output_data_file)
        except Exception as e:
            msg = 'Could not read partitioner Docker container output file: {}'.format(str(e))
            raise RuntimeError(msg) from e

    def _write_catchment_data_to_volume(self, catchment_data_json: dict, catchment_data_file_basename: str):
        """
        Write catchment data to a file in the Docker volume to be mounted into a partitioner container.

        Since the partitioning executable deals with files as inputs and outputs, these must be in a mounted Docker
        volume in the container to be externally accessible.  This includes the input catchment data.

        This function writes catchment data to a file with the given basename.  The file is written to the local storage
        directory of the involved Docker data volume, as stored in ::attribute:`data_volume_storage_dir`.   This is
        required at instance init, with checks to ensure it is an existing directory.

        Parameters
        ----------
        catchment_data_json : dict
            The JSON data to be written to a volume file.

        catchment_data_file_basename
            The basename of the desired file to be written inside the local volume storage directory.

        Raises
        -------
        RuntimeError
            Raised if writing fails, containing as a nested ``cause`` the encountered, more specific error/exception.
        """
        try:
            catchment_data_file = self.data_volume_storage_dir.joinpath(catchment_data_file_basename)
            catchment_data_file.write_text(str(catchment_data_json))
        except Exception as e:
            msg = 'Failed to write partitioner catchment data to container Docker volume: {}'.format(str(e))
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
                response = self._process_request(request)
                await websocket.send(str(response))

        except TypeError as te:
            logging.error("Problem with object types when processing received message", te)
        except websockets.exceptions.ConnectionClosed:
            logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
            logging.info("Cancelling listener task")
