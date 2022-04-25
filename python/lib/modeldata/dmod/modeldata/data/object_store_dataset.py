import io
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, TimeRange
from .dataset import Dataset, DatasetManager
from datetime import datetime
from minio import Minio
from minio.api import ObjectWriteResult
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type
from uuid import UUID


class ObjectStoreDataset(Dataset):
    """
    Dataset for which data is contained within an object store bucket.

    The backing object store bucket will have the same name as the dataset itself.

    The ::attribute:`access_location` property is based on the object store hostname and the name of the backing bucket,
    with these delimited with ::attribute:`_ACCESS_LOCATION_DELIMITER`.
    """

    _ACCESS_LOCATION_DELIMITER = "/"
    """ Delimiting separator for ::attribute:`access_location` value. """

    @classmethod
    def additional_init_param_deserialized(cls, json_obj: dict) -> Dict[str, Any]:
        """
        Deserialize any other params needed for this type's init function, returning in a map for ``kwargs`` use.

        The main ::method:`factory_init_from_deserialized_json` class method for the base ::class:`Dataset` type handles
        a large amount of the work for deserialization.  However, subtypes could have additional params they require
        in their ::method:`__init__`.  This function should do this deserialization work for any subtype, and return a
        deserialized dictionary.  The keys should be the names of the relevant ::method:`__init__` parameters.

        In the event a type's ::method:`__init__` method takes no additional params beyond the base type, its
        implementation of this function should return an empty dictionary.

        Any types with an init that does not have one or more of the params of the base type's init should fully
        override ::method:`factory_init_from_deserialized_json`.

        Parameters
        ----------
        json_obj : dict
            The serialized form of the object that is a subtype of ::class:`Dataset`.

        Returns
        -------
        Dict[str, Any]
            A dictionary of ``kwargs`` for those init params and values beyond what the base type uses.
        """
        # TODO: update docstring a bit for this once finalized nothing is needed
        return dict()

    def __init__(self, name: str, category: DataCategory, data_domain: DataDomain, access_location: str,
                 uuid: Optional[UUID] = None, manager: Optional[DatasetManager] = None,
                 manager_uuid: Optional[UUID] = None, is_read_only: bool = True, expires: Optional[datetime] = None,
                 derived_from: Optional[str] = None, derivations: Optional[List[str]] = None,
                 created_on: Optional[datetime] = None, last_updated: Optional[datetime] = None):
        super(ObjectStoreDataset, self).__init__(name, category, data_domain, access_location, uuid, manager,
                                                 manager_uuid, is_read_only, expires, derived_from, derivations,
                                                 created_on, last_updated)
        # TODO: remove this explicit override of superclass __init__ if there ends up being nothing type-specific in it

    def add_file(self, file: Path, add_relative_to: Optional[Path] = None) -> bool:
        """

        Parameters
        ----------
        file
        add_relative_to

        Returns
        -------
        bool
            Whether the file was added successfully
        """
        bucket_root = file.parent if add_relative_to is None else add_relative_to
        return self.manager.add_data(dataset_name=self.name, file=file, bucket_root=bucket_root)

    def add_files(self, directory: Path, bucket_root: Optional[Path] = None) -> bool:
        """
        Add all files in the given directory to this existing object store.

        Function, via its manager, adds all files within the passed directory to its backing object store.  As the
        backing store cannot replicate the file system structure, especially nested directories, it simulates this by
        encoding it into the store file object names.  Only the structure relative to a corresponding "root" directory
        is encoded, which may be indicated using the ``bucket_root`` param.  The root level of the backing object store
        bucket is assumed to correspond to ``directory`` itself if ``bucket_root`` is ``None``, which is the default.

        E.g. perhaps there exists the ``dataset_1/`` directory, with structure and contents:

            dataset_1/
            dataset_1/file_1
            dataset_1/file_2
            dataset_1/subdir_a/
            dataset_1/subdir_a/file_a_1
            dataset_1/subdir_a/file_a_2
            dataset_1/subdir_b/
            dataset_1/subdir_b/file_b_1

        If the ``bucket_root` was set to ``dataset_1``, then ``dataset_1/file_1`` would not receive a subdirectory
        prefix to its object name, while ``dataset_1/subdir_a/file_a_1`` would receive a prefix encoding that it was
        within the ``subdir_a`` directory under the bucket root.

        Parameters
        ----------
        directory : Path
            A path to a directory, for which all contents should be added to this dataset.
        bucket_root : Optional[Path]
            An optional directory that corresponds to the dataset's root level, for purposes of naming objects in a way
            that simulates a nested directory structure (when ``None``, replaced with ``directory`` itself).

        Returns
        -------
        bool
            Whether the data was added successfully.

        See Also
        -------
        ::attribute:`manager`
        ::method:`ObjectStoreDatasetManager.add_data`
        """
        return self.manager.add_data(dataset_name=self.name, directory=directory,
                                     bucket_root=(directory if bucket_root is None else bucket_root))

    @property
    def files(self) -> List[str]:
        """
        List of files in this dataset, relative to dataset root.

        Returns
        -------
        List[str]
            List of files in this dataset, relative to dataset root.
        """
        return self.manager.list_files(self.name, bucket_name=self.name)


class ObjectStoreDatasetManager(DatasetManager):
    """
    Dataset manager implementation specifically for ::class:`ObjectStoreDataset` instances.
    """

    _SUPPORTED_TYPES = {ObjectStoreDataset}
    """ Supported dataset types set, which is always ::class:`ObjectStoreDataset` for this manager subtype. """
    _SERIALIZED_OBJ_NAME_TEMPLATE = "{}_serialized.json"
    """ The name of the file/object for serialized versions of datasets, within a dataset's bucket. """

    def __init__(self, obj_store_host_str: str, access_key: Optional[str] = None, secret_key: Optional[str] = None,
                 datasets: Optional[Dict[str, Dataset]] = None):
        super(ObjectStoreDatasetManager, self).__init__(datasets)
        # TODO: add checks to ensure all datasets passed to this type are ObjectStoreDataset
        self._obj_store_host_str = obj_store_host_str
        # TODO (later): may need to look at turning this back on
        try:
            self._client = Minio(endpoint=obj_store_host_str, access_key=access_key, secret_key=secret_key, secure=False)
            # For any buckets that have the standard serialized object (i.e., were for datasets previously), reload them
            for bucket_name in self.list_buckets():
                self._load_from_existing_bucket(bucket_name)
        except Exception as e:
            self._errors.append(e)
            # TODO: consider if we should not re-throw this (which would likely force us to ensure users checked this)
            raise e

    def _decode_object_name_to_file_path(self, object_name: str) -> str:
        """
        Reverse the object name encoding of nested file names.

        This essentially just decodes the encoding performed by ::method:`_push_file`.

        Parameters
        ----------
        object_name : str
            The name of the object storing some previously uploaded file data.

        Returns
        -------
        str
            The decoded file name that reflects any subdirectory structure.

        See Also
        -------
        ::method:`_push_file`
        """
        return "/".join(object_name.split(self._OBJECT_NAME_SEPARATOR))

    def _gen_dataset_serial_obj_name(self, dataset_name: str) -> str:
        return self._SERIALIZED_OBJ_NAME_TEMPLATE.format(dataset_name)

    # TODO: add stuff for threading
    def _push_file(self, bucket_name: str, file: Path, bucket_root: Optional[Path] = None, dest: Optional[str] = None,
                   do_checks: bool = True, resync_serialized: bool = True) -> ObjectWriteResult:
        """
        Push a file to a bucket.

        A file may be pushed either to an explicitly named object (via ``dest``) or to an object with a name derived
        from a ``bucket_root`` as described below.  If neither is provided, the file will be pushed to an object named
        using the basename of the source file.

        Buckets can simulate subdirectories by encoding relative directory structure into object names.  This relative
        structure is based on a bucket "root" directory, corresponding to the directory used to create this dataset.

        E.g. perhaps there exists the ``dataset_1/`` directory, which needs to be uploaded to a dataset, with
        structure:

            dataset_1/
            dataset_1/file_1
            dataset_1/file_2
            dataset_1/subdir_a/
            dataset_1/subdir_a/file_a_1
            dataset_1/subdir_a/file_a_2
            dataset_1/subdir_b/
            dataset_1/subdir_b/file_b_1

        Assume ``dataset_1/`` is the "root", and there already exists a ``file_1`` object in the bucket for
        ``dataset_1/file_1``.  When it is time to for this method to push ``dataset_1/subdir_a/file_a_1``, the file is
        associated with an object name that encodes the subdirectory structure:  ``subdir_a___file_a_1``.  The separator
        comes from the class variable ::attribute:`_OBJECT_NAME_SEPARATOR`.

        Parameters
        ----------
        bucket_name : str
            The name of the existing bucket to push to.
        file : Path
            The path to a non-directory file to push to the bucket.
        bucket_root : Path
            Optional directory level that corresponds to the bucket's root level, for object naming purposes.
        dest : Optional[str]
            An optional explicit name of the destination object that should receive this data.
        do_checks : bool
            Whether to do sanity checks on the local file and bucket root (``True`` by default).
        resync_serialized : bool
            Whether to resync the serialized file object within the dataset bucket after pushing (default: ``True``).

        Returns
        -------
        ObjectWriteResult
        """
        if do_checks:
            if not file.exists():
                raise RuntimeError("Cannot push non-existing file {} to bucket {}".format(str(file), bucket_name))
            elif not file.is_file():
                raise RuntimeError("Cannot push non-regular file {} to bucket {}".format(str(file), bucket_name))
            elif bucket_root is not None and not file.is_relative_to(bucket_root):
                msg = "Cannot push {} to bucket {} when provided bad or non-relative bucket root {}"
                raise RuntimeError(msg.format(str(file), bucket_name, str(bucket_root)))

        if bucket_root is not None:
            file_rel_root = file.relative_to(bucket_root)
            dest = self._OBJECT_NAME_SEPARATOR.join(file_rel_root.parts)
        elif dest is None:
            dest = file.name

        result = self._client.fput_object(bucket_name=bucket_name, object_name=dest, file_path=str(file))
        if resync_serialized:
            self.persist_serialized(bucket_name)
        return result

    def _load_from_existing_bucket(self, bucket_name: str) -> bool:
        """
        Search existing bucket for standard serialized dataset object, and reload the dataset if it is there.

        Parameters
        ----------
        bucket_name : str
            The name of the existing bucket.

        Returns
        -------
        bool
            ``True`` if a previous serialized dataset was reloaded, or ``False`` if one could not be from this bucket.
        """
        for obj in self._client.list_objects(bucket_name):
            if obj.object_name == self._gen_dataset_serial_obj_name(bucket_name):
                self.reload(bucket_name)
                return True
        return False

    # TODO: might need to add the threading stuff in this function when ready to add it
    def _push_files(self, bucket_name: str, dir_path: Path, recursive: bool = True, bucket_root: Optional[Path] = None,
                    do_checks: bool = True, resync_serialized: bool = True):
        """
        Push the file contents of the given directory to the provided bucket.

        Parameters
        ----------
        bucket_name : str
            The name of the existing bucket to push to.
        dir_path : Path
            The path to an existing directory containing files to push to the bucket.
        recursive : bool
            Whether contents of nested directories, their inner directory contents, etc., should all be pushed, as
            opposed to only regular files that are immediate children of ``dir_path`` (``True`` by default)
        bucket_root : Optional[Path]
            The directory level that corresponds to the bucket's root level, for object naming purposes.
        do_checks : bool
            Whether to do sanity checks on the local file and bucket root (``True`` by default).
        resync_serialized : bool
            Whether to resync the serialized file object within the dataset bucket after pushing (default: ``True``).
        """
        if do_checks:
            if not dir_path.exists():
                msg = "Cannot push files from non-existing directory {} to bucket {}"
                raise RuntimeError(msg.format(str(dir_path), bucket_name))
            elif not dir_path.is_dir():
                msg = "Cannot push directory contents from non-directory {} to bucket {}"
                raise RuntimeError(msg.format(str(dir_path), bucket_name))
        if bucket_root is None:
            bucket_root = dir_path
        # First take care of immediate
        for file in [f for f in dir_path.iterdir() if f.is_file()]:
            self._push_file(bucket_name, file, bucket_root, do_checks=False, resync_serialized=False)
        if recursive:
            for directory in [d for d in dir_path.iterdir() if d.is_dir()]:
                self._push_files(bucket_name, directory, recursive, bucket_root, do_checks=False, resync_serialized=False)
        if resync_serialized:
            self.persist_serialized(bucket_name)

    def add_data(self, dataset_name: str, dest: str, data: Optional[bytes] = None, source: Optional[str] = None,
                 **kwargs) -> bool:
        """
        Add raw data or data from one or more files to the object store for the given dataset.

        Function adds either a binary data, data from a single file, or data from all files within a supplied directory,
        to the backing object store of the given dataset.  The dataset name must be recognized; if it is not, ``False``
        is immediately returned.

        The manager maintains a simulated directory structure within the dataset by encoding the parent directory path
        of files in the corresponding bucket object's name, along with the file's basename.  Only the relative path of
        the parent is included though, with this being relative to an ancestor directory that corresponds to the root
        level of the object store bucket.  The value of this corresponding root may be provided in the ``bucket_root``
        keyword arg.  If not provided, it is assumed to be the parent directory when adding a ``file``, or the directory
        itself when adding all files within a ``directory``.

        E.g. perhaps there exists the ``dataset_1/`` directory, with structure and contents:

            dataset_1/
            dataset_1/file_1
            dataset_1/file_2
            dataset_1/subdir_a/
            dataset_1/subdir_a/file_a_1
            dataset_1/subdir_a/file_a_2
            dataset_1/subdir_b/
            dataset_1/subdir_b/file_b_1

        If this function passed ``dataset_1`` as the ``directory``, and the ``bucket_root` was set or implied to be
        ``dataset_1``, then ``dataset_1/file_1`` would not have any directory structure encoded into its object name,
        while ``dataset_1/subdir_a/file_a_1`` would have ``subdir_a`` encoded, giving that object the name
        `subdir_a___file_a_1``.  The separator comes from the class variable ::attribute:`_OBJECT_NAME_SEPARATOR`.

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
        kwargs
            Implementation-specific params for representing the data and details of how it should be added.

        Keyword Args
        ----------
        bucket_root : Path
            The directory level that corresponds to the bucket's root level, for object naming purposes when ``source``
            represents a directory of data to add (defaults to the ``source`` directory itself if absent).

        Returns
        -------
        bool
            Whether the data was added successfully.
        See Also
        -------
        ::method:`_push_file`
        ::method:`_push_files`
        """
        if dataset_name not in self.datasets:
            return False
        elif data is not None:
            result = self._client.put_object(bucket_name=dataset_name, data=data, length=len(data), object_name=dest)
            return result.bucket_name == dataset_name
        elif source is None or len(source) == 0:
            from sys import _getframe
            msg = "{}.{} requires either binary data or a source for data to be provided."
            raise ValueError(msg.format(self.__class__.__name__, _getframe(0).f_code.co_name))

        src_path = Path(source)
        if not src_path.exists():
            from sys import _getframe
            msg = "{}.{} source path '{}' does not exist."
            raise ValueError(msg.format(self.__class__.__name__, _getframe(0).f_code.co_name, source))
        elif src_path.is_dir():
            bucket_root = kwargs.get('bucket_root', src_path)
            self._push_files(bucket_name=dataset_name, dir_path=kwargs['directory'], bucket_root=bucket_root)
            # TODO: probably need something better than just always returning True if this gets executed
            return True
        else:
            result = self._push_file(bucket_name=dataset_name, file=src_path, dest=dest)
            # TODO: test
            return isinstance(result.object_name, str)

    def create(self, name: str, category: DataCategory, domain: DataDomain, is_read_only: bool,
               initial_data: Optional[str] = None) -> ObjectStoreDataset:
        """
        Create a new ::class:`ObjectStoreDataset` instance and, if needed, backing object store bucket of the same name.

        Parameters
        ----------
        name : str
            The name for the new dataset.
        category : DataCategory
            The data category for the new dataset.
        domain : DataDomain
            The data domain for the new dataset, which includes the format, fields, and restrictions on values.
        is_read_only : bool
            Whether the new dataset is read-only.
        initial_data : Optional[str]
            Optional string form of a path to a directory containing initial data that should be added to the dataset.

        Returns
        -------
        ObjectStoreDataset
            A newly created dataset instance ready for use.
        """
        if name in self.datasets:
            raise RuntimeError("Cannot create new dataset with name {}: name already in use".format(name))
        if self._client.bucket_exists(name):
            raise RuntimeError("Unexpected existing bucket when creating dataset {}".format(name))

        files_dir = None
        if initial_data is not None:
            files_dir = Path(initial_data)
            if not files_dir.is_dir():
                raise RuntimeError("Invalid param for initial dataset data: {} not a directory".format(files_dir))
        elif is_read_only:
            msg = "Attempting to create read-only dataset {} without supplying it with any initial data"
            raise RuntimeError(msg.format(name))

        self._client.make_bucket(name)
        created_on = datetime.now()
        access_loc = "{}{}{}".format(self._obj_store_host_str, ObjectStoreDataset._ACCESS_LOCATION_DELIMITER, name)
        dataset = ObjectStoreDataset(name=name, category=category, data_domain=domain, manager=self,
                                     access_location=access_loc, is_read_only=is_read_only, created_on=created_on,
                                     last_updated=created_on)
        self.datasets[name] = dataset
        if files_dir is not None:
            self._push_files(bucket_name=name, dir_path=files_dir, recursive=True)
        self.persist_serialized(name)
        return dataset

    def list_buckets(self) -> List[str]:
        """
        List currently existing object store buckets.

        Returns
        -------
        List[str]
            A list of the names of currently existing object store buckets
        """
        return [bucket.name for bucket in self._client.list_buckets()]

    def list_files(self, dataset_name: str, **kwargs) -> List[str]:
        """
        List the files in the dataset of the provided name, with names decoded relative to dataset "root".

        Parameters
        ----------
        dataset_name : str
            The dataset name.

        Returns
        -------
        List[str]
            List of files in dataset of the provided name, relative to dataset root.

        See Also
        -------
        ::method:`_push_file`
        ::method:`_decode_object_name_to_file_path`
        """
        if dataset_name not in self.datasets:
            raise RuntimeError("Unrecognized dataset name {} given to request to list files".format(dataset_name))
        objects = self._client.list_objects(dataset_name, recursive=True)
        return [self._decode_object_name_to_file_path(object_name=str(obj)) for obj in objects]

    def get_bucket_creation_times(self) -> Dict[str, datetime]:
        """
        Get a dictionary of the creation times for existing buckets, keyed by bucket name.

        Returns
        -------
        Dict[str, datetime]
            A dictionary of the creation times for existing buckets, keyed by bucket name.
        """
        values = dict()
        for bucket in self._client.list_buckets():
            values[bucket.name] = bucket.creation_date
        return values

    def persist_serialized(self, name: str):
        """
        Write or re-write the serialized object file for this dataset within its bucket.

        Parameters
        ----------
        name : str
            The name of the dataset.
        """
        bin_json_str = self.datasets[name].to_json().encode()
        result = self._client.put_object(bucket_name=name, object_name=self._gen_dataset_serial_obj_name(name),
                                         data=io.BytesIO(bin_json_str), length=len(bin_json_str))

    def reload(self, name: str, is_read_only: bool = False, access_location: Optional[str] = None) -> ObjectStoreDataset:
        """
        Create a new dataset object by reloading from an existing storage location.

        Parameters
        ----------
        name : str
            The name of the dataset.
        is_read_only : bool
            Whether the loaded dataset object should be read-only (default: ``False``).
        access_location : Optional[str]
            Optional string for specifying access location when it cannot be inferred from ``name`` (default: ``None``).

        Returns
        -------
        ObjectStoreDataset
            A new dataset object, loaded from a previously stored dataset.
        """
        if name in self.datasets:
            raise RuntimeError("Cannot reload dataset with name {}: name already in use".format(name))
        elif not self._client.bucket_exists(name):
            raise RuntimeError("Expected bucket to exist when re-creating dataset {}".format(name))
        # TODO: (later) add something for checking host part of access location if provided, and if that is not this host, its a problem

        try:
            response_obj = self._client.get_object(bucket_name=name, object_name=self._gen_dataset_serial_obj_name(name))
            response_data = response_obj.data.decode()
        finally:
            response_obj.close()
            response_obj.release_conn()

        dataset = ObjectStoreDataset.factory_init_from_deserialized_json(response_data)
        self.datasets[name] = dataset
        return dataset

    @property
    def supported_dataset_types(self) -> Set[Type[Dataset]]:
        """
        The set of ::class:`Dataset` subclass types that this instance supports.

        Typically (but not necessarily always) this will be backed by a static or hard-coded value for the manager
        subtype.

        Returns
        -------
        Set[Type[Dataset]]
            The Set of ::class:`Dataset` subclass types that this instance supports.
        """
        return self._SUPPORTED_TYPES
