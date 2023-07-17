from pydantic import Field, validator

from .partial_realization_config import PartialRealizationConfig

from dmod.core.meta_data import TimeRange
from dmod.core.serializable import Serializable

from typing import List, Optional


class NGENRequestBody(Serializable):
    """
    Request body encapsulating data within outer request.

    Encapsulated data to define a requested ngen job.  It includes details on the time range, hydrofabric, and
    configurations need for executing ngen.  It may also include a reference to what forcing data to use.

    An instance contains a reference to the ::class:`DataFormat.NGEN_JOB_COMPOSITE_CONFIG` dataset containing
    configurations for the requested job.  In cases when this dataset doesn't yet exist, an instance also contains the
    necessary details for generating such a dataset.  In particular, this includes:

        - a realization config dataset id **OR** a ::class:`PartialRealizationConfig`
        - (optionally) a BMI init config dataset id
        - (optionally) a t-route configuration dataset id

    When dataset ids are given, these are treated as sources for the new ::class:`DataFormat.NGEN_JOB_COMPOSITE_CONFIG`,
    with the contents of the former copied into the latter as appropriate.
    """

    time_range: TimeRange = Field(description="The time range over which to run ngen simulation(s).")
    hydrofabric_uid: str = Field(description="The (DMOD-generated) unique id of the hydrofabric to use.")
    hydrofabric_data_id: str = Field(description="The dataset id of the hydrofabric dataset to use.")
    composite_config_data_id: str = Field(None, description="Id of required ngen composite config dataset.")
    realization_config_data_id: Optional[str] = Field(None, description="Id of composite source of realization config.")
    forcings_data_id: Optional[str] = Field(None, description="Id of requested forcings dataset.")
    bmi_config_data_id: Optional[str] = Field(None, description="Id of composite source of BMI init configs.")
    # NOTE: consider pydantic.conlist to constrain this type rather than using validators
    catchments: Optional[List[str]] = Field(None, description="Subset of ids of catchments to include in job.")
    partial_realization_config: Optional[PartialRealizationConfig] = Field(
        default=None, description="Partial realization config, when supplied by user.")
    partition_cfg_data_id: Optional[str] = Field(None, description="Partition config dataset, when multi-process job.")
    t_route_config_data_id: Optional[str] = Field(None, description="Id of composite source of t-route config.")

    @validator("catchments")
    def validate_deduplicate_and_sort_catchments(
        cls, value: List[str]
    ) -> Optional[List[str]]:
        if value is None:
            return None

        deduped = set(value)
        return sorted(list(deduped))

    class Config:
        fields = {
            "partition_cfg_data_id": {"alias": "partition_config_data_id"},
        }

    def dict(self, **kwargs) -> dict:
        # if exclude is set, ignore this _get_exclude_fields()
        only_if_set = ("catchments", "partition_cfg_data_id", "forcings_data_id", "partial_realization_config",
                       "t_route_config_data_id")
        if kwargs.get("exclude", False) is False:
            kwargs["exclude"] = {f for f in only_if_set if not self.__getattribute__(f)}
        return super().dict(**kwargs)

    @property
    def composite_config_source_ids(self) -> List[str]:
        """
        A list of the data ids for any datasets that are sources of data for a generated composite config dataset.

        An instance may know dataset ids of existing datasets from which a new composite config dataset should be
        derived.  For the base type, this potentially includes datasets for a realization config, BMI init configs, and
        t-route configs.  Any such datasets are referenced in certain attributes for the instance;
        e.g., ::attribute:`bmi_config_data_id`.  This property encapsulates collecting those applicable attribute values
        while filtering out any that are not set.

        Note that an empty list does not (by itself) imply the composite config dataset is expected to exist, as it is
        possible for the dataset to be created from a ::class:`PartialRealizationConfig` and auto-generated BMI init
        configs.

        Returns
        -------
        List[str]
            List of the data ids for any datasets that are sources of data for a generated composite config dataset.
        """
        result = []
        if self.realization_config_data_id is not None:
            result.append(self.realization_config_data_id)
        if self.bmi_config_data_id is not None:
            result.append(self.bmi_config_data_id)
        if self.t_route_config_data_id is not None:
            result.append(self.t_route_config_data_id)
        return result
