from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import reduce
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar, Union, Dict, Iterable, Type, Set, List, Optional

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

    def __init__(self, *, item: DataItem, item_name: Optional[str] = None, decode_format: str = 'utf-8'):
        """
        Initialize an instance.

        Parameters
        ----------
        item: DataItem
            The data item for which a domain will be detected.
        item_name: Optional[str]
            The name for the item, which includes important domain metadata in some situations.
        decode_format: str
            The decoder format when decoding byte strings (``utf-8`` by default).
        """
        is_item_file = isinstance(item, Path)
        if is_item_file and item.is_dir():
            raise ValueError(f"{self.__class__.__name__} can't initialize with a directory path as its data item")
        self._item: DataItem = item
        """ The data item for which to detect a domain. """
        self._item_name = self._item.name if is_item_file else item_name
        """ Name for the item; in some situations, contains important constraint metadata (e.g. catchment name). """
        self._decode_format = decode_format
        """ A decoder format sometimes used when reading data item in order to get metadata. """


class AbstractUniversalItemDomainDetector(ItemDataDomainDetector, ABC):
    """
    Abstraction for detector that works with many formats by trying to detect using provided format-specific subtypes.

    A specialized implementation of :class:`ItemDataDomainDetector` that is potentially capable of detecting the data
    domain of data items in multiple data formats.  It accomplishes this by leveraging a collection of known
    :class:`ItemDataDomainDetector` subclasses provided during initialization, and trying to detect an item's domain
    using each of those types.

    Only "vanilla" init params inherent to the init of :class:`ItemDataDomainDetector` directly are provided to
    subclasses when creating new instances: ``item``, ``item_name``, and ``decode_format``.  As such, a subclass that
    needs additional params provided explicitly should not be associated, and will result in exceptions when
    :method:`detect` is called.  Class that need more advanced behavior with respect to the init params of subclass
    instances may override :method:`_try_detection`.
    """

    _data_format: DataFormat = DataFormat.GENERIC
    """ The associated :class:`DataFormat` of this subclass. """

    def __init__(self,
                 *,
                 item: DataItem,
                 item_name: Optional[str] = None,
                 decode_format: str = 'utf-8',
                 detector_types: Iterable[Type[ItemDataDomainDetector]],
                 short_on_success: bool = False,
                 type_sort_func: Optional[Callable[[Type[ItemDataDomainDetector]], Any]] = None,
                 **kwargs):
        """
        Initialize an instance.

        Parameters
        ----------
        item: DataItem
            The data item for which a domain will be detected.
        item_name: Optional[str]
            The name for the item, which includes important domain metadata in some situations.
        decode_format: str
            The decoder format when decoding byte strings (``utf-8`` by default).
        detector_types: Iterable[Type[ItemDataDomainDetector]]
            The :class:`ItemDataDomainDetector` subclasses that this instance will try to defer to when detecting.
        short_on_success: bool
            Indication of whether :method:`detect` should short circuit and return the 1st successful detection, rather
            than try all subclasses and risk multiple detections, and thus an error condition (default: ``False``).
        type_sort_func: Optional[Callable[[Type[ItemDataDomainDetector]], Any]]
            Optional function necessary for calls to usage of the built-in ``sorted`` function to sort detector
            subclasses during various instance operations, and serving as the ``key`` argument to ``sorted``; note that
            sorting is performed in such places IFF this is validly set, as the subclass themselves - i.e., the
            :class:`type` objects - do not implement `<`.
        kwargs
        """
        super().__init__(item=item, item_name=item_name, decode_format=decode_format)
        self._detector_types: Set[Type[ItemDataDomainDetector]] = set(detector_types)
        if len(self._detector_types) == 0:
            raise ValueError(f"{self.__class__.__name__} received empty collection of detector subclasses during init")
        self._short_on_success: bool = short_on_success
        self._type_sort_func: Optional[Callable[[Type[ItemDataDomainDetector]], Any]] = type_sort_func

    def _try_detection(self, detector_type: Type[ItemDataDomainDetector]) -> Optional[DataDomain]:
        """
        Initialize an instance of the given detector subclass and attempt domain detection using it.

        Initialize an instance of the given detector subclass, using only "vanilla" init params inherent of
        :class:`ItemDataDomainDetector`: ``item``, ``item_name``, and ``decode_format``.  Then call that instance's
        :method:`ItemDataDomainDetector.detect` method, passing no extra keyword args.  If ``detect`` succeeds, return
        the resulting :class:`DataDomain`, but if it fails, catch the raised exception and return ``None``.

        Parameters
        ----------
        detector_type: Type[ItemDataDomainDetector]
            The subclass of :class:`ItemDataDomainDetector` to use for detection.

        Returns
        -------
        Optional[DataDomain]
            The domain, if it could be detected by the sub-instance; otherwise ``None``.

        Raises
        ------
        TypeError
            Raised if an associated subclass type requires additional init params beyond ``item``, ``item_name``, and
            ``decode_format``.
        """
        detector = detector_type(item=self._item, item_name=self._item_name, decode_format=self._decode_format)
        try:
            return detector.detect()
        except Exception as e:
            logging.debug("%(this_class)s could not detect domain of %(item_type)s item '%(item_name)s' using "
                          "%(detector_name)s due to %(exception_type)s: %(exception_msg)s",
                          dict(this_class=self.__class__.__name__,
                               item_type=self._item.__class__.__name__,
                               item_name=self._item_name if self._item_name else 'n/a',
                               detector_name=detector_type.__name__,
                               exception_type=e.__class__.__name__,
                               exception_msg=str(e)))
            return None

    @property
    def covered_formats(self) -> Set[DataFormat]:
        """
        Get the data formats for which there is at least one associated, known subclass of detector.

        Returns
        -------
        Set[DataFormat]
            The data formats for which there is at least one associated, known subclass of detector.
        """
        return {detector.get_data_format() for detector in self._detector_types if
                detector.get_data_format() != DataFormat.GENERIC and detector.get_data_format() != DataFormat.EMPTY}

    def detect(self, **kwargs) -> DataDomain:
        """
        Detect and return the data domain.

        Detect a domain by calling the analogous method of one or more instance of the known subclasses of
        :class:`ItemDataDomainDetector` provided during instance initialization. Selection of the right subclass to use
        for this is based on brute-force trials - i.e., a subclass is selected, an instance is created, the ``detect``
        method is called, and we assess what happens.

        Only "vanilla" init params inherent to the init of :class:`ItemDataDomainDetector` directly are provided to
        subclasses when creating new instances: ``item``, ``item_name``, and ``decode_format``.

        The ``type_sort_func`` init parameter is used to control the order of subclasses trials.  If it was
        ``None``, then the order is arbitrary.  If not, this method calls the built-in ``sorted()`` function to sort the
        subclasses and passes the value of the aforementioned init param to ``sorted`` as the latter's ``key`` param.

        Another instance init param - ``short_on_success`` also has significant impact on this method.  When ``True``,
        this method will return the first successfully detected :class:`DataDomain`.  If ``False``, a trial will occur
        for all the associate detector subclasses.  In this case, if there are multiple, distinct domain values,  a
        :class:`DmodRuntimeError` is raised.

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
        TypeError
            Raised if an associated subclass type requires additional init params beyond what this instance provides in
            the implementation of :method:`_try_detection`.
        DmodRuntimeError
            If it was not possible to properly detect a single valid domain.

        See Also
        --------
        _try_detection
        """
        if self._type_sort_func is None:
            detector_subclasses = self._detector_types
        else:
            detector_subclasses = sorted(self._detector_types, key=self._type_sort_func)

        if self._short_on_success:
            for detector_type in detector_subclasses:
                result = self._try_detection(detector_type=detector_type)
                if isinstance(result, DataDomain):
                    return result
            raise DmodRuntimeError("No domain could be detected for item.")

        results = {subclass: self._try_detection(detector_type=subclass) for subclass in detector_subclasses}
        successes = {sub.__name__: result for sub, result in results.items() if isinstance(result, DataDomain)}

        # Obviously raise if we don't detect anything ...
        if len(successes) == 0:
            raise DmodRuntimeError("No domain could be detected for item.")
        # ... and return if only one subclass could successfully detect a domain
        elif len(successes) == 1:
            return next(iter(successes.values()))
        # Also, if multiple detector subclasses succeeded, but all resulting DataDomain objects are equal, this is fine
        elif len(set(successes.values())) == 1:
            return next(iter(successes.values()))
        # But multiple different DataDomain results mean there's ambiguity, and thus is a problem
        else:
            raise DmodRuntimeError(f"Multiple distinct domains detected for item by different detectors: {successes!s}")

    def get_detectors(self, data_format: Optional[DataFormat] = None) -> List[Type[ItemDataDomainDetector]]:
        """
        Get associated :class:`ItemDataDomainDetector` subclasses, potentially sorted and/or filtered by data format.

        Parameters
        ----------
        data_format: Optional[DataFormat]
            Optional data format, used for filtering the returned subclasses.

        Returns
        -------
        List[Type[ItemDataDomainDetector]]
            A list of :class:`ItemDataDomainDetector` subclasses, potentially sorted and/or filtered.
        """
        if data_format is None:
            results = [d for d in self._detector_types]
        else:
            results = [d for d in self._detector_types if d.get_data_format() == data_format]
        if self._type_sort_func is not None:
            return sorted(results, key=self._type_sort_func)
        return results

    def is_associated(self, subclass: Type[ItemDataDomainDetector]) -> bool:
        """
        Whether this detector subclass is associated with this instance.

        Parameters
        ----------
        subclass: Union[str, Type[ItemDataDomainDetector]]
            The potentially registered subclass type.

        Returns
        -------
        bool
            Whether this is an associated subclass.
        """
        return subclass in self._detector_types


U = TypeVar("U", bound=AbstractUniversalItemDomainDetector)


class AbstractDataCollectionDomainDetector(AbstractDomainDetector, Generic[U], ABC):
    """
    Abstract domain detector that operates on a grouped collection of data items rather than just one item.

    Simple abstraction for generalized detector that can detect the aggregate domain for a collection of many data
    items.  These items can be given as a dictionary (item names mapped to data items), a :class:`Dataset` (with a valid
    :class:`DatasetManager` set), or a :class:`Path` to a directory containing data files.

    Instances detect the domain for a collection of data by using generic :class:`U` instances (bound to
    :class:`AbstractUniversalItemDomainDetector`) to detect the domain of individual items within the data collection,
    and then merging the domains together. Concrete implementations must specify the generic :class:`U` type and the
    :method:`get_item_detectors` method.
    """

    # TODO: (later) add mechanism for more intelligent hinting at what kinds of detectors to use
    def __init__(self, data_collection: DataCollection, collection_name: Optional[str] = None):
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
        Detection is performed by merging individual item domains detected using :class:`U` instances.  This type does
        not influence the details of how individual domains detections are performed by :class:`U` objects.  The
        subsequent merging is performed by reducing individual item domains using :method:`DataDomain.merge_domains`.
        The order of the items processed when reducing is based on the order of results of a call to
        :method:`get_item_detectors`.

        Returns
        -------
        DataDomain
            The detected domain.

        Raises
        ------
        DmodRuntimeError
            If it was not possible to properly detect the domain.
        """
        domain = reduce(DataDomain.merge_domains, [det.detect() for _, det in self.get_item_detectors().items()])
        # If this domain has a format with a self-reference to dataset id, and we have a name, then set that restriction
        if StandardDatasetIndex.DATA_ID in domain.data_format.indices_to_fields().keys() and self._collection_name:
            domain.discrete_restrictions[StandardDatasetIndex.DATA_ID] = DiscreteRestriction(
                variable=StandardDatasetIndex.DATA_ID,
                values=[self._collection_name]
            )
        return domain

    @abstractmethod
    def get_item_detectors(self) -> Dict[str, U]:
        """
        Get initialized detection objects, keyed by item names, for items within this instance's data collection.

        Returns
        -------
        Dict[str, U]
            Dictionary of per-item initialize detection objects, keyed by item name.
        """
        pass

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
