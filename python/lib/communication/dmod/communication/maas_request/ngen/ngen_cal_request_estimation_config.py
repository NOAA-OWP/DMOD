from pydantic import Field, validator
from typing import Any, Dict, List, Optional
from .ngen_exec_request_body import NGENRequestBody


# TODO: (later) consider adding different type for when receiving data_id of existing ngen_cal config dataset

class NgenCalRequestEstimationConfig(NGENRequestBody):
    """
    Request body encapsulating data within outer calibration request.

    Encapsulated data to define a requested ngen-cal calibration job.  It includes details on the time range,
    hydrofabric, ngen configurations, and calibration configurations need for performing an ngen-cal calibration. It may
    also include a reference to what forcing data to use.

    An instance contains a reference to the ::class:`DataFormat.NGEN_JOB_COMPOSITE_CONFIG` dataset containing
    configurations for the requested job.  In cases when this dataset doesn't yet exist, an instance also contains the
    necessary details for generating such a dataset.  In particular, this includes:

        - a realization config dataset id **OR** a ::class:`PartialRealizationConfig`
        - a calibration config dataset **OR** calibration config parameters directly
        - (optionally) a BMI init config dataset id
        - a t-route configuration dataset id

    When dataset ids are given, these are treated as sources for the new ::class:`DataFormat.NGEN_JOB_COMPOSITE_CONFIG`,
    with the contents of the former copied into the latter as appropriate.
    """

    ngen_cal_config_data_id: Optional[str] = Field(None, description="Id of existing source ngen_cal config dataset.")
    parallel_proc: int = Field(1, gt=0, description="Number of parallel ngen processes for ngen-cal to use.")
    # TODO: #needs_issue - Add validator for supported values
    algorithm: str = Field("dds", description="The calibration optimization algorithm.")
    objective_function: str = Field(None, description="The calibration objective function.")
    iterations: int = Field(None, gt=0, description="The number of ngen iterations to run through during calibration.")
    # TODO: #needs_issue - Add validator to ensure this isn't larger than the total number of iterations
    start_iteration: int = Field(1, gt=0, description="The starting iteration, which is greater than 1 for restarts.")
    # TODO: #needs_issue - Add validator for supported values (independent, uniform, explicit)
    # TODO: #needs_issue - Add validator for adjusting case when needed
    model_strategy: str = Field(None, description="The particular ngen calibration strategy to use.")
    model_params: Dict[str, List[Dict[str, Any]]] = None

    @validator("ngen_cal_config_data_id", pre=True)
    def _validate_ngen_cal_config_data_id(cls, value, field):
        """
        Validate that, if ``ngen_cal_config_data_id`` is provided and not ``None``, it is a non-empty string.

        Parameters
        ----------
        value
        field

        Returns
        -------
        Optional[str]
            The value, if valid.
        """
        if value is not None and len(value.strip()) == 0:
            raise ValueError(f"{field.name} must either be None or non-empty string")
        return value

    @validator("objective_function", "iterations", "model_strategy", pre=True, always=True)
    def _validate_objective_function(cls, value, values, field):
        """
        Validate that ``objective_function`` is set correctly unless ``ngen_cal_config_data_id`` is provided.

        Parameters
        ----------
        value
        field

        Returns
        -------
        Optional[str]
            The value, if valid.
        """
        if values.get("ngen_cal_config_data_id") is None and value is None:
            raise ValueError(f"{field.name} must be set unless ngen_cal config dataset id is provided.")
        return value

    @property
    def composite_config_source_ids(self) -> List[str]:
        """
        A list of the data ids for any datasets that are sources of data for a generated composite config dataset.

        An instance may know dataset ids of existing datasets from which a new composite config dataset should be
        derived.  For the type, this potentially includes datasets for a realization config, BMI init configs, and
        t-route configs.  For this subtype, that is extended further to also include ngen-cal config datasets.

        Any such datasets are referenced in certain attributes for the instance; e.g., ::attribute:`bmi_config_data_id`.
        This property encapsulates collecting the applicable attribute values while filtering out any that are not set.

        Note that an empty list does not (by itself) imply the composite config dataset is expected to exist, as it is
        possible for the dataset to be created from a ::class:`PartialRealizationConfig`, auto-generated BMI init
        configs, and the instance's explicit calibration configuration attributes.

        Returns
        -------
        List[str]
            List of the data ids for any datasets that are sources of data for a generated composite config dataset.
        """
        result = super().composite_config_source_ids

        if self.ngen_cal_config_data_id is not None:
            result.append(self.ngen_cal_config_data_id)

        return result
