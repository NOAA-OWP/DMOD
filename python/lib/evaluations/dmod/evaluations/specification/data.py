"""
@TODO: Put a module wide description here
"""
import json
import typing

import dmod.core.common as common

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
        elif not hasattr(other, "x_axis"):
            return False

        if self.value_field != other.value_field:
            return False
        elif self.locations != other.locations:
            return False
        elif not common.contents_are_equivalent(self.field_mapping, other.field_mapping):
            return False
        elif self.unit != other.unit:
            return False

        return self.x_axis == other.x_axis

    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields.update({
            "value_selectors": [selector.to_dict() for selector in self.__value_selectors],
            "backend": self._backend.to_dict(),
            "locations": self.__locations.to_dict(),
            "field_mapping": [mapping.to_dict() for mapping in self.__field_mapping],
            "unit": self.__unit.to_dict(),
            "x_axis": self.__x_axis,
            "value_field": self.__value_field
        })
        return fields

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if 'backend' in configuration:
            if self._backend:
                self._backend.overlay_configuration(
                    configuration=configuration['backend'],
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self._backend = BackendSpecification.create(
                    data=configuration['backend'],
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

        self.__value_field = configuration.get("value_field", self.__value_field)

        for selector in configuration.get("value_selectors", list()):
            matching_selector = common.find(
                self.__value_selectors,
                lambda value_selector: value_selector.name == selector['name']
            )

            if matching_selector:
                matching_selector.overlay_configuration(
                    configuration=selector,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.__value_selectors.append(
                    ValueSelector.create(
                        data=selector,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                )

        if "unit" in configuration:
            self.__unit = UnitDefinition.create(
                data=configuration['unit'],
                template_manager=template_manager,
                decoder_type=decoder_type
            )

        if 'locations' in configuration:
            if self.__locations:
                self.__locations.overlay_configuration(
                    configuration=configuration.get("locations"),
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.__locations = LocationSpecification.create(
                    data=configuration.get("locations"),
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

        for mapping in configuration.get("field_mapping", list()):
            matching_mapping = common.find(
                self.__field_mapping,
                lambda field_mapping: field_mapping.field == mapping.get("field")
            )

            if matching_mapping:
                matching_mapping.overlay_configuration(
                    configuration=configuration,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.__field_mapping.append(
                    FieldMappingSpecification.create(
                        data=mapping,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                )

        self.__x_axis = configuration.get("x_axis", self.__x_axis)

    def validate(self) -> typing.Sequence[str]:
        return list()

    __slots__ = [
        "__value_field",
        "__locations",
        "__field_mapping",
        "__value_selectors",
        "__unit",
        "__x_axis"
    ]

    def __init__(
        self,
        value_field: str,
        backend: BackendSpecification,
        value_selectors: typing.Sequence[ValueSelector],
        unit: UnitDefinition,
        x_axis: str = None,
        locations: LocationSpecification = None,
        field_mapping: typing.List[FieldMappingSpecification] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._backend = backend

        if not self.name:
            self._name = value_field

        self.__value_field = value_field
        self.__locations = locations if locations else LocationSpecification(identify=False)
        self.__field_mapping: typing.List[FieldMappingSpecification] = field_mapping if field_mapping else list()
        self.__value_selectors: typing.MutableSequence[ValueSelector] = [selector for selector in value_selectors]
        self.__unit = unit
        self.__x_axis = x_axis or "value_date"

    @property
    def value_field(self) -> str:
        return self.__value_field

    @property
    def backend(self) -> BackendSpecification:
        return self._backend

    @property
    def locations(self) -> LocationSpecification:
        return self.__locations

    @property
    def field_mapping(self) -> typing.List[FieldMappingSpecification]:
        return [mapping for mapping in self.__field_mapping]

    @property
    def value_selectors(self) -> typing.Sequence[ValueSelector]:
        return [selector for selector in self.__value_selectors]

    @property
    def unit(self) -> UnitDefinition:
        return self.__unit

    @property
    def x_axis(self) -> str:
        return self.__x_axis

    def get_column_options(self) -> typing.Dict[str, typing.Union[typing.Dict[str, typing.Any], typing.List[str]]]:
        """
        Gets options that may be required for loading data into a table

        Returns:

        """
        options = dict()

        for selector in self.__value_selectors:
            selector_options = selector.get_column_types()

            for key, value in selector_options.items():
                if key not in options:
                    options[key] = value
                elif isinstance(options[key], dict):
                    options[key].update(value)
                elif common.is_sequence_type(options[key]):
                    for entry in value:
                        if entry not in options[key]:
                            options[key].append(entry)

        return options

    def __str__(self) -> str:
        return f"{self._name} ({str(self._backend)})"
