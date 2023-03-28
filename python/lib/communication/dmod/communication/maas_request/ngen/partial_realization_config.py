from ngen.config.configurations import Routing
from ngen.config.formulation import Formulation
from ngen.config.realization import CatchmentRealization
from pydantic import BaseModel, validator
from typing import ClassVar, Dict, List, Optional


class PartialRealizationConfig(BaseModel):
    """
    Helper class for working with the serialized formulation configurations ::class:`AbstractNgenRequest` messages.

    The type relies on classes from the ``ngen-config`` external package and the transitive ``pydantic`` dependency.
    """

    _FROM_ENV_DELIMIT: ClassVar[str] = ':::'
    _FROM_ENV_PREFIX: ClassVar[str] = 'from_env'

    hydrofabric_uid: str
    """ The unique id of hydrofabric associated with the catchments to which the contained formulations apply. """

    global_formulations: Optional[List[Formulation]] = None
    """ The global formulation(s) config, serving as a default once in a full NextGen realization configuration. """

    catchment_formulations: Optional[Dict[str, CatchmentRealization]] = None
    """ The individual catchment formulation configs, if set, keyed by catchment id. """

    forcing_file_pattern: Optional[str] = None
    """ Optional catchment-id-based pattern string for basename of per-catchment forcing files. """

    forcing_file_name: Optional[str] = None
    """ Optional fixed name for the forcing data file. """

    routing_config: Optional[Routing] = None
    """ Optional routing config object for the partial config. """

    is_env_workaround: bool = None
    """ If this partial config indicated use of the env-supplied local mount workaround for the forcing data. """

    @validator('is_env_workaround', pre=True, always=True)
    def default_is_env_workaround(cls, v, values):
        if v is not None:
            return v

        def has_indicator(field_name: str):
            return field_name in values and values[field_name].split(cls._FROM_ENV_DELIMIT)[0] == cls._FROM_ENV_PREFIX

        return has_indicator('forcing_file_pattern') or has_indicator('forcing_file_name')

    @validator('catchment_formulations', pre=True, always=True)
    def validate_formulations(cls, v, values):
        # If a non-empty dict was passed for catchment_formulations, then we are good (so return it)
        if v:
            return v
        # Alternatively, if we received a non-empty global_formulations, then we are also good (so return the value)
        elif 'global_formulations' in values and values['global_formulations']:
            return v
        # But if we got neither a global formulation or individual catchment formulations, that is a problem
        else:
            raise ValueError('Catchment formulations must be provided if no global formulation is present')