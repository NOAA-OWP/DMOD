from abc import ABC, abstractmethod
from dmod.core.meta_data import ContinuousRestriction, DataCategory, DataDomain, DataFormat, DiscreteRestriction, \
    StandardDatasetIndex, TimeRange
from datetime import datetime, timedelta

from dmod.core.serializable import Serializable, ResultIndicator
from numbers import Number
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple, Type, Union
from uuid import UUID, uuid4


class Dataset(Serializable, ABC):
    """
    Abstraction representation of a grouped collection of data and its metadata.
    """

    _SERIAL_DATETIME_STR_FORMAT = '%Y-%m-%d %H:%M:%S'

    _KEY_ACCESS_LOCATION = 'access_location'
    _KEY_CREATED_ON = 'create_on'
    _KEY_DATA_CATEGORY = 'data_category'
    _KEY_DATA_DOMAIN = 'data_domain'
    _KEY_DERIVED_FROM = 'derived_from'
    _KEY_DERIVATIONS = 'derivations'
    _KEY_EXPIRES = 'expires'
    _KEY_IS_READ_ONLY = 'is_read_only'
    _KEY_LAST_UPDATE = 'last_updated'
    _KEY_MANAGER_UUID = 'manager_uuid'
    _KEY_NAME = 'name'
    _KEY_UUID = 'uuid'

    @classmethod
    @abstractmethod
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
        pass

    # TODO: move this (and something more to better automatically handle Serializable subtypes) to Serializable directly
    @classmethod
    def _date_parse_helper(cls, json_obj: dict, key: str) -> Optional[datetime]:
        if key in json_obj:
            return datetime.strptime(json_obj[key], cls.get_datetime_str_format())
        else:
            return None

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        try:
            if cls._KEY_MANAGER_UUID in json_obj:
                manager_uuid = UUID(json_obj[cls._KEY_MANAGER_UUID])
            else:
                manager_uuid = None

            return cls(name=json_obj[cls._KEY_NAME],
                       category=DataCategory.get_for_name(json_obj[cls._KEY_DATA_CATEGORY]),
                       data_domain=DataDomain.factory_init_from_deserialized_json(json_obj[cls._KEY_DATA_DOMAIN]),
                       access_location=json_obj[cls._KEY_ACCESS_LOCATION],
                       uuid=UUID(json_obj[cls._KEY_UUID]),
                       manager_uuid=manager_uuid,
                       is_read_only=json_obj[cls._KEY_IS_READ_ONLY],
                       expires=cls._date_parse_helper(json_obj, cls._KEY_EXPIRES),
                       derived_from=json_obj[cls._KEY_DERIVED_FROM] if cls._KEY_DERIVED_FROM in json_obj else None,
                       derivations=json_obj[cls._KEY_DERIVATIONS] if cls._KEY_DERIVATIONS in json_obj else [],
                       created_on=cls._date_parse_helper(json_obj, cls._KEY_CREATED_ON),
                       last_updated=cls._date_parse_helper(json_obj, cls._KEY_LAST_UPDATE),
                       **cls.additional_init_param_deserialized(json_obj))
        except Exception as e:
            return None

    def __eq__(self, other):
        return isinstance(other, Dataset) and self.name == other.name and self.category == other.category \
               and self.data_domain == other.data_domain and self.access_location == other.access_location \
               and self.is_read_only == other.is_read_only and self.created_on == other.created_on

    def __hash__(self):
        return hash(','.join([self.__class__.__name__, self.name, self.category.name, str(hash(self.data_domain)),
                              self.access_location, str(self.is_read_only), str(hash(self.created_on))]))

    def __init__(self, name: str, category: DataCategory, data_domain: DataDomain, access_location: str,
                 uuid: Optional[UUID] = None, manager: Optional['DatasetManager'] = None,
                 manager_uuid: Optional[UUID] = None, is_read_only: bool = True, expires: Optional[datetime] = None,
                 derived_from: Optional[str] = None, derivations: Optional[List[str]] = None,
                 created_on: Optional[datetime] = None, last_updated: Optional[datetime] = None):
        self._name = name
        self._category = category
        self._data_domain = data_domain
        self._access_location = access_location
        self._uuid = uuid4() if uuid is None else uuid
        self._manager = manager
        self._manager_uuid = manager.uuid if manager is not None else manager_uuid
        self._is_read_only = is_read_only
        self._expires = expires if expires is None else expires.replace(microsecond=0)
        self._derived_from = derived_from
        self._derivations = derivations if derivations is not None else list()
        self._created_on = created_on if created_on is None else created_on.replace(microsecond=0)
        self._last_updated = last_updated if last_updated is None else last_updated.replace(microsecond=0)
        # TODO: have manager handle the logic
        #retention_strategy

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
        self._expires = new_expires
        # n = datetime.now()
        # n.astimezone().tzinfo.tzname(n.astimezone())
        self._last_updated = datetime.now()

    @property
    def access_location(self) -> str:
        """
        String representation of the location at which this dataset is accessible.

        Depending on the subtype, this may be the string form of a URL, URI, or basic filesystem path.

        Returns
        -------
        str
            String representation of the location at which this dataset is accessible.
        """
        return self._access_location

    @property
    def category(self) -> DataCategory:
        """
        The ::class:`DataCategory` type value for this instance.

        Returns
        -------
        DataCategory
            The ::class:`DataCategory` type value for this instance.
        """
        return self._category

    @property
    def created_on(self) -> Optional[datetime]:
        """
        When this dataset was created, or ``None`` if that is not known.

        Returns
        -------
        Optional[datetime]
            When this dataset was created, or ``None`` if that is not known.
        """
        return self._created_on

    @property
    def data_domain(self) -> DataDomain:
        """
        The data domain for this instance.

        Returns
        -------
        DataDomain
            The ::class:`DataDomain` for this instance.
        """
        return self._data_domain

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
    def derivations(self) -> List[str]:
        """
        List of names of datasets which were derived from this dataset.

        Note that it is not guaranteed that any such dataset still exist and/or are still available.

        Returns
        -------
        List[str]
            List of names of datasets which were derived from this dataset.
        """
        return self._derivations

    @property
    def derived_from(self) -> Optional[str]:
        """
        The name of the dataset from which this dataset was derived, if it is known to have been derived.

        Returns
        -------
        Optional[str]
            The name of the dataset from which this dataset was derived, or ``None`` if this dataset is not known to
            have been derived.
        """
        return self._derived_from

    @property
    def expires(self) -> Optional[datetime]:
        """
        The time after which a dataset may "expire" and be removed, or ``None`` if the dataset is not temporary.

        A dataset may be temporary, meaning its availability and validity cannot be assumed perpetually; e.g., the data
        may be removed from storage.  This property indicates the time through which availability and validity is
        guaranteed.

        Returns
        -------
        Optional[datetime]
            The time after which a dataset may "expire" and be removed, or ``None`` if the dataset is not temporary.
        """
        return self._expires

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
            self._set_expires(self._expires + value)
            return True
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
    def is_read_only(self) -> bool:
        """
        Whether this is a dataset that can only be read from.

        Returns
        -------
        bool
            Whether this is a dataset that can only be read from.
        """
        return self._is_read_only

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
    def last_updated(self) -> Optional[datetime]:
        """
        When this dataset was last updated, or ``None`` if that is not known.

        Note that this includes adjustments to metadata, including the value for ::attribute:`expires`.

        Returns
        -------
        Optional[datetime]
            When this dataset was last updated, or ``None`` if that is not known.
        """
        return self._last_updated

    @property
    def manager(self) -> 'DatasetManager':
        """
        The ::class:`DatasetManager` for this instance.

        Returns
        -------
        DatasetManager
            The ::class:`DatasetManager` for this instance.
        """
        return self._manager

    @manager.setter
    def manager(self, manager: 'DatasetManager'):
        self._manager = manager
        self._manager_uuid = manager.uuid

    @property
    def manager_uuid(self) -> UUID:
        """
        The UUID of the ::class:`DatasetManager` for this instance.

        Returns
        -------
        DatasetManager
            The UUID of the ::class:`DatasetManager` for this instance.
        """
        return self._manager_uuid

    @property
    def name(self) -> str:
        """
        The name for this dataset, which also should be a unique identifier.

        Every dataset in the domain of all datasets known to this instance's ::attribute:`manager` must have a unique
        name value.

        Returns
        -------
        str
            The dataset's unique name.
        """
        return self._name

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

    @property
    def uuid(self) -> UUID:
        """
        The UUID for this instance.

        Returns
        -------
        UUID
            The UUID for this instance.
        """
        return self._uuid

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        """
        Get the serial form of this instance as a dictionary object.

        Returns
        -------
        Dict[str, Union[str, Number, dict, list]]
            The serialized form of this instance.
        """
        serial = dict()
        serial[self._KEY_NAME] = self.name
        serial[self._KEY_DATA_CATEGORY] = self.category.name
        serial[self._KEY_DATA_DOMAIN] = self.data_domain.to_dict()
        # TODO: unit test this
        serial[self._KEY_ACCESS_LOCATION] = self.access_location
        serial[self._KEY_UUID] = str(self.uuid)
        serial[self._KEY_IS_READ_ONLY] = self.is_read_only
        if self.manager_uuid is not None:
            serial[self._KEY_MANAGER_UUID] = str(self.manager_uuid)
        if self.expires is not None:
            serial[self._KEY_EXPIRES] = self.expires.strftime(self.get_datetime_str_format())
        if self.derived_from is not None:
            serial[self._KEY_DERIVED_FROM] = self.derived_from
        if len(self.derivations) > 0:
            serial[self._KEY_DERIVATIONS] = self.derivations
        if self.created_on is not None:
            serial[self._KEY_CREATED_ON] = self.created_on.strftime(self.get_datetime_str_format())
        if self.last_updated is not None:
            serial[self._KEY_LAST_UPDATE] = self.last_updated.strftime(self.get_datetime_str_format())
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

    def __init__(self, uuid: Optional[UUID] = None, datasets: Optional[Dict[str, Dataset]] = None):
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
        """
        pass

    @abstractmethod
    def reload(self, name: str, is_read_only: bool = False, access_location: Optional[str] = None) -> Dataset:
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
        Dataset
            A new dataset object, loaded from a previously stored dataset.
        """
        pass

    @property
    @abstractmethod
    def supported_dataset_types(self) -> Set[Type[Dataset]]:
        """
        The set of ::class:`Dataset` subclass types that this instance supports.

        Typically (but not necessarily always) this will be backed by a static or hard-coded value for the manager
        subtype.

        Returns
        -------
        Set[Type[Dataset]]
            The set of ::class:`Dataset` subclass types that this instance supports.
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
