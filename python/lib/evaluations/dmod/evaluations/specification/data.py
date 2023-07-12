"""
Defines specification classes for how to read, define, interpret,
and transform data for evaluations
"""
import json
import typing

import pydantic
from dmod.core.common import find
from dmod.core.common import contents_are_equivalent
from dmod.core.common import Bag
from dmod.core.common import is_sequence_type
from pydantic import validator

from . import TemplateManager
from .backend import BackendSpecification
from .backend import LoaderSpecification

from .fields import ValueSelector
from .fields import FieldMappingSpecification

from .locations import LocationSpecification

from .unit import UnitDefinition


class DataSourceSpecification(LoaderSpecification):
    """
    Specification for where to get the actual data for evaluation
    """
    x_axis: typing.Optional[str] = pydantic.Field(
        default="value_date",
        description="What axis to evaluate found data upon"
    )
    value_selectors: typing.List[ValueSelector] = pydantic.Field(
        description="What values to select from the input data"
    )
    field_mapping: typing.Optional[typing.List[FieldMappingSpecification]] = pydantic.Field(
        default_factory=list,
        description="How to map fields to expected names"
    )
    unit: typing.Union[UnitDefinition, dict, str] = pydantic.Field(description="What unit the input data is measured in")
    locations: typing.Optional[LocationSpecification] = pydantic.Field(
        default=None,
        description="Details about how to glean location information from the input data"
    )
    value_field: str = pydantic.Field(
        description="What field within the input contains the value data to use within the evaluation"
    )

    @pydantic.root_validator
    def ensure_name_is_present(cls, values):
        if "name" not in values:
            values['name'] = values.get("value_field")
        return values

    def __eq__(self, other: "DataSourceSpecification"):
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "value_field"):
            return False
        elif not hasattr(other, "locations"):
            return False
        elif not hasattr(other, "field_mapping"):
            return False
        elif not hasattr(other, "unit"):
            return False
        elif not hasattr(other, "value_selectors"):
            return False
        elif not hasattr(other, "x_axis"):
            return False

        if self.value_field != other.value_field:
            return False
        elif self.locations != other.locations:
            return False
        elif not contents_are_equivalent(Bag(self.field_mapping), Bag(other.field_mapping)):
            return False
        elif self.unit != other.unit:
            return False
        elif not contents_are_equivalent(Bag(self.value_selectors), Bag(other.value_selectors)):
            return False

        return self.x_axis == other.x_axis

    @validator("unit")
    def _convert_unit(cls, value: typing.Union[str, dict, UnitDefinition]) -> UnitDefinition:
        if isinstance(value, str):
            value = UnitDefinition(value=value)
        elif isinstance(value, dict):
            value = UnitDefinition.parse_obj(value)

        return value

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if 'backend' in configuration:
            if self.backend:
                self.backend.overlay_configuration(
                    configuration=configuration['backend'],
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.backend = BackendSpecification.create(
                    data=configuration['backend'],
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

        self.value_field = configuration.get("value_field", self.value_field)

        for selector in configuration.get("value_selectors", list()):
            matching_selector = find(
                self.value_selectors,
                lambda value_selector: value_selector.name == selector['name']
            )

            if matching_selector:
                matching_selector.overlay_configuration(
                    configuration=selector,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.value_selectors.append(
                    ValueSelector.create(
                        data=selector,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                )

        if "unit" in configuration:
            self.unit = UnitDefinition.create(
                data=configuration['unit'],
                template_manager=template_manager,
                decoder_type=decoder_type
            )

        if 'locations' in configuration:
            if self.locations:
                self.locations.overlay_configuration(
                    configuration=configuration.get("locations"),
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.locations = LocationSpecification.create(
                    data=configuration.get("locations"),
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

        for mapping in configuration.get("field_mapping", list()):
            matching_mapping = find(
                self.field_mapping,
                lambda field_mapping: field_mapping.field == mapping.get("field")
            )

            if matching_mapping:
                matching_mapping.overlay_configuration(
                    configuration=configuration,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.field_mapping.append(
                    FieldMappingSpecification.create(
                        data=mapping,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                )

        self.x_axis = configuration.get("x_axis", self.x_axis)

    def validate_self(self) -> typing.Sequence[str]:
        return list()

    def get_column_options(self) -> typing.Dict[str, typing.Union[typing.Dict[str, typing.Any], typing.List[str]]]:
        """
        Gets options that may be required for loading data into a table

        Returns:

        """
        options = dict()

        for selector in self.value_selectors:
            selector_options = selector.get_column_types()

            for key, value in selector_options.items():
                if key not in options:
                    options[key] = value
                elif isinstance(options[key], dict):
                    options[key].update(value)
                elif is_sequence_type(options[key]):
                    for entry in value:
                        if entry not in options[key]:
                            options[key].append(entry)

        return options

    def __str__(self) -> str:
        return f"{self.name} ({str(self.backend)})"
