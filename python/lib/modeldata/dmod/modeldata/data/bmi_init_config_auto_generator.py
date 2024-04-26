import geopandas as gpd
import pandas as pd

from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Union
from pydantic import BaseModel

from ngen.config.formulation import Formulation
from ngen.config.multi import MultiBMI
from ngen.config.realization import NgenRealization
from ngen.config_gen.file_writer import DefaultFileWriter
from ngen.config_gen.hook_providers import DefaultHookProvider
from ngen.config_gen.models import Pet
from ngen.config_gen.models.cfe import Cfe

from dmod.core.exception import DmodRuntimeError


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

    # TODO: get Noah OWP Modular params data/files/dir and add noah here
    _module_to_model_map: Dict[str, Any] = {"CFE": Cfe, "PET": Pet}

    @staticmethod
    def get_module_names(formulation: Formulation) -> List[str]:
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
            return [formulation.params.model_name]
        return list(modules)

    def __init__(self,
                 ngen_realization: NgenRealization,
                 hydrofabric_data: gpd.GeoDataFrame,
                 hydrofabric_model_attributes: pd.DataFrame,
                 catchment_subset: Optional[Set[str]] = None):
        self._realization: NgenRealization = ngen_realization
        self._hf_data: gpd.GeoDataFrame = hydrofabric_data
        self._hf_model_attributes: pd.DataFrame = hydrofabric_model_attributes
        self._catchment_subset: Optional[Set[str]] = catchment_subset

        # TODO: get Noah OWP Modular params data/files/dir

    def _get_module_builder_types_for_catchment(self, catchment_id: str) -> List:
        """
        Get a list of builder types to build init config model objects for modules use by the associated formulation.

        Get a list of the classes for builder types that build BMI module init config models for all the modules that
        appear in the catchment formulation for the referenced catchment.  These builder types are classes from the
        ``ngen.config_gen`` package, such as :class:`Cfe`, that are used to  not the Pydantic model classes that actually model the
        BMI init config itself.

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
            if module_name not in self._module_to_model_map:
                raise NotImplementedError(f"{self.__class__.__name__} not implemented for '{module_name}' BMI module")
            builder_types.append(self._module_to_model_map[module_name])
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
