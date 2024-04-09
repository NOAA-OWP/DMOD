name = 'client'

from dmod.core.dataset import ItemDataDomainDetectorRegistry


def register_modeldata_domain_detectors() -> bool:
    """
    Register the known item domain detectors implemented within the ``dmod.modeldata`` package, if it is installed.

    Returns
    -------
    bool
        Whether the registration succeeded, which typically equates to whether ``dmod.modeldata`` was installed.
    """
    try:
        from dmod.modeldata.data.item_domain_detector import (AorcCsvFileDomainDetector, RealizationConfigDomainDetector,
                                                              GeoPackageHydrofabricDomainDetector)
        for d in (AorcCsvFileDomainDetector, GeoPackageHydrofabricDomainDetector, RealizationConfigDomainDetector):
            ItemDataDomainDetectorRegistry.get_instance().register(d)
        return True
    except ModuleNotFoundError:
        return False