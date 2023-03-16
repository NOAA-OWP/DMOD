from abc import ABC, abstractmethod
from numbers import Number
from typing import Dict, List, Optional, Set, Union

from dmod.core.meta_data import (
    DataCategory,
    DataDomain,
    DataFormat,
    DataRequirement,
    DiscreteRestriction,
    TimeRange,
)

from ..dmod_job_request import DmodJobRequest
from ..model_exec_request import ExternalRequest


class AbstractNextGenRequest(DmodJobRequest, ABC):
    """
    Abstract extension of ::class:`DmodJobRequest` for requesting some kind of NextGen-specific job.

    A representation of request for a job involving NextGen.  As such it contains attributes/properties inherent to
    using the NextGen framework within DMOD:

        - execution time range
        - hydrofabric UID, dataset id, and ::class:`DataRequirement`
        - primary config dataset id (i.e., the realization config) and ::class:`DataRequirement`
        - BMI init configs dataset id and ::class:`DataRequirement`
        - forcing ::class:`DataRequirement`
        - list of each output dataset's ::class:`DataFormat`
        - (Optional) partitioning config dataset id and ::class:`DataRequirement`
        - (Optional) list of catchments

    This type provides the implementation for ::method:`factory_init_from_deserialized_json` for all subtypes.  This
    works by having each level of the class hierarchy be responsible for deserialization applicable to it, as described
    below.

    Instead of implementing full deserialization, this type and subtypes include a function to deserialize from JSON the
    type-specific keyword parameters passed to the individual type's ::method:`__init__`.  This is the
    ::method:`deserialize_for_init` class method.  Subclass implementations should ensure they call superclass's version
    and build on the returned dict of deserialized keyword params from ancestor levels.

    This abstract type also implements a version of ::method:`to_dict` for serializing all the state included at this
    level.
    """

    @classmethod
    def deserialize_for_init(cls, json_obj: dict) -> dict:
        """
        Deserialize a JSON representation to the keyword args needed for use with this type's ::method:`__init__`.

        Parameters
        ----------
        json_obj: dict
            A serialized JSON representation of an instance.

        Returns
        -------
        dict
            A dictionary containing the keyword args (both required and any contained optional) necessary for
            initializing an instance, with the values deserialized from the received JSON.
        """
        deserialized_kwargs = dict()
        deserialized_kwargs["time_range"] = TimeRange.factory_init_from_deserialized_json(json_obj["time_range"])
        deserialized_kwargs["hydrofabric_uid"] = json_obj["hydrofabric_uid"]
        deserialized_kwargs["hydrofabric_data_id"] = json_obj["hydrofabric_data_id"]
        deserialized_kwargs["config_data_id"] = json_obj["config_data_id"]
        deserialized_kwargs["bmi_cfg_data_id"] = json_obj["bmi_config_data_id"]

        if "cpu_count" in json_obj:
            deserialized_kwargs["cpu_count"] = json_obj["cpu_count"]
        if "allocation_paradigm" in json_obj:
            deserialized_kwargs["allocation_paradigm"] = json_obj["allocation_paradigm"]
        if "catchments" in json_obj:
            deserialized_kwargs["catchments"] = json_obj["catchments"]
        if "partition_config_data_id" in json_obj:
            deserialized_kwargs["partition_config_data_id"] = json_obj["partition_config_data_id"]

        return deserialized_kwargs

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> Optional["AbstractNextGenRequest"]:
        """
        Deserialize request formated as JSON to an instance.

        See the documentation of this type's ::method:`to_dict` for an example of the format of valid JSON.

        Parameters
        ----------
        json_obj : dict
            The serialized JSON representation of a request object.

        Returns
        -------
        The deserialized ::class:`NGENRequest`, or ``None`` if the JSON was not valid for deserialization.

        See Also
        -------
        ::method:`to_dict`
        """
        try:
            keyword_args = cls.deserialize_for_init(json_obj)
            return cls(**keyword_args)
        except Exception as e:
            return None

    def __eq__(self, other):
        return (
                self.time_range == other.time_range
                and self.hydrofabric_data_id == other.hydrofabric_data_id
                and self.hydrofabric_uid == other.hydrofabric_uid
                and self.config_data_id == other.config_data_id
                and self.bmi_config_data_id == other.bmi_config_data_id
                and self.cpu_count == other.cpu_count
                and self.partition_cfg_data_id == other.partition_cfg_data_id
                and self.catchments == other.catchments
        )

    def __hash__(self):
        hash_str = "{}-{}-{}-{}-{}-{}-{}-{}".format(
            self.time_range.to_json(),
            self.hydrofabric_data_id,
            self.hydrofabric_uid,
            self.config_data_id,
            self.bmi_config_data_id,
            self.cpu_count,
            self.partition_cfg_data_id,
            ",".join(self.catchments),
        )
        return hash(hash_str)

    def __init__(self,
                 time_range: TimeRange,
                 hydrofabric_uid: str,
                 hydrofabric_data_id: str,
                 bmi_cfg_data_id: str,
                 catchments: Optional[Union[Set[str], List[str]]] = None,
                 partition_cfg_data_id: Optional[str] = None,
                 *args,
                 **kwargs):
        """
        Initialize an instance.

        Parameters
        ----------
        time_range : TimeRange
            A definition of the time range for the requested model execution.
        hydrofabric_uid : str
            The unique ID of the applicable hydrofabric for modeling, which provides the outermost geospatial domain.
        hydrofabric_data_id : str
            A data identifier for the hydrofabric, for distinguishing between different hydrofabrics that cover the same
            set of catchments and nexuses (i.e., the same sets of catchment and nexus ids).
        catchments : Optional[Union[Set[str], List[str]]]
            An optional collection of the catchment ids to narrow the geospatial domain, where the default of ``None``
            or an empty collection implies all catchments in the hydrofabric.
        bmi_cfg_data_id : Optional[str]
            The optioanl BMI init config ``data_id`` index, for identifying the particular BMI init config datasets
            applicable to this request.

        Keyword Args
        -----------
        config_data_id : str
            The config data id index, for identifying the particular configuration datasets applicable to this request.
        session_secret : str
            The session secret for the right session when communicating with the MaaS request handler
        """
        super(AbstractNextGenRequest, self).__init__(*args, **kwargs)
        self._time_range = time_range
        self._hydrofabric_uid = hydrofabric_uid
        self._hydrofabric_data_id = hydrofabric_data_id
        self._bmi_config_data_id = bmi_cfg_data_id
        self._part_config_data_id = partition_cfg_data_id
        # Convert an initial list to a set to remove duplicates
        try:
            catchments = set(catchments)
        # TypeError should mean that we received `None`, so just use that to set _catchments
        except TypeError:
            self._catchments = catchments
        # Assuming we have a set now, move this set back to list and sort
        else:
            self._catchments = list(catchments)
            self._catchments.sort()

        self._hydrofabric_data_requirement = None
        self._forcing_data_requirement = None
        self._realization_cfg_data_requirement = None
        self._bmi_cfg_data_requirement = None
        self._partition_cfg_data_requirement = None

    def _gen_catchments_domain_restriction(self, var_name: str = "catchment_id") -> DiscreteRestriction:
        """
        Generate a ::class:`DiscreteRestriction` that will restrict to the catchments applicable to this request.

        Note that if the ::attribute:`catchments` property is ``None`` or empty, then the generated restriction object
        will reflect that with an empty list of values, implying "all catchments in hydrofabric."  This is slightly
        different than the internal behavior of ::class:`DiscreteRestriction` itself, which only infers this for empty
        lists (i.e., not a ``values`` value of ``None``).  This is intentional here, as the natural implication of
        specific catchments not being provided as part of a job request is to include all of them.

        Parameters
        ----------
        var_name : str
            The value of the ::attribute:`DiscreteRestriction.variable` for the restriction; defaults to `catchment-id`.

        Returns
        -------
        DiscreteRestriction
            ::class:`DiscreteRestriction` that will restrict to the catchments applicable to this request.
        """
        return DiscreteRestriction(
            variable=var_name,
            values=([] if self.catchments is None else self.catchments),
        )

    @property
    def data_requirements(self) -> List[DataRequirement]:
        """
        List of all the explicit and implied data requirements for this request, as needed for creating a job object.

        Returns
        -------
        List[DataRequirement]
            List of all the explicit and implied data requirements for this request.
        """
        requirements = [
            self.bmi_cfg_data_requirement,
            self.forcing_data_requirement,
            self.hydrofabric_data_requirement,
            self.realization_cfg_data_requirement,
        ]
        if self.use_parallel_ngen:
            requirements.append(self.partition_cfg_data_requirement)
        return requirements

    @property
    def bmi_config_data_id(self) -> str:
        """
        The index value of ``data_id`` to uniquely identify sets of BMI module config data that are otherwise similar.

        Returns
        -------
        str
            Index value of ``data_id`` to uniquely identify sets of BMI module config data that are otherwise similar.
        """
        return self._bmi_config_data_id

    @property
    def bmi_cfg_data_requirement(self) -> DataRequirement:
        """
        A requirement object defining of the BMI configuration data needed to execute this request.

        Returns
        -------
        DataRequirement
            A requirement object defining of the BMI configuration data needed to execute this request.
        """
        if self._bmi_cfg_data_requirement is None:
            bmi_config_restrict = [
                DiscreteRestriction(
                    variable="data_id", values=[self.bmi_config_data_id]
                )
            ]
            bmi_config_domain = DataDomain(
                data_format=DataFormat.BMI_CONFIG,
                discrete_restrictions=bmi_config_restrict,
            )
            self._bmi_cfg_data_requirement = DataRequirement(
                bmi_config_domain, True, DataCategory.CONFIG
            )
        return self._bmi_cfg_data_requirement

    @property
    def catchments(self) -> Optional[List[str]]:
        """
        An optional list of catchment ids for those catchments in the request ngen execution.

        No list implies "all" known catchments.

        Returns
        -------
        Optional[List[str]]
            An optional list of catchment ids for those catchments in the request ngen execution.
        """
        return self._catchments

    @property
    def forcing_data_requirement(self) -> DataRequirement:
        """
        A requirement object defining of the forcing data needed to execute this request.

        Returns
        -------
        DataRequirement
            A requirement object defining of the forcing data needed to execute this request.
        """
        if self._forcing_data_requirement is None:
            # TODO: going to need to address the CSV usage later
            forcing_domain = DataDomain(
                data_format=DataFormat.AORC_CSV,
                continuous_restrictions=[self._time_range],
                discrete_restrictions=[self._gen_catchments_domain_restriction()],
            )
            self._forcing_data_requirement = DataRequirement(
                domain=forcing_domain, is_input=True, category=DataCategory.FORCING
            )
        return self._forcing_data_requirement

    @property
    def hydrofabric_data_requirement(self) -> DataRequirement:
        """
        A requirement object defining the hydrofabric data needed to execute this request.

        Returns
        -------
        DataRequirement
            A requirement object defining the hydrofabric data needed to execute this request.
        """
        if self._hydrofabric_data_requirement is None:
            hydro_restrictions = [
                DiscreteRestriction(
                    variable="hydrofabric_id", values=[self._hydrofabric_uid]
                ),
                DiscreteRestriction(
                    variable="data_id", values=[self._hydrofabric_data_id]
                ),
            ]
            hydro_domain = DataDomain(
                data_format=DataFormat.NGEN_GEOJSON_HYDROFABRIC,
                discrete_restrictions=hydro_restrictions,
            )
            self._hydrofabric_data_requirement = DataRequirement(
                domain=hydro_domain, is_input=True, category=DataCategory.HYDROFABRIC
            )
        return self._hydrofabric_data_requirement

    @property
    def hydrofabric_data_id(self) -> str:
        """
        The data format ``data_id`` for the hydrofabric dataset to use in requested modeling.

        This identifier is needed to distinguish the correct hydrofabric dataset, and thus the correct hydrofabric,
        expected for this modeling request.  For arbitrary hydrofabric types, this may not be possible with the unique
        id of the hydrofabric alone.  E.g., a slight adjustment of catchment coordinates may be ignored with respect
        to the hydrofabric's uid, but may be relevant with respect to a model request.

        Returns
        -------
        str
            The data format ``data_id`` for the hydrofabric dataset to use in requested modeling.
        """
        return self._hydrofabric_data_id

    @property
    def hydrofabric_uid(self) -> str:
        """
        The unique id of the hydrofabric for this modeling request.

        Returns
        -------
        str
            The unique id of the hydrofabric for this modeling request.
        """
        return self._hydrofabric_uid

    @property
    def output_formats(self) -> List[DataFormat]:
        """
        List of the formats of each required output dataset for the requested job.

        Returns
        -------
        List[DataFormat]
            List of the formats of each required output dataset for the requested job.
        """
        return [DataFormat.NGEN_OUTPUT]

    @property
    def partition_cfg_data_id(self) -> Optional[str]:
        """
        The ``data_id`` for the partition config dataset to use in requested modeling.

        This identifier is needed to distinguish the correct specific partition config dataset, and thus the correct
        partition config, expected for this modeling request.  However, this may not always be necessary, as it should
        be possible to find a compatible partitioning config dataset of the right hydrofabric and size, so long as one
        exists.

        Returns
        -------
        Optional[str]
            The data format ``data_id`` for the partition config dataset to use in requested modeling, or ``None``.
        """
        return self._part_config_data_id

    @property
    def partition_cfg_data_requirement(self) -> DataRequirement:
        """
        A requirement object defining of the partitioning configuration data needed to execute this request.

        Returns
        -------
        DataRequirement
            A requirement object defining of the partitioning configuration data needed to execute this request.
        """
        if self._partition_cfg_data_requirement is None:
            d_restricts = []

            # Add restriction on hydrofabric
            d_restricts.append(
                DiscreteRestriction(
                    variable="hydrofabric_id", values=[self.hydrofabric_uid]
                )
            )

            # Add restriction on partition count, which will be based on the number of request CPUs
            d_restricts.append(
                DiscreteRestriction(variable="length", values=[self.cpu_count])
            )

            # If present, add restriction on data_id
            if self.partition_cfg_data_id is not None:
                d_restricts.append(
                    DiscreteRestriction(
                        variable="data_id", values=[self.partition_cfg_data_id]
                    )
                )
            part_domain = DataDomain(
                data_format=DataFormat.NGEN_PARTITION_CONFIG,
                discrete_restrictions=d_restricts,
            )
            self._partition_cfg_data_requirement = DataRequirement(
                domain=part_domain, is_input=True, category=DataCategory.CONFIG
            )
        return self._partition_cfg_data_requirement

    @property
    def realization_config_data_id(self) -> str:
        """
        The index value of ``data_id`` to uniquely identify sets of realization config data that are otherwise similar.

        For example, two realization configs may apply to the same time and catchments, but be very different.  The
        nature of the differences is not necessarily even possible to define generally, and certainly not through
        (pre-existing) indices.  As such, the `data_id` index is added for such differentiating purposes.

        Returns
        -------
        str
            The index value of ``data_id`` to uniquely identify the required realization config dataset.
        """
        return self.config_data_id

    @property
    def realization_cfg_data_requirement(self) -> DataRequirement:
        """
        A requirement object defining of the realization configuration data needed to execute this request.

        Returns
        -------
        DataRequirement
            A requirement object defining of the realization configuration data needed to execute this request.
        """
        if self._realization_cfg_data_requirement is None:
            real_cfg_dis_restrict = [
                self._gen_catchments_domain_restriction(),
                DiscreteRestriction(
                    variable="data_id", values=[self.realization_config_data_id]
                ),
            ]
            real_cfg_domain = DataDomain(
                data_format=DataFormat.NGEN_REALIZATION_CONFIG,
                continuous_restrictions=[self.time_range],
                discrete_restrictions=real_cfg_dis_restrict,
            )
            self._realization_cfg_data_requirement = DataRequirement(
                domain=real_cfg_domain, is_input=True, category=DataCategory.CONFIG
            )
        return self._realization_cfg_data_requirement

    @property
    def time_range(self) -> TimeRange:
        """
        The time range for the requested model execution.

        Returns
        -------
        TimeRange
            The time range for the requested model execution.
        """
        return self._time_range

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        """
        Converts the request to a dictionary that may be passed to web requests.

        Will look like:

        {
            'allocation_paradigm': <allocation_paradigm_str>,
            'cpu_count': <cpu_count>,
            'time_range': { <serialized_time_range_object> },
            'hydrofabric_data_id': 'hy-data-id-val',
            'hydrofabric_uid': 'hy-uid-val',
            'config_data_id': 'config-data-id-val',
            'bmi_config_data_id': 'bmi-config-data-id',
            'partition_config_data_id': 'partition_config_data_id',
            ['catchments': { <serialized_catchment_discrete_restriction_object> },]
        }

        As a reminder, the ``catchments`` item may be absent, which implies the object does not have a specified list of
        catchment ids.

        Returns
        -------
        Dict[str, Union[str, Number, dict, list]]
            A dictionary containing all the data in such a way that it may be used by a web request
        """
        serial = dict()
        serial["allocation_paradigm"] = self.allocation_paradigm.name
        serial["cpu_count"] = self.cpu_count
        serial["time_range"] = self.time_range.to_dict()
        serial["hydrofabric_data_id"] = self.hydrofabric_data_id
        serial["hydrofabric_uid"] = self.hydrofabric_uid
        serial["config_data_id"] = self.config_data_id
        serial["bmi_config_data_id"] = self._bmi_config_data_id
        if self.catchments is not None:
            serial["catchments"] = self.catchments
        if self.partition_cfg_data_id is not None:
            serial["partition_config_data_id"] = self.partition_cfg_data_id
        return serial

    @property
    def use_parallel_ngen(self) -> bool:
        """
        Whether this request specifies to use the variant of the Nextgen framework compiled for parallel execution.

        Nextgen may be compiled to execute either serially or using parallelization.  DMOD and its Nextgen job workers
        can now support either.  This property indicates whether this request indicates that parallel execution should
        be used.

        In the default implementation, this property is ``True`` IFF ::method:`use_serial_ngen` is ``False``.

        Returns
        -------
        bool
            Whether this request specifies parallel Nextgen execution for the job.

        See Also
        -------
        use_serial_ngen
        """
        return not self.use_serial_ngen

    @property
    @abstractmethod
    def use_serial_ngen(self) -> bool:
        """
        Whether this request specifies to use the variant of the Nextgen framework compiled for serial execution.

        Nextgen may be compiled to execute either serially or using parallelization.  DMOD and its Nextgen job workers
        can now support either.  This property indicates whether this request indicates that serially execution should
        be used.

        Returns
        -------
        bool
            Whether this request specifies serial Nextgen execution for the job.

        See Also
        -------
        use_parallel_ngen
        """
        pass


class ExternalNextGenRequest(ExternalRequest, AbstractNextGenRequest, ABC):
    """
    Abstract extension of both ::class:`AbstractNextGenRequest` and ::class:`ExternalRequest`.

    An abstract subclass of ::class:`AbstractNextGenRequest` and ::class:`ExternalRequest` that, due to the latter,
    contains a ::attribute:`session_secret` property.  As such, the implementations of several functions from
    ::class:`AbstractNextGenRequest` are extended to properly account for this property (e.g., ::method:`__eq__`).
    """

    @classmethod
    def deserialize_for_init(cls, json_obj: dict) -> dict:
        """
        Deserialize a JSON representation to the keyword args needed for use with this type's ::method:`__init__`.

        Builds on the superclass's implementation by append the ::attribute:`session_secret` property value.

        Parameters
        ----------
        json_obj: dict
            A serialized JSON representation of an instance.

        Returns
        -------
        dict
            A dictionary containing the keyword args (both required and any contained optional) necessary for
            initializing an instance, with the values deserialized from the received JSON.
        """
        deserialized_kwargs = super().deserialize_for_init(json_obj)
        deserialized_kwargs["session_secret"] = json_obj["session_secret"]
        return deserialized_kwargs

    def __eq__(self, other):
        return super().__eq__(other) and self.session_secret == other.session_secret

    def __hash__(self):
        hash_str = "{}-{}-{}-{}-{}-{}-{}-{}-{}".format(
            self.time_range.to_json(),
            self.hydrofabric_data_id,
            self.hydrofabric_uid,
            self.config_data_id,
            self.bmi_config_data_id,
            self.session_secret,
            self.cpu_count,
            self.partition_cfg_data_id,
            ",".join(self.catchments),
        )
        return hash(hash_str)

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        serial = super().to_dict()
        serial["session_secret"] = self.session_secret
        return serial