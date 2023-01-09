from abc import ABC, abstractmethod
from .meta_data import ContinuousRestriction, DataCategory, DataDomain, DataFormat, DiscreteRestriction, \
    StandardDatasetIndex, TimeRange
from .exception import DmodRuntimeError
from datetime import datetime, timedelta

from .serializable import Serializable, ResultIndicator
from .enum import PydanticEnum
from typing import Any, Callable, ClassVar, Dict, FrozenSet, List, Optional, Set, Tuple, Type, Union
from pydantic import Field, validator, root_validator
from uuid import UUID, uuid4


class DatasetType(PydanticEnum):
    UNKNOWN = (-1, False, lambda dataset: None)
    OBJECT_STORE = (0, True, lambda dataset: dataset.name)
    FILESYSTEM = (1, True, lambda dataset: dataset.access_location)

    @classmethod
    def get_for_name(cls, name_str: str) -> 'DatasetType':
        cleaned_up_str = name_str.strip().upper()
        for value in cls:
            if value.name.upper() == cleaned_up_str:
                return value
        return DatasetType.UNKNOWN

    def __init__(self, unique_id: int, is_file_based: bool, docker_mount_func: Callable[['Dataset'], str]):
        self._unique_id = unique_id
        self._is_file_based = is_file_based
        self._docker_mount_func = docker_mount_func

    @property
    def docker_mount_func(self) -> Callable[['Dataset'], str]:
        """
        A callable that accepts a ::class:`Dataset` and can be used to get the appropriate Docker mount str for it.

        Returns
        -------
        Callable[['Dataset'], str]
            Callable that accepts a ::class:`Dataset` and can be used to get the appropriate Docker mount str for it.
        """
        return self._docker_mount_func

    @property
    def is_file_based(self) -> bool:
        """
        Whether this type of dataset is based on a filesystem or filesystem-like structure.

        Returns
        -------
        bool
            Whether this type of dataset is based on a filesystem or filesystem-like structure.
        """
        return self._is_file_based


class Dataset(Serializable):
    """
    Rrepresentation of the descriptive metadata for a grouped collection of data.
    """

    _SERIAL_DATETIME_STR_FORMAT: ClassVar = '%Y-%m-%d %H:%M:%S'
    name: str = Field(description="The name for this dataset, which also should be a unique identifier.")
    # QUESTION: should this be optional? see factory_init_from_deserialized_json
    category: Optional[DataCategory] = Field(None, alias="data_category", description="The ::class:`DataCategory` type value for this instance.")
    # QUESTION: should this be optional? see factory_init_from_deserialized_json
    data_domain: Optional[DataDomain]
    dataset_type: DatasetType = Field(DatasetType.UNKNOWN, alias="type")
    access_location: str = Field(description="String representation of the location at which this dataset is accessible.")
    uuid: Optional[UUID] = Field(default_factory=uuid4)
    # manager can only be passed as constructed DatasetManager subtype. Manager not included in `dict` or `json` deserialization.
    # TODO: don't include `manager` in `Dataset.schema()`. Inclusion is not reflective of the de/serialization behavior.
    manager: Optional['DatasetManager'] = Field(exclude=True)
    manager_uuid: Optional[UUID]
    is_read_only: bool = Field(True, description="Whether this is a dataset that can only be read from.")
    description: Optional[str]
    expires: Optional[datetime] = Field(description='The time after which a dataset may "expire" and be removed, or ``None`` if the dataset is not temporary.')
    derived_from: Optional[str] = Field(description="The name of the dataset from which this dataset was derived, if it is known to have been derived.")
    derivations: Optional[List[str]] = Field(default_factory=list, description="""List of names of datasets which were derived from this dataset.\n
    Note that it is not guaranteed that any such dataset still exist and/or are still available.""")
    created_on: Optional[datetime] = Field(description="When this dataset was created, or ``None`` if that is not known.")
    last_updated: Optional[datetime]

    @validator("created_on", "last_updated", "expires", pre=True)
    def parse_dates(cls, v):
        if v is None:
            return None

        if isinstance(v, datetime):
            return v

        return datetime.strptime(v, cls.get_datetime_str_format())

    @validator("created_on", "last_updated", "expires")
    def drop_microseconds(cls, v: datetime):
        return v.replace(microsecond=0)

    @validator("manager", pre=True)
    def drop_manager_if_not_constructed_subtype(cls, value):
        # manager can only be passed as constructed DatasetManager subtype
        if isinstance(value, DatasetManager):
            return value
        return None

    @root_validator()
    def set_manager_uuid(cls, values) -> dict:
        manager: Optional[DatasetManager] = values["manager"]
        # give preference to `manager.uuid` otherwise use specified `manager_uuid`
        if manager is not None:
            # pydantic will not validate this, so we need to check it
            if not isinstance(manager.uuid, UUID):
                raise ValueError(f"Expected UUID got {type(manager.uuid)}")
            values["manager_uuid"] = manager.uuid

        return values

    class Config:
        # NOTE: re-validate when any field is re-assigned (i.e. `model.foo = 12`)
        # TODO: in future deprecate setting properties unless through a setter method
        validate_assignment = True
        arbitrary_types_allowed = True

    # TODO: Remove after draft review
    # @classmethod
    # def factory_init_from_deserialized_json(cls, json_obj: dict):
    #     try:
    #         manager_uuid = UUID(json_obj[cls._KEY_MANAGER_UUID]) if cls._KEY_MANAGER_UUID in json_obj else None
    #         return cls(name=json_obj[cls._KEY_NAME],
    #                    category=DataCategory.get_for_name(json_obj[cls._KEY_DATA_CATEGORY]),
    #                    data_domain=DataDomain.factory_init_from_deserialized_json(json_obj[cls._KEY_DATA_DOMAIN]),
    #                    dataset_type=DatasetType.get_for_name(json_obj[cls._KEY_TYPE]),
    #                    access_location=json_obj[cls._KEY_ACCESS_LOCATION],
    #                    description=json_obj.get(cls._KEY_DESCRIPTION, None),
    #                    uuid=UUID(json_obj[cls._KEY_UUID]),
    #                    manager_uuid=manager_uuid,
    #                    is_read_only=json_obj[cls._KEY_IS_READ_ONLY],
    #                    expires=cls._date_parse_helper(json_obj, cls._KEY_EXPIRES),
    #                    derived_from=json_obj[cls._KEY_DERIVED_FROM] if cls._KEY_DERIVED_FROM in json_obj else None,
    #                    derivations=json_obj[cls._KEY_DERIVATIONS] if cls._KEY_DERIVATIONS in json_obj else [],
    #                    created_on=cls._date_parse_helper(json_obj, cls._KEY_CREATED_ON),
    #                    last_updated=cls._date_parse_helper(json_obj, cls._KEY_LAST_UPDATE))
    #     except Exception as e:
    #         return None

    def __hash__(self):
        return hash(','.join([self.__class__.__name__, self.name, self.category.name, str(hash(self.data_domain)),
                              self.access_location, str(self.is_read_only), str(hash(self.created_on))]))

    def _set_expires(self, new_expires: datetime):
        """
        "Private" function to set the ::attribute:`expires` property.

        Function sets the property to the given value, without any checks to validity.  It does, however, also update
        the ::attribute:`last_updated` property to ``datetime.now()``.

        Parameters
        ----------
        new_expires : datetime
            The new value for ::attribute:`expires`.
        """
        self.expires = new_expires
        self.last_updated = datetime.now()

    @property
    def data_format(self) -> DataFormat:
        """
        The data format for this instance.

        Returns
        -------
        DataFormat
            The ::class:`DataFormat` type value for this instance.
        """
        return self.data_domain.data_format

    @property
    def docker_mount(self) -> str:
        """
        The volume or bind mount location for this dataset, such that it can be mounted in a Docker container.

        This is obtained using the callable ::attr:`DatasetType.docker_mount_func` from the instance's
        ::attr:`dataset_type` property.

        Returns
        -------
        str
            The volume or bind mount location for this dataset, such that it can be mounted in a Docker container.

        Raises
        -------
        DmodRuntimeError
            Raised if the callable for determining this from the instance's ::class:`DatasetType` returns ``None``.
        """
        result = self.dataset_type.docker_mount_func(self)
        if result is None:
            msg = "Can't get Docker mount location for dataset {} of type {}"
            raise DmodRuntimeError(msg.format(self.name, self.dataset_type.name))
        else:
            return result

    def extend_life(self, value: Union[datetime, timedelta]) -> bool:
        """
        Extend the expiration of this dataset.

        This function allows the ::attribute:`expires` property to be extended further into the future.  If it updates
        the property, it will return ``True``.  However, there are several scenarios when it will not update the
        property, and instead just return ``False`` without side effects.

        If this instance is not temporary, according to the ::attribute:`is_temporary` property, then its state is not
        modified, regardless of the argument value, and this function returns ``False``.

        If a ::class:`timedelta` argument is supplied to a temporary instance, then ::attribute:`expires` will be set to
        its initial value plus this delta, and then ``True`` will be returned.

        For a ::class:`datetime` argument supplied to a temporary instance, IFF the argument value occurs after the
        initial ::attribute:`expires` value, then ::attribute:`expires` is updated and ``True`` is returned.

        Parameters
        ----------
        value : Union[datetime, timedelta]
            Either the time in the future to extend to, or the delta into the future from the current expiration.

        Returns
        -------
        bool
            Whether this dataset's expiration was extended.
        """
        if not self.is_temporary:
            return False
        elif isinstance(value, timedelta):
            # TODO: Fix bug. expires could be None
            self._set_expires(self.expires + value)
            return True
            # TODO: Fix bug. expires could be None
        elif isinstance(value, datetime) and self.expires < value:
            self._set_expires(value)
            return True
        else:
            return False

    @property
    def fields(self) -> Dict[str, Type]:
        """
        The specific data fields that are part of this dataset.

        Returns
        -------
        Dict[str, Type]
            The data fields that are available from this dataset.
        """
        return self.data_domain.data_fields

    @property
    def is_temporary(self) -> bool:
        """
        Whether this dataset is (at present) intended to be temporary.

        A dataset may be temporary, meaning its availability and validity cannot be assumed perpetually; e.g., the data
        may be removed from storage.  This property offers a convenience access to whether that is the case.

        Returns
        -------
        bool
            Whether this dataset is (at present) intended to be temporary.
        """
        return self.expires is not None

    @property
    def time_range(self) -> Optional[TimeRange]:
        """
        The time range over which the dataset has data, if it is a time series, or ``None``.

        Returns
        -------
        Optional[TimeRange]
            The time range over which the dataset has data, if it is a time series, or ``None``.
        """
        if not self.data_format.is_time_series:
            return None
        # As TimeRange extends ContinuousRestriction, it should only be in the continuous_restrictions property list
        tr = self.data_domain.continuous_restrictions[StandardDatasetIndex.TIME]
        return tr if isinstance(tr, TimeRange) else TimeRange(begin=tr.begin, end=tr.end, variable=tr.variable)

    def _get_exclude_fields(self) -> Set[str]:
        """Set of fields to exclude during deserialization if they are some None variant (e.g. '', 0, None)"""
        candidates = ("manager_uuid", "expires", "derived_from", "derivations", "description", "created_on", "last_updated")
        return {f for f in candidates if not self.__getattribute__(f)}

    def dict(self, **kwargs) -> dict:
        # if exclude is set, ignore this _get_exclude_fields()
        exclude = self._get_exclude_fields() if kwargs.get("exclude", False) is False else kwargs["exclude"]
        kwargs["exclude"] = exclude

        serial = super().dict(**kwargs)

        # serialize uuid
        serial["uuid"] = str(self.uuid)
        return serial


class DatasetUser(ABC):
    """
    Abstract type that is a user of a dataset, and for which a temporary dataset should continue to survive.

    Some datasets may be created temporarily.  A common example is derived datasets.  While an expiration time can be
    set for a dataset, it may not be straightforward to determine what the right value for expiration time is or if a
    previous value is still appropriate.

    This provides a more direct designation of something using one or more datasets.
    """

    @property
    @abstractmethod
    def uuid(self) -> UUID:
        """
        UUID for this instance.

        Returns
        -------
        UUID
            UUID for this instance.
        """
        pass

    @property
    @abstractmethod
    def datasets_in_use(self) -> Dict[UUID, str]:
        """
        A collection of datasets in used, keyed by UUID, with values being the dataset names.

        Returns
        -------
        Dict[UUID, str]
            A collection of datasets in used, keyed by UUID, with values being the dataset names.
        """
        pass

    def link_to_dataset(self, dataset: Dataset) -> bool:
        """
        Establish a usage link with this dataset.

        Most conditions that would cause failure result in exceptions, which are not caught here.  However, in the event
        the given dataset does not have a reference to a manager set (in which case, there is little point to keeping
        track of usage), then this method will return ``False``.

        Additionally, if the dataset's manager cannot establish a link on its side, this method will return ``False.``

        Parameters
        ----------
        dataset : Dataset
            The used dataset.

        Returns
        -------
        bool
            Whether establishing the link was successful.
        """
        if dataset.manager is not None and dataset.manager.link_user(user=self, dataset=dataset):
            self.datasets_in_use[dataset.uuid] = dataset.name
            self.linked_dataset_managers[dataset.uuid] = dataset.manager
            return True
        else:
            return False

    @property
    @abstractmethod
    def linked_dataset_managers(self) -> Dict[UUID, 'DatasetManager']:
        """
        A collection of associated managers of in-use datasets, key by UUID of the in-use dataset.

        Returns
        -------
        Dict[UUID, 'DatasetManager']
            A collection of associated managers of in-use datasets, key by UUID of the in-use dataset.
        """
        pass

    def unlink_to_dataset(self, dataset: Dataset) -> bool:
        """
        Release an existing usage link with this dataset.

        Parameters
        ----------
        dataset : Dataset
            The used dataset.

        Returns
        -------
        bool
            Whether an established usage link was successful released.
        """
        if dataset.uuid not in self.datasets_in_use or dataset.uuid not in self.linked_dataset_managers:
            return False
        elif self.linked_dataset_managers[dataset.uuid].unlink_user(user=self, dataset=dataset):
            self.datasets_in_use.pop(dataset.uuid)
            self.linked_dataset_managers.pop(dataset.uuid)
            return True
        else:
            return False


class DatasetManager(ABC):
    """
    Abstract representation of manager of ::class:`Dataset` instances.

    Type maintains the required condition of unique ::class:`Dataset` names by holding known datasets in a dictionary
    keyed by dataset name.

    Types must implement two functions for deriving new datasets from existing ones.  ::method:`filter` creates a new
    dataset from an existing one, but in exactly the same format, and with only a subset of the overall data records.
    ::method:`transform` creates a new dataset from an existing one, but transforms the data to another format.
    """

    _SERIALIZED_OBJ_NAME_TEMPLATE = "{}_serialized.json"
    """ The name of the file/object for serialized versions of datasets, within a dataset's bucket. """

    @classmethod
    def get_serial_dataset_filename(cls, dataset_name: str) -> str:
        """
        Get the standard file basename for persisting the serialized state of a ::class:`Dataset` of the given name.

        Parameters
        ----------
        dataset_name: str
            The name of the dataset in question.

        Returns
        -------
        str
           The file basename for persisting the serialized state of a dataset with the given name.
        """
        return cls._SERIALIZED_OBJ_NAME_TEMPLATE.format(dataset_name)

    def __init__(self, uuid: Optional[UUID] = None, datasets: Optional[Dict[str, Dataset]] = None, *args, **kwargs):
        self._uuid = uuid4() if uuid is None else uuid
        self._datasets = datasets if datasets is not None else dict()
        self._dataset_users: Dict[str, Set[UUID]] = dict()
        """ Collection of dataset names each keyed to a set of UUIDs of each user using the corresponding dataset. """
        self._errors = []
        """ A property attribute to hold errors encountered during operations. """

    # TODO: implement functions and routines for scrubbing temporary datasets as needed

    @abstractmethod
    def add_data(self, dataset_name: str, dest: str, data: Optional[bytes] = None, source: Optional[str] = None,
                 is_temp: bool = False, **kwargs) -> bool:
        """
        Add data in some format to the dataset.

        Implementations must support receiving data to insert in the form of byte strings.  Implementations may also
        support alternative scenarios via their specific keyword args (e.g., adding data from a file).

        Parameters
        ----------
        dataset_name : str
            The dataset to which to add data.
        dest : str
            A path-like string specifying a location within the dataset (e.g., file, object, sub-URL) where the data
            should be added.
        data : Optional[bytes]
            Optional encoded byte string containing data to be inserted into the data set; either this or ``source``
            must be provided.
        source : Optional[str]
            Optional string specifying a location from which to source the data to be added; either this or ``data``
            must be provided.
        is_temp : bool
            Indication of whether this item should be treated as temporary, as applicable to the implementation.
        kwargs
            Implementation-specific params for other ways to represent data and details of how it should be added.

        Returns
        -------
        bool
            Whether the data was added successfully.
        """
        pass

    @abstractmethod
    def combine_partials_into_composite(self, dataset_name: str, item_name: str, combined_list: List[str]) -> bool:
        pass

    @abstractmethod
    def create(self, name: str, category: DataCategory, domain: DataDomain, is_read_only: bool,
               initial_data: Optional[str] = None) -> Dataset:
        """
        Create a new dataset instance.

        Implementations should ensure that a returned dataset is ready for use.  That is, existing data at the time of
        creation is accessible according to the dataset's metadata, and (when appropriate) the dataset is ready for
        receiving output written to it.

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
            Optional string representation of a location in which there is initial data that should be added to the
            dataset.

        Returns
        -------
        Dataset
            A newly created dataset instance ready for use.
        """
        pass

    @abstractmethod
    def delete(self, dataset: Dataset, **kwargs) -> bool:
        """
        Delete the supplied dataset, as long as it is managed by this manager.

        Parameters
        ----------
        dataset
        kwargs

        Returns
        -------
        bool
            Whether the delete was successful.
        """
        pass

    # TODO: add back as abstract, then implement properly in subtypes
    #@abstractmethod
    def delete_data(self, dataset_name: str, **kwargs) -> bool:
        """
        Delete data in some format from the dataset.

        Parameters
        ----------
        dataset_name : str
            The dataset from which to delete data.
        kwargs
            Implementation-specific params for referencing what data should be deleted and how.

        Returns
        -------
        bool
            Whether the data was deleted successfully.
        """
        #pass
        return False

    @property
    @abstractmethod
    def data_chunking_params(self) -> Optional[Tuple[str, str]]:
        """
        The "offset" and "length" keywords than can be used with ::method:`get_data` to chunk results, when supported.
        Returns
        -------
        Optional[Tuple[str, str]]
            The "offset" and "length" keywords to chunk results, or ``None`` if chunking not supported.
        """
        pass

    @property
    def datasets(self) -> Dict[str, Dataset]:
        """
        The datasets known to and managed by this instance, mapped by the unique ::attribute:`Dataset.name` of each.

        Returns
        -------
        Dict[str, Dataset]
            The datasets known to and managed by this instance.
        """
        return self._datasets

    @property
    def errors(self) -> List[Union[str, Exception, ResultIndicator]]:
        """
        List of previously encountered errors, which may be strings, exceptions, or ::class:`ResultIndicator` objects.

        Note that earlier error will have lower indices.

        Returns
        -------
        List[Union[str, Exception, ResultIndicator]]
            List of representational objects for previously encountered errors.
        """
        return self._errors

    # TODO: add back as abstract, then implement in subtypes
    #@abstractmethod
    def filter(self, base_dataset: Dataset, restrictions: List[Union[ContinuousRestriction, DiscreteRestriction]],
               new_dataset_name: str, is_temporary: bool, **kwargs) -> Dataset:
        """
        Produce a new dataset by filtering the data records in an existing one by values in certain fields.

        Parameters
        ----------
        base_dataset : Dataset
            The original base dataset
        restrictions : List[Union[ContinuousRestriction, DiscreteRestriction]]
            A list of restrictions defining filtering variables and accepted values.
        new_dataset_name : str
            The name for the new resulting dataset which will contain the filtered data.
        is_temporary : bool
            Whether the new resulting dataset should be created as temporary.
        kwargs
            Implementation-specific params

        Returns
        -------
        Dataset
            A new dataset containing a subset of records from the original ``dataset``, but in the same data format.
        """
        pass

    @abstractmethod
    def get_data(self, dataset_name: str, item_name: str, **kwargs) -> Union[bytes, Any]:
        """
        Get data from this dataset.

        All implementation must support returning data as a ::class:`bytes` object by default.  Implementations may
        support other return types, with their keyword args being used in some manner to cause that.

        Parameters
        ----------
        dataset_name : str
            The dataset from which to get data.
        item_name : str
            The name of the object from which to get data.
        kwargs
            Implementation-specific params for representing what data to get and how to get and deliver it.

        Returns
        -------
        Union[bytes, Any]
            A ::class:`bytes` object containing the data, or a return value of implementation-specific type.
        """
        pass

    def get_dataset_users(self, dataset_name: str) -> FrozenSet[UUID]:
        """
        Get an immutable set of UUIDs for the linked users of a dataset.

        Parameters
        ----------
        dataset_name : str
            The name of the dataset of interest.

        Returns
        -------
        FrozenSet[UUID]
            Immutable set of UUIDs for the linked users of a dataset.
        """
        return frozenset(self._dataset_users[dataset_name]) if dataset_name in self._dataset_users else frozenset()

    def link_user(self, user: DatasetUser, dataset: Dataset) -> bool:
        """
        Link a dataset user with this dataset.

        Parameters
        ----------
        user : DatasetUser
            A dataset user.
        dataset: Dataset
            The dataset that the user is to be recorded as using.

        Returns
        ----------
        bool
            Whether the link was successful.
        """
        if dataset.name not in self.datasets:
            raise RuntimeError("Cannot link user {} to unknown dataset {}".format(user.uuid, dataset.name))
        if dataset.name not in self._dataset_users:
            self._dataset_users[dataset.name] = set()
        self._dataset_users[dataset.name].add(user.uuid)
        return True

    @abstractmethod
    def list_files(self, dataset_name: str, **kwargs) -> List[str]:
        """
        List the files in the dataset of the provided name, relative to dataset root.

        Note that not all datasets will be file-based.  Implementations should clearly document how they behave in such
        scenarios.

        Parameters
        ----------
        dataset_name : str
            The name of the relevant dataset.
        kwargs
            Other implementation specific keyword args.

        Returns
        -------
        List[str]
            A list of files in the dataset of the provided name, relative to dataset root.

        Raises
        -------
        DmodRuntimeError
            Implementations should raise this error if the dataset in question is of a ::class:`DatasetType` that is not
            file-based.
        """
        pass

    @abstractmethod
    def reload(self, reload_from: str, serialized_item: Optional[str] = None) -> Dataset:
        """
        Reload a ::class:`Dataset` object from a serialized copy at a specified location.

        Parameters
        ----------
        reload_from : str
            The location (in string form) where a serialized copy of the desired dataset can be found.
        serialized_item : Optional[str]
            Optional string for specifying the item to reload from when it cannot be inferred from ``reload_from``
            (default: ``None``).

        Returns
        -------
        Dataset
            A new dataset object, loaded from a previously serialized dataset.
        """
        pass

    @property
    @abstractmethod
    def supported_dataset_types(self) -> Set[DatasetType]:
        """
        The set of ::class:`DatasetType` values that this instance supports.

        Typically (but not necessarily always) this will be backed by a static or hard-coded value for the manager
        subtype.

        Returns
        -------
        Set[DatasetType]
            The set of ::class:`DatasetType` values that this instance supports.
        """
        pass

    # TODO: add back as abstract, then implement in subtypes
    #@abstractmethod
    def transform(self, base_dataset: Dataset, new_format: DataFormat, prevent_loss: bool = True, **kwargs) -> Dataset:
        """
        Transform the given dataset into a new dataset with the same records but in a different ::class:`DataFormat`.

        Parameters
        ----------
        base_dataset : Dataset
            The original base dataset.
        new_format : DataFormat
            The format for the new dataset.
        prevent_loss : bool
            Whether transformation is prevented if the new format does not have all the data fields of the old.
        kwargs
            Other implementation-specific params.

        Returns
        -------
        Dataset
            A new dataset with records transformed from the base dataset.

        Raises
        -------
        RuntimeError
            Raised if ``prevent_loss`` is ``True`` and the new format does not have the same fields as the original.
        """
        pass

    def unlink_user(self, user: DatasetUser, dataset: Dataset) -> bool:
        """
        Unlink a dataset user with this dataset.

        Parameters
        ----------
        user : DatasetUser
            A dataset user.
        dataset: Dataset
            The dataset that the user was, but is no longer, using.

         Returns
        ----------
        bool
            Whether the usage link was successfully unlinked.
        """
        if dataset.name not in self._dataset_users or user.uuid not in self._dataset_users[dataset.name]:
            return False
        elif len(self._dataset_users[dataset.name]) == 1:
            self._dataset_users.pop(dataset.name)
        else:
            self._dataset_users[dataset.name].remove(user.uuid)
        return True

    @property
    def uuid(self) -> UUID:
        """
        UUID for this instance.

        Returns
        -------
        UUID
            UUID for this instance.
        """
        return self._uuid
