from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, TimeRange
from .dataset import Dataset, DatasetManager
from datetime import datetime
from minio import Minio
from minio.api import ObjectWriteResult
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID


class ObjectStoreDataset(Dataset):

    _OBJECT_NAME_SEPARATOR = "___"
    """ Separator for individual parts (e.g., corresponding to directories) of an object name. """

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

    _OBJECT_NAME_SEPARATOR = "___"
    """ Separator for individual parts (e.g., corresponding to directories) of an object name. """

    def __init__(self, obj_store_host_str: str, access_key: Optional[str] = None, secret_key: Optional[str] = None,
                 datasets: Optional[Dict[str, Dataset]] = None):
        super(ObjectStoreDatasetManager, self).__init__(datasets)
        # TODO: add checks to ensure all datasets passed to this type are ObjectStoreDataset
        self._obj_store_host_str = obj_store_host_str
        # TODO (later): may need to look at turning this back on
        self._client = Minio(obj_store_host_str, access_key=access_key, secret_key=secret_key, secure=False)


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

    # TODO: add stuff for threading
    def _push_file(self, bucket_name: str, file: Path, bucket_root: Path, do_checks: bool = True) -> ObjectWriteResult:
        """
        Push a file to a bucket.

        Buckets simulate subdirectories by encoding relative directory structure into object names.  This relative
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
            The directory level that corresponds to the bucket's root level, for object naming purposes.
        do_checks : bool
            Whether to do sanity checks on the local file and bucket root (``True`` by default).

        Returns
        -------
        ObjectWriteResult
        """
        if do_checks:
            if not file.exists():
                raise RuntimeError("Cannot push non-existing file {} to bucket {}".format(str(file), bucket_name))
            elif not file.is_file():
                raise RuntimeError("Cannot push non-regular file {} to bucket {}".format(str(file), bucket_name))
            elif not file.is_relative_to(bucket_root):
                msg = "Cannot push {} to bucket {} when provided bad or non-relative bucket root {}"
                raise RuntimeError(msg.format(str(file), bucket_name, str(bucket_root)))
        file_rel_root = file.relative_to(bucket_root)
        object_name = self._OBJECT_NAME_SEPARATOR.join(file_rel_root.parts)
        return self._client.fput_object(bucket_name=bucket_name, object_name=object_name, file_path=str(file))

    # TODO: might need to add the threading stuff in this function when ready to add it
    def _push_files(self, bucket_name: str, dir_path: Path, recursive: bool = True, bucket_root: Optional[Path] = None,
                    do_checks: bool = True):
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
            self._push_file(bucket_name, file, bucket_root, do_checks=False)
        if recursive:
            for directory in [d for d in dir_path.iterdir() if d.is_dir()]:
                self._push_files(bucket_name, directory, recursive, bucket_root, do_checks=False)

    def add_data(self, dataset_name: str, **kwargs) -> bool:
        """
        Add one or more files to the object store for the given dataset.

        Function adds either a single file or all files within a supplied directory to the backing object store of the
        given dataset, as long as the dataset name is recognized (if not, ``False`` is immediately returned).  This is
        done using either the ``file`` or ``directory`` kwargs value respectively.  Note that a ::class:`ValueError`
        will be raised if both are present.

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
        kwargs
            Implementation-specific params for representing the data and details of how it should be added.

        Keyword Args
        ----------
        file : Path
            When present, path to a file to be added (either ``file`` or ``directory`` must be present).
        directory : Path
            When present, path to a directory of files to be added.
        bucket_root : Path
            The directory level that corresponds to the bucket's root level, for object naming purposes (defaults to the
            parent of ``file`` if used, or to ``directory`` itself if used).

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
        elif 'file' in kwargs and 'directory' in kwargs:
            from sys import _getframe
            msg = "{}.{} does not support both 'file' and 'directory' kwargs in a single call"
            raise ValueError(msg.format(self.__class__.__name__, _getframe(0).f_code.co_name))
        elif 'file' in kwargs:
            bucket_root = kwargs['bucket_root'] if 'bucket_root' in kwargs else kwargs['file'].parent
            result = self._push_file(bucket_name=dataset_name, file=kwargs['file'], bucket_root=bucket_root)
            # TODO: test
            return isinstance(result.object_name, str)
        elif 'directory' in kwargs:
            bucket_root = kwargs['bucket_root'] if 'bucket_root' in kwargs else kwargs['directory']
            self._push_files(bucket_name=dataset_name, dir_path=kwargs['directory'], bucket_root=bucket_root)
            # TODO: probably need something better than just always returning True if this gets executed
            return True
        else:
            return False

    def create(self, name: str, category: DataCategory, data_format: DataFormat, is_read_only: bool,
               files_dir: Optional[Path] = None, time_range: Optional[TimeRange] = None,
               expect_bucket_exists: bool = False, recurse_dir: bool = True, **kwargs) -> ObjectStoreDataset:
        """
        Create a new ::class:`ObjectStoreDataset` instance.

        Parameters
        ----------
        name : str
            The name for the new dataset.
        category : DataCategory
            The data category for the new dataset.
        data_format : DataFormat
            The data format for the new dataset.
        is_read_only : bool
            Whether the new dataset is read-only.
        files_dir : Optional[Path]
            Optional path to a directory containing initial data for the dataset (essential for read-only datasets).
        time_range : Optional[TimeRange]
            Optional time range over which the created dataset has data.
        expect_bucket_exists : bool
            Whether it is expected that the associated object store bucket is already created (default: ``False``).
        recurse_dir : bool
            Whether subdirectories under ``files_dir`` and their contents should also be added as initial data.
        kwargs
            Implementation specific args.

        Returns
        -------
        Dataset
            A newly created dataset instance ready for use.
        """
        if name in self.datasets:
            raise RuntimeError("Cannot create new dataset with name {}: name already in use".format(name))
        does_bucket_exist = self._client.bucket_exists(name)
        if not expect_bucket_exists and does_bucket_exist:
            raise RuntimeError("Unexpected existing bucket when creating dataset {}".format(name))
        elif expect_bucket_exists and not does_bucket_exist:
            raise RuntimeError("Expected bucket to exist when creating dataset {}".format(name))
        elif not expect_bucket_exists:
            self._client.make_bucket(name)

        if files_dir is not None:
            if not files_dir.is_dir():
                raise RuntimeError("Invalid non-directory path {} passed for dataset files directory".format(files_dir))
            else:
                self._push_files(bucket_name=name, dir_path=files_dir, recursive=recurse_dir)

        if is_read_only and len(list(self._client.list_objects(name, recursive=True))) == 0:
            msg = "Attempting to create read-only dataset {} without supplying it with any initial data"
            raise RuntimeError(msg.format(name))

        created_on = datetime.now()
        return ObjectStoreDataset(name=name, category=category, data_format=data_format, manager=self,
                                  access_location=self._obj_store_host_str, is_read_only=is_read_only,
                                  created_on=created_on, last_updated=created_on)

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
