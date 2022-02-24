from abc import ABC, abstractmethod
from .meta_data import ContinuousRestriction, DataCategory, DataFormat, DiscreteRestriction, TimeRange
from datetime import datetime, timedelta

from dmod.communication.serializeable import Serializable
from numbers import Number
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Union
from uuid import UUID, uuid4


class Dataset(Serializable, ABC):
    """
    Abstraction representation of a grouped collection of data and its metadata.
    """

    _SERIAL_DATETIME_STR_FORMAT = '%Y-%m-%d %H:%M:%S %z'

    _KEY_ACCESS_LOCATION = 'access_location'
    _KEY_CREATED_ON = 'create_on'
    _KEY_DATA_CATEGORY = 'data_category'
    _KEY_DATA_FORMAT = 'data_format'
    _KEY_DERIVED_FROM = 'derived_from'
    _KEY_DERIVATIONS = 'derivations'
    _KEY_EXPIRES = 'expires'
    _KEY_IS_READ_ONLY = 'is_read_only'
    _KEY_LAST_UPDATE = 'last_updated'
    _KEY_MANAGER_UUID = 'manager_uuid'
    _KEY_NAME = 'name'
    _KEY_UUID = 'uuid'
    _KEY_TIME_RANGE = 'time_range'

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
        return datetime.strptime(json_obj[key], cls.get_datetime_str_format()) if key in json_obj else None

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        try:
            if cls._KEY_TIME_RANGE in json_obj:
                time_range = TimeRange.factory_init_from_deserialized_json(json_obj[cls._KEY_TIME_RANGE])
            else:
                time_range = None

            if cls._KEY_MANAGER_UUID in json_obj:
                manager_uuid = UUID(json_obj[cls._KEY_MANAGER_UUID])
            else:
                manager_uuid = None

            cls(name=json_obj[cls._KEY_NAME],
                category=DataCategory.get_for_name(json_obj[cls._KEY_DATA_CATEGORY]),
                data_format=DataFormat.get_for_name(json_obj[cls._KEY_DATA_FORMAT]),
                access_location=json_obj[cls._KEY_ACCESS_LOCATION],
                uuid=UUID(json_obj[cls._KEY_UUID]),
                manager_uuid=manager_uuid,
                is_read_only=json_obj[cls._KEY_IS_READ_ONLY],
                time_range=time_range,
                expires=cls._date_parse_helper(json_obj, cls._KEY_EXPIRES),
                derived_from=json_obj[cls._KEY_DERIVED_FROM] if cls._KEY_DERIVED_FROM in json_obj else None,
                derivations=json_obj[cls._KEY_DERIVATIONS] if cls._KEY_DERIVATIONS in json_obj else None,
                created_on=cls._date_parse_helper(json_obj, cls._KEY_CREATED_ON),
                last_updated=cls._date_parse_helper(json_obj, cls._KEY_LAST_UPDATE),
                **cls.additional_init_param_deserialized(json_obj))
        except:
            return None

    def __init__(self, name: str, category: DataCategory, data_format: DataFormat, access_location: str,
                 uuid: Optional[UUID], manager: Optional['DatasetManager'] = None, manager_uuid: Optional[UUID] = None,
                 is_read_only: bool = True, time_range: Optional[TimeRange] = None, expires: Optional[datetime] = None,
                 derived_from: Optional[str] = None, derivations: Optional[List[str]] = None,
                 created_on: Optional[datetime] = None, last_updated: Optional[datetime] = None):
        self._name = name
        self._category = category
        self._data_format = data_format
        self._access_location = access_location
        self._uuid = uuid4() if uuid is None else uuid
        self._manager = manager
        self._manager_uuid = manager.uuid if manager is not None else manager_uuid
        self._is_read_only = is_read_only
        self._time_range = time_range
        self._expires = expires
        # TODO: handle domain properly
        #domain
        self._derived_from = derived_from
        self._derivations = derivations if derivations is not None else list()
        self._created_on = created_on
        self._last_updated = last_updated
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
    def data_format(self) -> DataFormat:
        """
        The ::class:`DataFormat` type value for this instance.

        Returns
        -------
        DataCategory
            The ::class:`DataFormat` type value for this instance.
        """
        return self._data_format

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
        return self.data_format.data_fields

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
        return self._time_range

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
        serial[self._KEY_DATA_CATEGORY] = self.category
        serial[self._KEY_DATA_FORMAT] = self.data_format
        # TODO: unit test this
        serial[self._KEY_ACCESS_LOCATION] = self.access_location
        serial[self._KEY_UUID] = str(self.uuid)
        serial[self._KEY_IS_READ_ONLY] = self.is_read_only
        if self.manager_uuid is not None:
            serial[self._KEY_MANAGER_UUID] = str(self.manager_uuid)
        if self.time_range is not None:
            serial[self._KEY_TIME_RANGE] = self.time_range
        if self.expires is not None:
            serial[self._KEY_EXPIRES] = self.expires
        if self.derived_from is not None:
            serial[self._KEY_DERIVED_FROM] = self.derived_from
        serial[self._KEY_DERIVATIONS] = self.derivations
        if self.created_on is not None:
            serial[self._KEY_CREATED_ON] = self.created_on
        if self.last_updated is not None:
            serial[self._KEY_LAST_UPDATE] = self.last_updated
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

    # TODO: implement functions and routines for scrubbing temporary datasets as needed

    @abstractmethod
    def create(self, name: str, category: DataCategory, data_format: DataFormat, is_read_only: bool,
               files_dir: Optional[Path] = None, time_range: Optional[TimeRange] = None, **kwargs) -> Dataset:
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
        data_format : DataFormat
            The data format for the new dataset.
        is_read_only : bool
            Whether the new dataset is read-only.
        files_dir : Optional[Path]
            Optional path to a directory containing initial data for the dataset (essential for read-only datasets).
        time_range : Optional[TimeRange]
            Optional time range over which the created dataset has data.
        kwargs
            Implementation specific args.

        Returns
        -------
        Dataset
            A newly created dataset instance ready for use.
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
