from pydantic import PrivateAttr

from typing import ClassVar, List, Optional, Set, Type, Union

# TODO: #pydantic_refactor - clean up any imports that are not still needed once this is finished
from dmod.core.meta_data import (
    DataCategory,
    DataDomain,
    DataFormat,
    DataRequirement,
    DiscreteRestriction,
    TimeRange,
)
from ...message import AbstractInitRequest, MessageEventType
from .abstract_nextgen_request import ExternalAbstractNgenRequest
from ..model_exec_request import ModelExecRequest
from ..model_exec_request_response import ModelExecRequestResponse
from .ngen_exec_request_body import NGENRequestBody


# TODO: #pydantic_refactor - make sure this works with Pydantic and changes to class hierarchy
class NGENRequest(ModelExecRequest, ExternalAbstractNgenRequest):

    event_type = MessageEventType.MODEL_EXEC_REQUEST
    """(:class:`MessageEventType`) The type of event for this message"""

    model_name = "ngen"  # FIXME case sentitivity
    """(:class:`str`) The name of the model to be used"""

    # TODO: #pydantic_refactor - examine after fixing for class hierarchy if this is still the best way to do things, or if serialized structure should be changed

    model: NGENRequestBody

    _hydrofabric_data_requirement = PrivateAttr(None)
    _forcing_data_requirement = PrivateAttr(None)
    _realization_cfg_data_requirement = PrivateAttr(None)
    _bmi_cfg_data_requirement = PrivateAttr(None)
    _partition_cfg_data_requirement = PrivateAttr(None)

    @classmethod
    def factory_init_correct_response_subtype(
        cls, json_obj: dict
    ) -> ModelExecRequestResponse:
        """
        Init a :obj:`Response` instance of the appropriate subtype for this class from the provided JSON object.

        Parameters
        ----------
        json_obj

        Returns
        -------

        """
        return NGENRequestResponse.factory_init_from_deserialized_json(
            json_obj=json_obj
        )

    def __eq__(self, other: "NGENRequest"):
        try:
            return (
                self.time_range == other.time_range
                and self.hydrofabric_data_id == other.hydrofabric_data_id
                and self.hydrofabric_uid == other.hydrofabric_uid
                and self.config_data_id == other.config_data_id
                and self.bmi_config_data_id == other.bmi_config_data_id
                and self.session_secret == other.session_secret
                and self.cpu_count == other.cpu_count
                and self.partition_cfg_data_id == other.partition_cfg_data_id
                and self.catchments == other.catchments
            )
        except AttributeError:
            return False

    def __hash__(self) -> int:
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

    # TODO: #pydantic_refactor - make sure this works with Pydantic and changes to class hierarchy
    def __init__(
        self,
        # required in prior version of code
        time_range: TimeRange = None,
        hydrofabric_uid: str = None,
        hydrofabric_data_id: str = None,
        bmi_cfg_data_id: str = None,
        # optional in prior version of code
        catchments: Optional[Union[Set[str], List[str]]] = None,
        partition_cfg_data_id: Optional[str] = None,
        **data
    ):
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
        # If `model` key is present, assume there is not a need for backwards compatibility
        if "model" in data:
            super().__init__(**data)
            return

        # NOTE: backwards compatibility support.
        model = NGENRequestBody(
            time_range=time_range,
            hydrofabric_uid=hydrofabric_uid,
            hydrofabric_data_id=hydrofabric_data_id,
            catchments=catchments,
            partition_cfg_data_id=partition_cfg_data_id,
            # previous version of code used `bmi_cfg_data_id` as parameter name.
            bmi_config_data_id=bmi_cfg_data_id,
            **data
        )

        super().__init__(model=model, **data)

    def _gen_catchments_domain_restriction(
        self, var_name: str = "catchment_id"
    ) -> DiscreteRestriction:
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
        return [
            self.bmi_cfg_data_requirement,
            self.forcing_data_requirement,
            self.hydrofabric_data_requirement,
            self.partition_cfg_data_requirement,
            self.realization_cfg_data_requirement,
        ]

    @property
    def bmi_config_data_id(self) -> str:
        """
        The index value of ``data_id`` to uniquely identify sets of BMI module config data that are otherwise similar.

        Returns
        -------
        str
            Index value of ``data_id`` to uniquely identify sets of BMI module config data that are otherwise similar.
        """
        return self.model.bmi_config_data_id

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
                    variable="data_id", values=[self._bmi_config_data_id]
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
        return self.model.catchments

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
                continuous_restrictions=[self.model.time_range],
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
                    variable="hydrofabric_id", values=[self.model.hydrofabric_uid]
                ),
                DiscreteRestriction(
                    variable="data_id", values=[self.model.hydrofabric_data_id]
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
        return self.model.hydrofabric_data_id

    @property
    def hydrofabric_uid(self) -> str:
        """
        The unique id of the hydrofabric for this modeling request.

        Returns
        -------
        str
            The unique id of the hydrofabric for this modeling request.
        """
        return self.model.hydrofabric_uid

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
        return self.model.partition_cfg_data_id

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
        return self.model.time_range


class NGENRequestResponse(ModelExecRequestResponse):
    """
    A response to a :class:`NGENRequest`.

    Note that, when not ``None``, the :attr:`data` value will be a dictionary with the following format:
        - key 'job_id' : the appropriate job id value in response to the request
        - key 'scheduler_response' : the related :class:`SchedulerRequestResponse`, in serialized dictionary form

    For example:
    {
        'job_id': 1,
        'output_data_id': '00000000-0000-0000-0000-000000000000',
        'scheduler_response': {
            'success': True,
            'reason': 'Testing Stub',
            'message': 'Testing stub',
            'data': {
                'job_id': 1
            }
        }
    }

    Or:
    {
        'job_id': 0,
        'output_data_id': '00000000-0000-0000-0000-000000000000',
        'scheduler_response': {
            'success': False,
            'reason': 'Testing Stub',
            'message': 'Testing stub',
            'data': {}
        }
    }
    """

    response_to_type: ClassVar[Type[AbstractInitRequest]] = NGENRequest
