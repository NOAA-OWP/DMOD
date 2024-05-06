import geopandas as gpd
import pandas as pd

from collections import defaultdict
from functools import partial
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Union
from pydantic import BaseModel
from math import degrees as math_degrees, tan as math_tan

from ngen.config.formulation import Formulation
from ngen.config.multi import MultiBMI
from ngen.config.realization import NgenRealization
from ngen.config_gen.file_writer import DefaultFileWriter
from ngen.config_gen.hook_providers import DefaultHookProvider
from ngen.config_gen.models import Pet
from ngen.config_gen.models.cfe import Cfe

from ngen.config.init_config.noahowp import (Forcing, InitialValues, LandSurfaceType, Location, ModelOptions,
                                             NoahOWP as NoahOWPConfig, Structure)
from ngen.config.init_config.noahowp_options import (CanopyStomResistOption, CropModelOption, DrainageOption,
                                                     DynamicVegOption, DynamicVicOption, EvapSrfcResistanceOption,
                                                     FrozenSoilOption, PrecipPhaseOption, RadiativeTransferOption,
                                                     RunoffOption, SfcDragCoeffOption, SnowAlbedoOption,
                                                     SnowsoilTempTimeOption, SoilTempBoundaryOption,
                                                     StomatalResistanceOption, SubsurfaceOption, SupercooledWaterOption)

from dmod.core.exception import DmodRuntimeError


#### Class copied from https://github.com/NOAA-OWP/ngen-cal/blob/a7f2c143166e71df37240f97aeb87464aff1c2cb/python/ngen_config_gen/examples/noaa_owp/noaa_owp.py
class NoahOWPBuilder:
    """
    NWM 2.2.3 analysis assim physics options
    source: https://www.nco.ncep.noaa.gov/pmb/codes/nwprod/nwm.v2.2.3/parm/analysis_assim/namelist.hrldas
    ! Physics options (see the documentation for details)
    | NoahOWP Name                | NoahMP Name                         | NWM 2.2.3 analysis assim physics options |
    |-----------------------------|-------------------------------------|------------------------------------------|
    | dynamic_veg_option          | DYNAMIC_VEG_OPTION                  | 4                                        |
    | canopy_stom_resist_option   | CANOPY_STOMATAL_RESISTANCE_OPTION   | 1                                        |
    | stomatal_resistance_option  | BTR_OPTION                          | 1                                        |
    | runoff_option               | RUNOFF_OPTION                       | 3                                        |
    | sfc_drag_coeff_option       | SURFACE_DRAG_OPTION                 | 1                                        |
    | frozen_soil_option          | FROZEN_SOIL_OPTION                  | 1                                        |
    | supercooled_water_option    | SUPERCOOLED_WATER_OPTION            | 1                                        |
    | radiative_transfer_option   | RADIATIVE_TRANSFER_OPTION           | 3                                        |
    | snow_albedo_option          | SNOW_ALBEDO_OPTION                  | 1                                        |
    | precip_phase_option         | PCP_PARTITION_OPTION                | 1                                        |
    | soil_temp_boundary_option   | TBOT_OPTION                         | 2                                        |
    | snowsoil_temp_time_option   | TEMP_TIME_SCHEME_OPTION             | 3                                        |
    | no glacier option           | GLACIER_OPTION                      | 2                                        |
    | evap_srfc_resistance_option | SURFACE_RESISTANCE_OPTION           | 4                                        |

    NWM 3.0.6 analysis assim physics options
    source: https://www.nco.ncep.noaa.gov/pmb/codes/nwprod/nwm.v3.0.6/parm/analysis_assim/namelist.hrldas
    ! Physics options (see the documentation for details)
    | NoahOWP Name                | NoahMP Name                         | NWM 3.0.6 analysis assim physics options |
    |-----------------------------|-------------------------------------|------------------------------------------|
    | dynamic_veg_option          | DYNAMIC_VEG_OPTION                  | 4                                        |
    | canopy_stom_resist_option   | CANOPY_STOMATAL_RESISTANCE_OPTION   | 1                                        |
    | stomatal_resistance_option  | BTR_OPTION                          | 1                                        |
    | runoff_option               | RUNOFF_OPTION                       | 7                                        |
    | sfc_drag_coeff_option       | SURFACE_DRAG_OPTION                 | 1                                        |
    | frozen_soil_option          | FROZEN_SOIL_OPTION                  | 1                                        |
    | supercooled_water_option    | SUPERCOOLED_WATER_OPTION            | 1                                        |
    | radiative_transfer_option   | RADIATIVE_TRANSFER_OPTION           | 3                                        |
    | snow_albedo_option          | SNOW_ALBEDO_OPTION                  | 1                                        |
    | precip_phase_option         | PCP_PARTITION_OPTION                | 1                                        |
    | soil_temp_boundary_option   | TBOT_OPTION                         | 2                                        |
    | snowsoil_temp_time_option   | TEMP_TIME_SCHEME_OPTION             | 3                                        |
    | no glacier option           | GLACIER_OPTION                      | 2                                        |
    | evap_srfc_resistance_option | SURFACE_RESISTANCE_OPTION           | 4                                        |
    |                             | IMPERV_OPTION                       | 2 (0: none; 1: total; 2: Alley&Veenhuis; |
    |                             |                                     |    9: orig)                              |

    """

    def __init__(self, start_time: str, end_time: str, parameter_dir: Path):
        self.data = defaultdict(dict)
        # NOTE: this might be handled differently in the future
        self.data["parameters"]["parameter_dir"] = parameter_dir

        # NOTE: expects "%Y%m%d%H%M" (e.g. 200012311730)
        self.data["timing"]["startdate"] = start_time
        self.data["timing"]["enddate"] = end_time

        # NOTE: these parameters will likely be removed in the future. They are not used if noah owp
        # is compiled for use with NextGen.
        self.data["timing"]["forcing_filename"] = Path("")
        self.data["timing"]["output_filename"] = Path("")

    def _v2_defaults(self) -> None:
        # ---------------------------------- Timing ---------------------------------- #
        # NOTE: in the future this _should_ be pulled from a forcing metadata hook (if one ever exists)
        self.data["timing"]["dt"] = 3600

        # -------------------------------- Parameters -------------------------------- #
        # NOTE: Wrf-Hydro configured as NWM uses USGS vegitation classes. Thus, so does HF v1.2 and v2.0
        self.data["parameters"]["veg_class_name"] = "USGS"

        # TODO: determine how to handle `parameter_dir`
        # NOTE: theses _could_ be bundled as package data
        # NOTE: could a parameter to the initializer
        # NOTE: moved to __init__ for now
        # self.data["parameters"]["parameter_dir"] =

        # looking through the from wrf-hydro source, it appears that wrf-hydro hard codes `STAS` as the `soil_class_name`
        # see https://sourcegraph.com/search?q=context:global+repo:https://github.com/NCAR/wrf_hydro_nwm_public+STAS&patternType=standard&sm=1&groupBy=repo
        self.data["parameters"]["soil_class_name"] = "STAS"  # | "STAS-RUC"

        # ---------------------------------- Forcing --------------------------------- #
        # measurement height for wind speed [m]
        # NOTE: in the future this _should_ be pulled from a forcing metadata hook (if one ever exists)
        zref = 10.0
        # TODO: not sure if this is a sane default
        # rain-snow temperature threshold
        rain_snow_thresh = 1.0
        self.data["forcing"] = Forcing(zref=zref, rain_snow_thresh=rain_snow_thresh)

        # ------------------------------- Model Options ------------------------------ #
        dynamic_veg_option: DynamicVegOption = (
            DynamicVegOption.off_use_lai_table_use_max_vegetation_fraction
        )
        canopy_stom_resist_option = CanopyStomResistOption.ball_berry
        stomatal_resistance_option = StomatalResistanceOption.noah
        runoff_option = RunoffOption.original_surface_and_subsurface_runoff
        sfc_drag_coeff_option = SfcDragCoeffOption.m_o
        frozen_soil_option = FrozenSoilOption.linear_effects
        supercooled_water_option = SupercooledWaterOption.no_iteration
        radiative_transfer_option = (
            RadiativeTransferOption.two_stream_applied_to_vegetated_fraction
        )
        snow_albedo_option = SnowAlbedoOption.BATS
        precip_phase_option = PrecipPhaseOption.sntherm
        soil_temp_boundary_option = SoilTempBoundaryOption.tbot_at_zbot
        # TODO: needs further verification
        snowsoil_temp_time_option = (
            SnowsoilTempTimeOption.semo_implicit_with_fsno_for_ts
        )
        # no glacier option
        evap_srfc_resistance_option = (
            EvapSrfcResistanceOption.sakaguchi_and_zeng_for_nonsnow_rsurf_eq_rsurf_snow_for_snow
        )
        # non noahmp options
        drainage_option = DrainageOption.dynamic_vic_runoff_with_dynamic_vic_runoff
        dynamic_vic_option = DynamicVicOption.philip
        crop_model_option = CropModelOption.none
        subsurface_option = SubsurfaceOption.noah_mp

        model_options = ModelOptions(
            precip_phase_option=precip_phase_option,
            snow_albedo_option=snow_albedo_option,
            dynamic_veg_option=dynamic_veg_option,
            runoff_option=runoff_option,
            drainage_option=drainage_option,
            frozen_soil_option=frozen_soil_option,
            dynamic_vic_option=dynamic_vic_option,
            radiative_transfer_option=radiative_transfer_option,
            sfc_drag_coeff_option=sfc_drag_coeff_option,
            canopy_stom_resist_option=canopy_stom_resist_option,
            crop_model_option=crop_model_option,
            snowsoil_temp_time_option=snowsoil_temp_time_option,
            soil_temp_boundary_option=soil_temp_boundary_option,
            supercooled_water_option=supercooled_water_option,
            stomatal_resistance_option=stomatal_resistance_option,
            evap_srfc_resistance_option=evap_srfc_resistance_option,
            subsurface_option=subsurface_option,
        )
        self.data["model_options"] = model_options

        # ------------------------------- InitialValues ------------------------------ #

        # snow/soil level thickness [m]
        # all nwm version (including 3.0) have always used soil horizons of 10cm 30cm 60cm and 1m; see last 4 values of dzsnso
        # NOTE: len nsnow + nsoil; thus [nsnow..., nsoil...] in this order
        # https://github.com/NOAA-OWP/noah-owp-modular/blob/30d0f53e8c14acc4ce74018e06ff7c9410ecc13c/src/DomainType.f90#L66
        # if you are looking at the fortran source, this is indexed like:
        # where [-2:0] are snow and [1:4] are soil
        #                     [ -2,  -1,   0,   1    2,   3,   4]
        dzsnso: List[float] = [0.0, 0.0, 0.0, 0.1, 0.3, 0.6, 1.0]

        # initial soil ice profile [m^3/m^3]
        # NOTE: len nsoil
        # https://github.com/NOAA-OWP/noah-owp-modular/blob/30d0f53e8c14acc4ce74018e06ff7c9410ecc13c/src/WaterType.f90#L110
        # NOTE: These values likely make no sense
        sice: List[float] = [0.0, 0.0, 0.0, 0.0]

        # initial soil liquid profile [m^3/m^3]
        # NOTE: len nsoil
        # https://github.com/NOAA-OWP/noah-owp-modular/blob/30d0f53e8c14acc4ce74018e06ff7c9410ecc13c/src/WaterType.f90#L111
        sh2o: List[float] = [0.3, 0.3, 0.3, 0.3]

        # initial water table depth below surface [m]
        # NOTE: not sure if this _should_ ever be derived. my intuition is this is -2 b.c. the total
        # soil horizon height is 2m (see `dzsnoso`)
        zwt: float = -2.0

        initial_values = InitialValues(
            dzsnso=dzsnso,
            sice=sice,
            sh2o=sh2o,
            zwt=zwt,
        )
        self.data["initial_values"] = initial_values

    def hydrofabric_linked_data_hook(
            self, version: str, divide_id: str, data: Dict[str, Any]
    ) -> None:
        # --------------------------------- Location --------------------------------- #
        lon = data["X"]
        lat = data["Y"]

        # TODO: i think the units are wrong m / km need degrees
        # TODO: this needs to be checked
        METERS_IN_KM = 1_000
        slope_m_km = data["slope"]
        slope_m_m = slope_m_km / METERS_IN_KM
        slope_deg = math_degrees(math_tan(slope_m_m))
        terrain_slope = slope_deg

        # TODO: not sure if this is right and where to get this from
        azimuth = data["aspect_c_mean"]
        self.data["location"] = Location(
            lon=lon, lat=lat, terrain_slope=terrain_slope, azimuth=azimuth
        )

        # --------------------------------- Structure -------------------------------- #
        # NOTE: Wrf-Hydro configured as NWM uses STAS soil classes. Thus, so does HF v1.2 and v2.0
        isltyp = data["ISLTYP"]
        # all nwm versions (including 3.0) have used 4 soil horizons
        nsoil = 4
        nsnow = 3
        # NOTE: Wrf-Hydro configured as NWM uses USGS vegetation classes. Thus, so does HF v1.2 and v2.0
        # NOTE: this can be derived from Parameters `veg_class_name` field (USGS=27; MODIS=20)
        nveg = 27
        vegtyp = data["IVGTYP"]
        # crop type (SET TO 0, no crops currently supported)
        # source: https://github.com/NOAA-OWP/noah-owp-modular/blob/30d0f53e8c14acc4ce74018e06ff7c9410ecc13c/src/NamelistRead.f90#L36
        croptype = 0

        # NOTE: 16 = water bodies in USGS vegetation classification (see MPTABLE.TBL)
        USGS_VEG_IS_WATER = 16
        if vegtyp == USGS_VEG_IS_WATER:
            sfctyp = LandSurfaceType.lake
        else:
            sfctyp = LandSurfaceType.soil

        # TODO: not sure where this comes from
        # soil color index for soil albedo
        # https://github.com/NOAA-OWP/noah-owp-modular/blob/30d0f53e8c14acc4ce74018e06ff7c9410ecc13c/docs/changelog.md?plain=1#L35C7-L35C168
        # > SOILCOLOR is hard-coded as 4 in module_sf_noahmpdrv.F in the current release of HRLDAS. SOILCOLOR is used to select the albedo values for dry and saturated soil.
        # NOTE: it appears that the soil color indexes into the ALBSAT_VIS, ALBSAT_NIR, ALBDRY_VIS, ALBDRY_NIR tables
        # https://github.com/NOAA-OWP/noah-owp-modular/blob/30d0f53e8c14acc4ce74018e06ff7c9410ecc13c/parameters/MPTABLE.TBL#L328-L331
        # here is the indexing
        # https://github.com/NOAA-OWP/noah-owp-modular/blob/30d0f53e8c14acc4ce74018e06ff7c9410ecc13c/src/ParametersType.f90#L303-L306
        # NOTE: looks like for HRLDAS this is 4
        soilcolor: int = 4
        structure = Structure(
            isltyp=isltyp,
            nsoil=nsoil,
            nsnow=nsnow,
            nveg=nveg,
            vegtyp=vegtyp,
            # crop type (SET TO 0, no crops currently supported)
            # source: https://github.com/NOAA-OWP/noah-owp-modular/blob/30d0f53e8c14acc4ce74018e06ff7c9410ecc13c/src/NamelistRead.f90#L36
            croptype=croptype,
            sfctyp=sfctyp,
            soilcolor=soilcolor,
        )
        self.data["structure"] = structure

    def visit(self, hook_provider: "HookProvider") -> None:
        hook_provider.provide_hydrofabric_linked_data(self)

        self._v2_defaults()

    def build(self) -> BaseModel:
        return NoahOWPConfig(**self.data)


class BmiGenDivideIdHookObject:
    def __init__(self):
        self.__divide_id: Union[str, None] = None

    def hydrofabric_hook(self, version: str, divide_id: str, data: Dict[str, Any]) -> None:
        self.__divide_id = divide_id

    def visit(self, hook_provider) -> None:
        hook_provider.provide_hydrofabric_data(self)

    def divide_id(self) -> Union[str, None]:
        return self.__divide_id


# TODO: figure out how to handle noah owp
class BmiInitConfigAutoGenerator:
    """
    A tool for automatically generating required BMI initialization configs for a realization config and hydrofabric.

    A helper tool for generating BMI init configs as needed for a given realization config.  It also requires data from
    a hydrofabric dataset, not only because a realization config only has real meaning in the context of a particular
    hydrofabric (i.e., otherwise, what exactly is, for example, ``cat-115`` referring to?), but because the hydrofabric
    dataset contains model attributes data from which an applicable BMI init config can be generated.

    This type strategically applies classes in the ``ngen.config_gen`` package to perform the actual generation of
    configs.

    See https://www.lynker-spatial.com/copyright.html for license details on hydrofabric data.
    """

    _module_to_model_map: Dict[str, Any] = {"CFE": Cfe, "PET": Pet}
    """ Map of config strings to builders, for modules with builders than can be easily init with no more info. """
    _no_init_config_modules = {"SLOTH"}
    """ Config strings for modules that do not need init configs generated. """

    @staticmethod
    def get_module_names(formulation: Formulation) -> Set[str]:
        """
        Get name of all modules in a formulation (e.g. "NoahOWP").
        """
        modules = set()
        if isinstance(formulation.params, MultiBMI):
            for mod in formulation.params.modules:
                if isinstance(mod.params, MultiBMI):
                    modules.update(set(BmiInitConfigAutoGenerator.get_module_names(mod)))
                else:
                    modules.add(mod.params.model_name)
        else:
            return modules.add(formulation.params.model_name)
        return modules

    def __init__(self,
                 ngen_realization: NgenRealization,
                 hydrofabric_data: gpd.GeoDataFrame,
                 hydrofabric_model_attributes: pd.DataFrame,
                 noah_owp_params_dir: Optional[Union[str, Path]] = None,
                 catchment_subset: Optional[Set[str]] = None,
                 other_builder_hook_types: Optional[Dict[str, partial]] = None):
        """
        Initialize.

        Parameters
        ----------
        ngen_realization: NgenRealization
            The realization config model object.
        hydrofabric_data: gpd.GeoDataFrame
            The main hydrofabric data (i.e., the ``divides`` layer), as a dataframe.
        hydrofabric_model_attributes: pd.DataFrame
            The hydrofabric model attributes data, as a dataframe.
        noah_owp_params_dir: Union[str, Path], optional
            The directory containing the params data files for NoahOWP init configs, if NoahOWP init configs should be
            generated.
        catchment_subset: Set[str], optional
            An optional subset of catchments for which to generate init configs; ``None`` by default, which means to
            generate for all catchments in the hydrofabric.
        other_builder_hook_types: Dict[str, partial], optional
            Additional builder types that create module init configs, partially initialized in advance as
            :class:`partial` objects and keyed by the config string that appears in the realization config.
        """
        self._realization: NgenRealization = ngen_realization
        self._hf_data: gpd.GeoDataFrame = hydrofabric_data
        self._hf_model_attributes: pd.DataFrame = hydrofabric_model_attributes

        self._builder_hooks: Dict[str, Any] = {**self._module_to_model_map}

        if noah_owp_params_dir is not None:
            noah_owp = partial(
                NoahOWPBuilder,
                parameter_dir=noah_owp_params_dir if isinstance(noah_owp_params_dir, Path) else Path(noah_owp_params_dir),
                start_time=ngen_realization.time.start_time,
                end_time=ngen_realization.time.end_time,
            )
            self._builder_hooks["NoahOWP"] = noah_owp

        self._catchment_subset: Optional[Set[str]] = catchment_subset

        if other_builder_hook_types is not None:
            if not set(self._module_to_model_map.keys()).isdisjoint(set(other_builder_hook_types.keys())):
                raise ValueError(f"Can't provide {self.__class__.__name__} duplicate module builder name key")
            self._builder_hooks.update(other_builder_hook_types)

    def _get_module_builder_types_for_catchment(self, catchment_id: str) -> List:
        """
        Get a list of builder types to build init config model objects for modules use by the associated formulation.

        Get a list of the classes for builder types that build BMI module init config models for all the modules that
        appear in the catchment formulation for the referenced catchment.  These builder types are classes from the
        ``ngen.config_gen`` package, such as :class:`Cfe`, that are used to  not the Pydantic model classes that
        actually model the BMI init config itself.

        Parameters
        ----------
        catchment_id: str
            The id of the related catchment in the realization config.

        Returns
        -------
        List
            A list of builder types to build init config model objects for modules use by the associated formulation.
        """
        # Return no builder types for the catchment if a catchment subset was specified and this catchment isn't in it
        if self._catchment_subset and catchment_id not in self._catchment_subset:
            return list()

        formulations = self._realization.catchments.get(catchment_id, self._realization.global_config).formulations
        if len(formulations) > 1:
            raise DmodRuntimeError(f"{self.__class__.__name__} can't generate for ensemble config of {catchment_id}")
        builder_types = []
        for module_name in self.get_module_names(formulations[0]):
            if module_name in self._no_init_config_modules:
                continue
            if module_name not in self._builder_hooks:
                raise NotImplementedError(f"{self.__class__.__name__} not implemented for '{module_name}' BMI module")
            builder_types.append(self._builder_hooks[module_name])
        return builder_types

    def generate_configs(self) -> Generator[Tuple[str, BaseModel], None, None]:
        """
        Generate and yield generated configs.

        Yields
        -------
        Generator[Tuple[str, BaseModel], None, None]
            A generator yielding tuples, containing a catchment id and a deserialized BMI init config model object
            applicable to that catchment.
        """
        cat_hook_object = BmiGenDivideIdHookObject()
        for cat_hook_provider in DefaultHookProvider(hf=self._hf_data, hf_lnk_data=self._hf_model_attributes):
            # Get the divide/catchment id
            cat_hook_object.visit(cat_hook_provider)
            cat_id = cat_hook_object.divide_id()
            if self._catchment_subset and cat_id not in self._catchment_subset:
                continue

            for visitable_config_builder_type in self._get_module_builder_types_for_catchment(catchment_id=cat_id):
                builder = visitable_config_builder_type()
                builder.visit(cat_hook_provider)
                yield cat_id, builder.build()

    def get_supported_module_names(self) -> List[str]:
        """
        Get a list of the supported BMI module configuration names for which this instance can generate an init config.

        Returns
        -------
        List[str]
            List of the supported BMI module configuration names for which instance type can generate an init config.
        """
        return [k for k in self._builder_hooks]

    def write_configs(self, output_dir: Union[str, Path]):
        """
        Write the generated configs to a given directory.

        Parameters
        ----------
        output_dir: Union[str, Path]
            The directory to write the config files to, as a path or string.

        Raises
        ------
        ValueError
            Raised if parameter represents an existing, non-directory path.
        """
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        if not output_dir.exists():
            output_dir.mkdir(parents=True)
        elif not output_dir.is_dir():
            raise ValueError(f"{self.__class__.__name__} can't write configs to non-directory path {output_dir!s}")

        file_writer = DefaultFileWriter(output_dir)
        for catchment_id, config_gen_base_model in self.generate_configs():
            file_writer(catchment_id, config_gen_base_model)
