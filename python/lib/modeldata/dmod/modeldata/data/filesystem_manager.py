import json
import logging

from pathlib import Path
from typing import Optional, List, Set, Union, Any, Tuple

from dmod.core.dataset import Dataset, DatasetManager, DatasetType
from dmod.core.exception import DmodRuntimeError
from dmod.core.meta_data import DataCategory, DataDomain


class FilesystemDatasetManager(DatasetManager):
    """
    Dataset manager implementation for ``FILESYSTEM`` type datasets.

    The actual backing files are inherently tied to particular host, while job workers are not necessarily constrained
    to any particular host, this makes adding data tricky.  As such, ::method:`add_data` is not yet available and will
    raise a ::class:`NotImplementedError`.
    """

    _SUPPORTED_TYPES = {DatasetType.FILESYSTEM}

    @classmethod
    def _load_dataset_json_from_local_file(cls, reload_path: Path, file_basename: Optional[str]) -> dict:
        """
        Obtain and return the serialized JSON for a ::class:`Dataset` from a file within a local path.

        Parameters
        ----------
        reload_path : Path
            A local path, expected to have already been tested for existence, either of the serialized ::class:`Dataset`
            file itself or the parent directory of such a file.
        file_basename : Optional[str]
            The basename of the serialized ::class:`Dataset` file within ``reload_path`` when this path is a directory,
            or ``None`` otherwise.

        Returns
        -------
        dict
            The JSON dict that can be used to deserialize the desired :class:`Dataset` object.
        """
        if reload_path.is_dir():
            if file_basename is None:
                # TODO: look at whether there should be a default tried
                msg = "Cannot reload dataset from provided directory {} without also having a serialized file"
                raise DmodRuntimeError(msg.format(str(reload_path)))
            else:
                reload_path = reload_path.joinpath(file_basename)

        if not reload_path.is_file():
            msg = "Cannot reload dataset from non-existing reload file {}"
            raise DmodRuntimeError(msg.format(str(reload_path)))

        return json.loads(reload_path.read_text())

    # TODO: need to implement mechanism to sync across different nodes (and outside container probably), then add
    #  several method implementations that have been skipped at this point

    def __init__(self, serialized_files_directory: Optional[Path] = None, *args, **kwargs):
        """
        Initialize this instance.

        Parameters
        ----------
        serialized_files_directory : Optional[Path]
            Optional local directory containing serialized dataset files for datasets that should be reloaded.

        Keyword Params
        ----------
        datasets : Optional[Dict[str, Dataset]]
            Optional map of already-known datasets, forwarded to call to superclass init function.
        uuid : Optional[UUID]
            Optional, pre-determined UUID (e.g. when deserializing), forwarded to call to superclass init function.
        """
        super(FilesystemDatasetManager, self).__init__(*args, **kwargs)
        if serialized_files_directory is not None:
            if not serialized_files_directory.is_dir():
                msg = "Invalid reload directory {} provided when initializing new {} object"
                raise DmodRuntimeError(msg.format(str(serialized_files_directory), self.__class__.__name__))
            for file in [f for f in serialized_files_directory.iterdir() if f.is_file()]:
                try:
                    self.reload(reload_from=str(file))
                except Exception as e:
                    msg = "{} could not reload a dataset from {} due to {} ({})"
                    logging.warning(msg.format(self.__class__.__name__, str(file), e.__class__.__name__, str(e)))

    def add_data(self, dataset_name: str, dest: str, data: Optional[bytes] = None, source: Optional[str] = None,
                 is_temp: bool = False, **kwargs) -> bool:
        """
        Add raw data or data from one or more files to this dataset.

        Parameters
        ----------
        dataset_name : str
            The dataset to which to add data.
        dest : str
            A path-like string that provides information on the location within the dataset where the data should be
            added when either adding byte string data from ``data`` or when adding from a single file specified in
            ``source`` (ignored when adding from files within a ``source`` directory).
        data : Optional[bytes]
            Optional encoded byte string containing data to be inserted into the data set; either this or ``source``
            must be provided.
        source : Optional[str]
            Optional string specifying either a source file containing data to be added, or a directory containing
            multiple files to be added.
        is_temp : bool
            Indication of whether this item should be temporary, and thus given a 1-hour retention config.
        kwargs
            Implementation-specific params for representing the data and details of how it should be added.

        Keyword Args
        ----------
        directory_root : Path
            The source data directory level that corresponds to the dataset's root directory.

        Returns
        -------
        bool
            Whether the data was added successfully or not.
        """
        msg = "Adding data to datasets managed by {} type not currently supported"
        raise NotImplementedError(msg.format(self.__class__.__name__))

    def create(self, name: str, category: DataCategory, domain: DataDomain, is_read_only: bool,
               initial_data: Optional[str] = None) -> Dataset:
        msg = "Creating datasets managed by {} type not currently supported"
        raise NotImplementedError(msg.format(self.__class__.__name__))

    def combine_partials_into_composite(self, dataset_name: str, item_name: str, combined_list: List[str]) -> bool:
        msg = "Combining datasets managed by {} type not currently supported"
        raise NotImplementedError(msg.format(self.__class__.__name__))

    @property
    def data_chunking_params(self) -> Optional[Tuple[str, str]]:
        msg = "Getting data chunking params for datasets managed by {} type not currently supported"
        raise NotImplementedError(msg.format(self.__class__.__name__))

    def delete(self, dataset: Dataset, **kwargs) -> bool:
        msg = "Deleting datasets managed by {} type not currently supported"
        raise NotImplementedError(msg.format(self.__class__.__name__))

    def get_data(self, dataset_name: str, item_name: str, **kwargs) -> Union[bytes, Any]:
        msg = "Getting data from datasets managed by {} type not currently supported"
        raise NotImplementedError(msg.format(self.__class__.__name__))

    def list_files(self, dataset_name: str, **kwargs) -> List[str]:
        msg = "Getting list of files for datasets managed by {} type not currently supported"
        raise NotImplementedError(msg.format(self.__class__.__name__))

    def reload(self, reload_from: str, serialized_item: Optional[str] = None) -> Dataset:
        """
        Reload a ::class:`Dataset` object from a serialized copy at a specified location.

        Parameters
        ----------
        reload_from : str
            A string form of a ::class:`Path`, either to the serialized dataset file itself or that file's parent
            directory.
        serialized_item : Optional[str]
            Optional string for specifying the serialized file to reload from ``reload_from`` is a path to a directory
            (default: ``None``).

        Returns
        -------
        Dataset
            A new dataset object, loaded from a previously serialized dataset.
        """
        # If the param represents an existing path, then assume we need to reload from something in the filesystem
        reload_path = Path(reload_from)
        if reload_path.exists():
            dataset_json = self._load_dataset_json_from_local_file(reload_path, serialized_item)
        # TODO: look at options such as being able to load from item saved in special object store bucket or Redis
        # For now at least, otherwise, assume there is an error
        else:
            msg = "Cannot determine how to reload dataset from given arguments {} and {}"
            raise DmodRuntimeError(msg.format(reload_from, serialized_item if serialized_item else 'None'))

        # If we can safely infer it, make sure the "type" key is set in cases when it is missing
        if len(self.supported_dataset_types) == 1 and Dataset._KEY_TYPE not in dataset_json:
            dataset_json[Dataset._KEY_TYPE] = list(self.supported_dataset_types)[0].name

        dataset = Dataset.factory_init_from_deserialized_json(dataset_json)
        if dataset is None:
            raise DmodRuntimeError("Unable to reload dataset: could not deserialize a object from the loaded JSON data")
        dataset.set_manager(self)
        self.datasets[dataset.name] = dataset
        return dataset

    @property
    def supported_dataset_types(self) -> Set[DatasetType]:
        return self._SUPPORTED_TYPES
