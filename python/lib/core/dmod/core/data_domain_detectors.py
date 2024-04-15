from __future__ import annotations

from abc import ABC, abstractmethod
from functools import reduce
from pathlib import Path
from typing import TypeVar, Union, Dict, Type, Set, List, Optional

from .common.reader import ReadSeeker
from .dataset import Dataset
from .exception import DmodRuntimeError
from .meta_data import DataDomain, DataFormat, StandardDatasetIndex, DiscreteRestriction

DataItem = TypeVar('DataItem', bound=Union[bytes, ReadSeeker, Path])
DataCollection = TypeVar('DataCollection', bound=Union[Dataset, Dict[str, Union[bytes, ReadSeeker]], Path])


class AbstractDomainDetector(ABC):
    """ Abstraction for something that will automatically detect a :class:`DataDomain` for some data. """

    @abstractmethod
    def detect(self, **kwargs) -> DataDomain:
        """
        Detect and return the data domain.

        Parameters
        ----------
        kwargs
            Optional kwargs applicable to the subtype, which may enhance or add to the domain detection and generation
            capabilities, but which should not be required to produce a valid domain.

        Returns
        -------
        DataDomain
            The detected domain.

        Raises
        ------
        DmodRuntimeError
            If it was not possible to properly detect the domain.
        """
        pass


class ItemDataDomainDetectorRegistry:
    """ A singleton registry in which to track the subtypes of :class`ItemDataDomainDetector`. """

    _instance = None

    @classmethod
    def get_instance(cls) -> ItemDataDomainDetectorRegistry:
        """ Get the singleton registry instance. """
        if cls._instance is None:
            cls._instance = ItemDataDomainDetectorRegistry()
        return cls._instance

    def __init__(self):
        if self._instance is not None:
            raise RuntimeError(f"Attempting to create second {self.__class__.__name__} instance!")
        self._detectors: Set[Type[ItemDataDomainDetector]] = set()
        """ All registered subclasses, keyed by name. """

    def is_registered(self, entry: Type[ItemDataDomainDetector]) -> bool:
        """
        Whether this is a registered subclass.

        Parameters
        ----------
        entry: Union[str, Type[ItemDataDomainDetector]]
            The potentially registered subclass type.

        Returns
        -------
        bool
            Whether this is a registered subclass.
        """
        return entry in self._detectors

    def get_all_subclasses(self, do_sorted: bool = False) -> List[Type[ItemDataDomainDetector]]:
        """
        Get a list of all registered :class:`ItemDataDomainDetector` subclasses.

        Parameters
        ----------
        do_sorted: bool
            Whether to sort the returned list, using class name as the sort key (``False`` by default).

        Returns
        -------
        List[Type[ItemDataDomainDetector]]
            A (potentially sorted by class name) list of all registered :class:`ItemDataDomainDetector` subclasses.
        """
        if do_sorted:
            return sorted([d for d in self._detectors], key=lambda detector_subclass: detector_subclass.__name__)
        return [d for d in self._detectors]

    def get_for_format(self, data_format: DataFormat) -> List[Type[ItemDataDomainDetector]]:
        """
        Get a sorted (by subclass name) list of the detector subclasses associated with the given format.

        Parameters
        ----------
        data_format: DataFormat
            The data format of interest.

        Returns
        -------
        List[Type[ItemDataDomainDetector]]
            The sorted detector subclasses associated with the given format.
        """
        subclasses = [dt for dt in self._detectors if dt.get_data_format() == data_format]
        return sorted(subclasses, key=lambda detector_subclass: detector_subclass.__name__)

    def register(self, subclass: Type[ItemDataDomainDetector]):
        """
        Register the given subclass of :class:`ItemDataDomainDetector`.

        Parameters
        ----------
        subclass: Type[ItemDataDomainDetector]
            A subclass of :class:`ItemDataDomainDetector`.

        Notes
        -----
        If an already-registered subclass is passed in another call to this method, nothing will happen.  The instance's
        state will not change, nor will an error be thrown, and the method will quietly return.
        """
        self._detectors.add(subclass)

    def unregister(self, subclass: Type[ItemDataDomainDetector]):
        """
        Unregister the given subclass of :class:`ItemDataDomainDetector`.

        Parameters
        ----------
        subclass

        Raises
        -------
        DmodRuntimeError
            If the given subclass was not already registered.
        """
        if subclass not in self._detectors:
            raise DmodRuntimeError(f"{self.__class__.__name__} can't unregister unknown subclass '{subclass.__name__}'")
        self._detectors.remove(subclass)


class ItemDataDomainDetector(AbstractDomainDetector, ABC):
    """
    Type that can examine a data item and detect its individual :class:`DataDomain`.

    Abstraction for detecting the domain of a single data item.  Here, a data item specifically means either
    :class:`bytes` object with raw data, a :class:`ReadSeeker` object that can read data multiple times, or a
    :class:`Path` object pointing to a file (not a directory).

    This class provides the :method:`get_data_format` class functions important for use with the
    :class:`ItemDataDomainDetectorRegistry` singleton object.  This method lets the registry (and other users) identify
    the :class:`DataFormat` for which a subclass can determine domains.  Subclasses must be implemented to set the
    backing class variable.

    Note that subtypes must explicitly be registered with the :class:`ItemDataDomainDetectorRegistry` singleton.
    """

    _data_format: DataFormat = None
    """ The associated :class:`DataFormat` of this subclass. """

    @classmethod
    def get_data_format(cls) -> DataFormat:
        """
        Get the associated data format for this subclass of :class:`ItemDataDomainDetector`.

        Returns
        -------
        DataFormat
            The associated :class:`DataFormat` of this subclass.
        """
        return cls._data_format

    def __init__(self, item: DataItem, item_name: Optional[str] = None, decode_format: str = 'utf-8', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._item: DataItem = item
        """ The data item for which to detect a domain. """
        self._is_item_file = isinstance(self._item, Path)
        """ Private flag of whether data item is a :class:`Path` object (that points to a file, per other checks). """
        self._item_name = self._item.name if self._is_item_file else item_name
        """ Name for the item; in some situations, contains important constraint metadata (e.g. catchment name). """
        self._decode_format = decode_format
        """ A decoder format sometimes used when reading data item in order to get metadata. """
        if self._is_item_file and self._item.is_dir():
            raise ValueError(f"{self.__class__.__name__} can't initialize with a directory path as its data item")


class UniversalItemDomainDetector(ItemDataDomainDetector):
    """
    A special type of detector that works with all supported formats by trying all registered, format-specific subtypes.

    A specialized implementation of :class:`ItemDataDomainDetector` that is registered to the ``GENERIC``
    :class:`DataFormat`.  It is implemented to be capable of detecting the domain regardless of the actual format of the
    data.  It accomplishes this by using the registered subclasses associated with all the non-``GENERIC`` formats, and
    trying to detect a domain using each of those types.
    """

    _data_format: DataFormat = DataFormat.GENERIC
    """ The associated :class:`DataFormat` of this subclass. """

    def detect(self, **kwargs) -> DataDomain:
        """
        Detect and return the data domain.

        Detect a domain by calling the analogous method of an instance of registered subclasses of
        :class:`ItemDataDomainDetector` (excluding those with ``GENERIC`` or ``EMPTY`` :class:`DataFormat`).  Selection
        of the right subclass to use for this is based on brute-force trials - i.e., a subclass is selected, an instance
        is created, the ``detect`` method is called, and we assess what happens - along with an early exit mechanism for
        explicit format suggestions.

        Subclasses are tried in groups according to their associated :class:`DataFormat`.  The order of groups may be
        controlled by providing one or more format "suggestions", which will be tried first in the order provided. Also,
        one or more excluded formats can be optionally provided. The ``GENERIC`` and ``EMPTY`` formats are always
        treated as excluded. Iteration order of subclasses within a group is based on registration name by default -
        i.e., the value from :method:`ItemDataDomainDetector.get_registration_name` for each subclass - but a sorting
        key function can be provided to control this also.

        If/when a subclass instance's ``detect`` call returns a domain, no other subclasses for that format group are
        tried, but this function only returns that domain value immediately if the associated format was a provided
        suggestion.  Otherwise, iteration continues to the next group.  This is important, because if more than one
        class can detect a domain, there is an implicit ambiguity in the domain, and a :class:`DmodRuntimeError` is
        raised.

        Parameters
        ----------
        kwargs
            Optional kwargs applicable to the subtype, which may enhance or add to the domain detection and generation
            capabilities, but which should not be required to produce a valid domain.

        Keyword Args
        ------------
        excluded_formats: Union[DataFormat, Set[DataFormat]]
            Optional individual or set of :class:`DataFormat` to be excluded from testing; a :class:`ValueError` is
            raised if a format appears in both this and ``suggested_formats``.
        suggested_formats: Union[DataFormat, List[DataFormat]]
            An optional :class:`DataFormat` or list of :class:`DataFormat` values to try first, with any successes
            being immediately returned; a :class:`ValueError` is raised if a format appears more than once across both
            this and ``excluded_formats``.
        sort_key:
            Optional function of one argument (the subclass type) used to extract a comparison key from each registered
            subclasses when attempting to determine the order in which to try them (within the context of those
            associated with the particular data format being tried); if not provided, the order is based on each
            subclass's registration ``name``.

        Returns
        -------
        DataDomain
            The detected domain.

        Raises
        ------
        ValueError
            Raised if a :class:`DataFormat` appears multiple times across both ``excluded_formats`` and
            ``suggested_formats``; i.e., if any data format value is duplicated in the hypothetical list produced by
            ``list(kwargs.get('excluded_formats', [])) + list(kwargs.get('suggested_formats', []))``.
        DmodRuntimeError
            If it was not possible to properly detect the domain.
        """
        def try_detection(d_format: DataFormat) -> Optional[DataDomain]:
            subclasses = ItemDataDomainDetectorRegistry.get_instance().get_for_format(d_format)
            if 'sort_key' in kwargs:
                subclasses = sorted(subclasses, key=kwargs['sort_key'])
            for subclass_type in subclasses:
                try:
                    return subclass_type(item=self._item, item_name=self._item_name).detect()
                except:
                    pass
            return None

        excluded = kwargs.get('excluded_formats', set())
        if isinstance(excluded, DataFormat):
            excluded = {excluded}
        # Always exclude these two
        excluded.add(DataFormat.GENERIC)
        excluded.add(DataFormat.EMPTY)
        suggested = kwargs.get('suggested_formats', list())
        if isinstance(suggested, DataFormat):
            suggested = [suggested]
        if not excluded.isdisjoint(suggested):
            raise ValueError(f"Can't include data format in both exclusions and suggestions for domain detection.")
        if len(suggested) != len(set(suggested)):
            raise ValueError(f"Can't include data format multiple times in ordered suggestions for domain detection.")

        remaining_formats = {df for df in DataFormat if df not in excluded}

        # Try suggestions first, returning immediately if any are successful
        for data_format in suggested:
            remaining_formats.remove(data_format)
            result = try_detection(d_format=data_format)
            if result is not None:
                return result

        # Now we get to others
        main_trials = (try_detection(d_format=df) for df in remaining_formats)
        main_results = [t for t in main_trials if t is not None]
        if len(main_results) == 0:
            raise DmodRuntimeError("No domain could be detected for item.")
        elif len(main_results) == 1:
            return main_results[0]
        # Multiple results mean there's a problem (also, they can't be equal because they will have different formats)
        else:
            raise DmodRuntimeError(f"Multiple conflicting domain detected for item in the following formats: "
                                   f"{','.join([d.data_format.name for d in main_results])}")


# Register the universal tracker type
ItemDataDomainDetectorRegistry.get_instance().register(UniversalItemDomainDetector)


class DataCollectionDomainDetector(AbstractDomainDetector):
    """
    Domain detector that operates on a grouped collection of data items rather than just one item.

    Simple, generalized detector that can detect the aggregate domain for a collection of many data items.  These items
    can be given as a dictionary (item names mapped to data items), a :class:`Dataset` (with a valid
    :class:`DatasetManager` set), or a :class:`Path` to a directory containing data files.
    """

    # TODO: (later) add mechanism for more intelligent hinting at what kinds of detectors to use
    def __init__(self, data_collection: DataCollection, collection_name: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data_collection: DataCollection = data_collection
        """ Collection of data items, analogous to a :class:`Dataset`, if not a dataset outright. """
        self._collection_name: Optional[str] = collection_name
        """
        Optional name for collection, which is important when domains involve a ``data_id`` restriction.
        
        Note that **IFF** the data collection is a :class:`Dataset` object **AND** the passed ``collection_name`` param
        is ``None``, then this attribute will be set to the ``name`` attribute of the dataset collection itself.
        """
        if collection_name is None and isinstance(data_collection, Dataset):
            self._collection_name = data_collection.name

        if isinstance(self._data_collection, Path) and not self._data_collection.is_dir():
            raise ValueError(f"{self.__class__.__name__} initialized with a path require this path to be a directory.")
        if isinstance(self._data_collection, Dataset) and self._data_collection.manager is None:
            raise ValueError(f"Dataset used to initialize {self.__class__.__name__} must have manager set.")

    def detect(self, **kwargs) -> DataDomain:
        """
        Detect and return the data domain.

        Parameters
        ----------
        kwargs
            Optional kwargs applicable to the subtype, which may enhance or add to the domain detection and generation
            capabilities, but which should not be required to produce a valid domain.

        Notes
        -----
        Detection is performed by merging individual item domains detected using :class:`UniversalItemDomainDetector`
        instances.  This type does not influence the details of how individual domains detections are performed by
        :class:`UniversalItemDomainDetector` objects.  The subsequent merging is performed by reducing the
        individual item domains using :method:`DataDomain.merge_domains`. The order of the items processed when reducing
        is based on the order of results of a call to :method:`get_item_names`.

        Returns
        -------
        DataDomain
            The detected domain.

        Raises
        ------
        DmodRuntimeError
            If it was not possible to properly detect the domain.
        """
        domain = reduce(DataDomain.merge_domains,
                        {UniversalItemDomainDetector(item=self.get_item(i), item_name=i).detect() for i in
                         self.get_item_names()})
        # If this domain has a format with a self-reference to dataset id, and we have a name, then set that restriction
        if StandardDatasetIndex.DATA_ID in domain.data_format.indices_to_fields().keys() and self._collection_name:
            domain.discrete_restrictions[StandardDatasetIndex.DATA_ID] = DiscreteRestriction(
                variable=StandardDatasetIndex.DATA_ID,
                values=[self._collection_name]
            )
        return domain

    def get_item_names(self) -> Set[str]:
        """
        Get the names of data items in the collection.

        Get the individual item names of the items in the data collection for this instance.  Each returned name can be
        used to retrieve the unique corresponding item via :method:`get_item`.  For file items in particular, this means
        the names will be the string representation of each file's path relative to the collection directory.

        Returns
        -------
        Set[str]
            Names of data items in the collection.

        See Also
        --------
        get_item
        """
        if isinstance(self._data_collection, dict):
            return set(self._data_collection.keys())
        elif isinstance(self._data_collection, Path):
            return set(str(p.relative_to(self._data_collection)) for p in self._data_collection.glob("**/*"))
        elif isinstance(self._data_collection, Dataset) and self._data_collection.manager is not None:
            return set(self._data_collection.manager.list_files(self._data_collection.name))
        else:
            raise DmodRuntimeError(f"{self.__class__.__name__} received unexpected collection type "
                                   f"{self._data_collection.__class__.__name__}")

    def get_item(self, item_name: str) -> DataItem:
        """
        Get the item with the given name from the instance's data collection.

        Parameters
        ----------
        item_name: str
            The name of the item of interest.

        Returns
        -------
        DataItem
            The item with the given name from the instance's data collection.
        """
        if isinstance(self._data_collection, dict):
            return self._data_collection[item_name]
        elif isinstance(self._data_collection, Path):
            return self._data_collection.joinpath(item_name)
        else:
            return self._data_collection.manager.get_data(dataset_name=self._data_collection.name, item_name=item_name)
