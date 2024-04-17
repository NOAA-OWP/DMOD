from dmod.core.data_domain_detectors import (AbstractUniversalItemDomainDetector, AbstractDataCollectionDomainDetector,
                                             DataItem, ItemDataDomainDetector)
from dmod.modeldata.data.item_domain_detector import (AorcCsvFileDomainDetector, GeoPackageHydrofabricDomainDetector,
                                                      RealizationConfigDomainDetector)
from typing import Any, Callable, Dict, List, Optional, Set, Type


class ClientUniversalItemDomainDetector(AbstractUniversalItemDomainDetector):
    """
    Concrete implementation of :class:`AbstractUniversalItemDomainDetector`, with some default detector subclass types.


    """
    _default_detector_types: Set[Type[ItemDataDomainDetector]] = {
        AorcCsvFileDomainDetector,
        GeoPackageHydrofabricDomainDetector,
        RealizationConfigDomainDetector
    }
    """ Default detector subclasses always associated with instances of this type. """

    @classmethod
    def get_default_detectors(cls) -> List[Type[ItemDataDomainDetector]]:
        return [d for d in cls._default_detector_types]

    def __init__(self,
                 item: DataItem,
                 item_name: Optional[str] = None,
                 decode_format: str = 'utf-8',
                 short_on_success: bool = False,
                 type_sort_func: Optional[Callable[[Type[ItemDataDomainDetector]], Any]] = None):
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
        short_on_success: Optional[bool]
            Indication of whether :method:`detect` should short circuit and return the 1st successful detection, rather
            than try all subclasses and risk multiple detections, and thus an error condition (default: ``False``).
        type_sort_func: Optional[Callable[[Type[ItemDataDomainDetector]], Any]]
            Optional function necessary for calls to usage of the built-in ``sorted`` function to sort detector
            subclasses during various instance operations, and serving as the ``key`` argument to ``sorted``; note that
            sorting is performed in such places IFF this is validly set, as the subclass themselves - i.e., the
            :class:`type` objects - do not implement `<`.
        """
        super().__init__(item=item,
                         item_name=item_name,
                         decode_format=decode_format,
                         detector_types=self._default_detector_types,
                         short_on_success=short_on_success,
                         type_sort_func=type_sort_func)


class ClientDataCollectionDomainDetector(AbstractDataCollectionDomainDetector[ClientUniversalItemDomainDetector]):
    """
    Concrete implementation relying on :class:`UniversalItemDomainDetector` to detect items.
    """

    def get_item_detectors(self) -> Dict[str, ClientUniversalItemDomainDetector]:
        """
        Get initialized detection objects, keyed by item names, for items within this instance's data collection.

        Returns
        -------
        Dict[str, ClientUniversalItemDomainDetector]
            Dictionary of per-item initialize detection objects, keyed by item name.
        """
        detectors = dict()
        for item_name in self.get_item_names():
            detectors[item_name] = ClientUniversalItemDomainDetector(item=self.get_item(item_name), item_name=item_name)
        return detectors
