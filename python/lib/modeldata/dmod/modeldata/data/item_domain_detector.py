from dmod.core.meta_data import DataDomain, DataFormat, DiscreteRestriction, StandardDatasetIndex, TimeRange
from dmod.core.common.reader import RepeatableReader
from dmod.core.exception import DmodRuntimeError
from dmod.core.dataset import ItemDataDomainDetector
from pandas import read_csv as pandas_read_csv

from typing import Optional
from io import StringIO
import re

from ..hydrofabric.geopackage_hydrofabric import GeoPackageHydrofabric

# Try to do this if ngen-config package is available
try:
    import ngen.config.realization
    __NGEN_CONFIG_INSTALLED = True
except ModuleNotFoundError:
    __NGEN_CONFIG_INSTALLED = False


class AorcCsvFileDomainDetector(ItemDataDomainDetector, format_type=DataFormat.AORC_CSV):
    """
    Subclass for detecting domains of NextGen regridded per-catchment AORC forcing CSV files.

    Instances must be explicitly or implicitly provided an item name along with the item.  Receiving a :class:`Path`
    object implicitly satisfies this, with the object's ``name`` property used.  This is required because the applicable
    catchment for data is not within the data itself; the convention is to include the catchment id as part of the file
    name.
    """

    _csv_header: str = "Time,RAINRATE,Q2D,T2D,U2D,V2D,LWDOWN,SWDOWN,PSFC"
    _datetime_format: str = "%Y-%m-%d %H:%M:%S"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._item_name is None:
            raise DmodRuntimeError(f"{self.__class__.__name__} must be passed an item name on init unless item is file")

        self._num_time_steps = None

    def _get_catchment_id(self) -> str:
        # TODO: test
        pattern = re.compile('^.*(cat)[_-](\d+)\D.*$')
        matches = pattern.match(self._item_name)
        if matches:
            return f"{matches.group(1)}-{matches.group(2)}"
        else:
            raise DmodRuntimeError(f"{self.__class__.__name__} couldn't parse cat id from name '{self._item_name}'")

    def _get_cat_restriction(self) -> DiscreteRestriction:
        """ Get :class:`DiscreteRestriction` defining applicable catchments (i.e., catchment) for the domain. """
        return DiscreteRestriction(variable=StandardDatasetIndex.CATCHMENT_ID, values=[self._get_catchment_id()])

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

        # Do this early to fail here rather than try to load the dataframe
        cat_restriction = self._get_cat_restriction()
        data = StringIO(self._item.decode(self._decode_format)) if isinstance(self._item, bytes) else self._item
        dt_index = self.get_data_format().indices_to_fields()[StandardDatasetIndex.TIME]
        # TODO: (later) perhaps do a little more about the header checking
        df = pandas_read_csv(data, parse_dates=[0])
        self._num_time_steps = df.shape[0]
        date_range = TimeRange(begin=df.iloc[0][dt_index].to_pydatetime(), end=df.iloc[-1][dt_index].to_pydatetime())
        return DataDomain(data_format=self.get_data_format(), continuous_restrictions=[date_range],
                          discrete_restrictions=[cat_restriction])


# TODO: track and record hydrofabric ids and file names of what's out there so that we recognize known versions/regions


# TODO: might need to expand things in the future ... there are other geopackage formats (e.g., older NextGen
#  hydrofabric versions that used "id" instead of "divide_id") and maybe we need to account for that in detectors (and
#  in formats)
class GeoPackageHydrofabricDomainDetector(ItemDataDomainDetector, format_type=DataFormat.NGEN_GEOPACKAGE_HYDROFABRIC_V2):

    def _is_region_string_for_conus(self, region_str: Optional[str]) -> bool:
        """
        Whether this is a region string signifies CONUS.

        Parameters
        ----------
        region_str: Optional[str]
            A region string, or ``None``.

        Returns
        -------
        bool
            Whether there was a region string provided that indicates CONUS.
        """
        if not isinstance(region_str, str):
            return False
        else:
            return region_str.strip().lower() == 'conus'

    def detect(self, **kwargs) -> DataDomain:
        """
        Detect and return the data domain.

        Parameters
        ----------
        kwargs
            Optional kwargs applicable to the subtype, which may enhance or add to the domain detection and generation
            capabilities, but which should not be required to produce a valid domain.

        Keyword Args
        ------------
        version: str
            A version string for a constraint using the ``HYDROFABRIC_VERSION`` index.
        region: str
            A region string for a constraint using the ``HYDROFABRIC_REGION`` index; if provided, it will be converted
            to lower case and have any non-alphanumeric characters removed before use.

        Returns
        -------
        DataDomain
            The detected domain.

        Raises
        ------
        DmodRuntimeError
            If it was not possible to properly detect the domain.
        """
        # TODO: (later) probably isn't necessary to treat separately, but don't have a good way to test yet
        if isinstance(self._item, RepeatableReader):
            gpkg_data = self._item.read()
            self._item.reset()
        else:
            gpkg_data = self._item

        if isinstance(kwargs.get('region'), str):
            raw_str = kwargs['region'].strip().lower()
            if raw_str == 'conus':
                vpu = None
                conus = True
            else:
                conus = False
                pattern = re.compile('(vpu)([-_]?)(\d+)')
                matches = pattern.match(raw_str)
                vpu = int(matches.groups()[-1]) if matches else None
        else:
            vpu = None
            conus = False

        try:
            hydrofabric = GeoPackageHydrofabric.from_file(geopackage_file=gpkg_data, vpu=vpu, is_conus=conus)
            d_restricts = [
                # Define range of catchment ids for catchment ids
                DiscreteRestriction(variable=StandardDatasetIndex.CATCHMENT_ID,
                                    values=list(hydrofabric.get_all_catchment_ids())),
                # Define hydrofabric id restriction for domain
                DiscreteRestriction(variable=StandardDatasetIndex.HYDROFABRIC_ID, values=[hydrofabric.uid])]
            # If included, also append region restriction
            # TODO: (later) implement this part later
            # TODO: (later) consider whether conus should literally also include all the individual VPUs, plus "CONUS"
            if hydrofabric.is_conus:
                d_restricts.append(DiscreteRestriction(variable=StandardDatasetIndex.HYDROFABRIC_REGION,
                                                       values=["CONUS"]))
            elif vpu is not None:
                d_restricts.append(DiscreteRestriction(variable=StandardDatasetIndex.HYDROFABRIC_REGION,
                                                       values=[f"VPU{vpu:02d}"]))
            if 'version' in kwargs:
                d_restricts.append(DiscreteRestriction(variable=StandardDatasetIndex.HYDROFABRIC_VERSION,
                                                       values=[kwargs['version']]))

            return DataDomain(data_format=DataFormat.NGEN_GEOPACKAGE_HYDROFABRIC_V2, discrete_restrictions=d_restricts)
        except Exception as e:
            raise DmodRuntimeError(f"{self.__class__.__name__} encountered {e.__class__.__name__} attempting to detect "
                                   f"domain for data item: {e!s}")


if __NGEN_CONFIG_INSTALLED:
    import json

    class RealizationConfigDomainDetector(ItemDataDomainDetector, format_type=DataFormat.NGEN_REALIZATION_CONFIG):
        def detect(self, **kwargs) -> DataDomain:
            try:
                real_obj = ngen.config.realization.NgenRealization(**json.load(self._item))
            except Exception as e:
                raise DmodRuntimeError(f"{self.__class__.__name__} failed detect due to {e.__class__.__name__}: {e!s}")

            # When there is a global config, make catchment restriction values empty list to indicate "all"
            has_global_config = real_obj.global_config is not None and real_obj.global_config.formulations
            cat_restrict = DiscreteRestriction(variable=StandardDatasetIndex.CATCHMENT_ID,
                                               values=[] if has_global_config else sorted(real_obj.catchments.keys()))
            time_range = TimeRange(begin=real_obj.time.start_time, end=real_obj.time.end_time)
            # An individual file won't have a data id (i.e., data_id only applies to a Dataset or collection)
            return DataDomain(data_format=self.get_data_format(), continuous_restrictions=[time_range],
                              discrete_restrictions=[cat_restrict])
