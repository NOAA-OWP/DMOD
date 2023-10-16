"""
Defines classes used to load, interpret, and apply thresholds
"""
from __future__ import annotations

import typing
import json

from pydantic import Field

from dmod.core.common import find
from dmod.core.common import contents_are_equivalent
from dmod.core.common import Bag
from pydantic import validator

from .base import TemplatedSpecification
from .template import TemplateManager

from .backend import BackendSpecification
from .backend import LoaderSpecification

from .locations import LocationSpecification

from .unit import UnitDefinition
from .fields import AssociatedField


class ThresholdDefinition(TemplatedSpecification):
    """
    A definition of a single threshold, the field that it comes from, and its significance
    """
    field: typing.Optional[typing.Union[str, typing.Sequence[str]]] = Field(
        default=None,
        description="Where to look for threshold values"
    )
    weight: typing.Optional[typing.Union[int, float]] = Field(
        default=None,
        description="A relative score for the significance of this threshold"
    )
    unit: typing.Optional[typing.Union[str, dict, UnitDefinition]] = Field(
        default=None,
        description="A definition for what the threshold is measured in"
    )

    def __eq__(self, other) -> bool:
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "field") or self.field != other.field:
            return False
        elif not hasattr(other, "unit") or self.unit != other.unit:
            return False

        return hasattr(other, "weight") and self.weight == other.weight

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if 'unit' in configuration:
            if self.unit:
                self.unit.overlay_configuration(
                    configuration=configuration['unit'],
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.__set_unit_definition(configuration.get('unit'))

        if 'field' in configuration:
            self.__set_field(configuration['field'])

        if 'weight' in configuration:
            self.weight = float(configuration['weight'])

    def validate_self(self) -> typing.Sequence[str]:
        validation_messages = list()

        if not isinstance(self.unit, UnitDefinition):
            validation_messages.append(f"{self.get_specification_type()} is missing a unit definition")

        if not isinstance(self.weight, (str, int, float)):
            validation_messages.append(f"{self.get_specification_type()} is missing a weight value")

        if not isinstance(self.field, typing.Iterable):
            validation_messages.append(f"{self.get_specification_type()} is missing a field indication")

        if not isinstance(self.name, str):
            validation_messages.append(f"{self.get_specification_type()} is missing a name")

        return validation_messages

    def __set_unit_definition(self, unit: typing.Union[UnitDefinition, str, dict]):
        if isinstance(unit, str):
            unit = UnitDefinition(value=unit)
        elif isinstance(unit, dict):
            unit = UnitDefinition.create(unit)

        self.unit = unit

    @validator("unit")
    def _interpret_unit(
        cls,
        value: typing.Union[UnitDefinition, str, bytes, dict] = None
    ) -> typing.Optional[UnitDefinition]:
        if isinstance(value, bytes):
            value = value.decode()

        if isinstance(value, str):
            value = UnitDefinition(value=value)
        elif isinstance(value, dict):
            value = UnitDefinition.create(value)

        return value

    def __set_field(self, field: typing.Union[str, bytes, typing.Sequence[str]] = None):
        if field is None:
            return

        if isinstance(field, bytes):
            field = field.decode()

        if isinstance(field, str):
            self.field = field.split("/")
        else:
            self.field = field

    @validator("field")
    def _interpret_field(
        cls,
        value: typing.Union[str, bytes, typing.Sequence[str]] = None
    ) -> typing.Optional[typing.Sequence[str]]:
        if value is None:
            return value

        if isinstance(value, bytes):
            value = value.decode()

        if isinstance(value, str):
            value = value.split("/")

        return value

    def __str__(self) -> str:
        return f"{self.name}, weighing {self.weight}, from the '{self.field}' field."

    def __repr__(self) -> str:
        return str(self.to_dict())


class ThresholdApplicationRules(TemplatedSpecification):
    """
    Added rules for how thresholds should be applied.

    One example for use is transforming one or more values in a threshold and one or more values in the
    observations to put all values needed to apply thresholds to values equivalent.

    If a threshold is described as being on a month or day and an observation is taken at a date and time,
    the threshold month and day will need to be transformed into a new 'Day' object field while the date field on the
    observations will need to be converted to a `Day` object

    Example:
        >>> application_rules = {
                "name": "Date to Day",
                "threshold_field": {
                    "name": "threshold_day",
                    "path": [
                        "month_nu",
                        "day_nu"
                    ],
                    "datatype": "Day"
                },
                "observation_field": {
                    "name": "threshold_day",
                    "path": [
                        "value_date"
                    ],
                    "datatype": "Day"
                }
            }

    This indicates that thresholds and observations should line up by matching the day of the threshold generated
    by combining the month and day and the day of the observation by getting the day of each value date. Thresholds
    with single values per location or such wouldn't need this definition since no other transformations are needed
    to link the threshold values to their observations or predictions.
    """
    threshold_field: typing.Optional[AssociatedField] = Field(
        default=None,
        description="How to interpret one or more threshold fields to line up with observations or predictions"
    )
    observation_field: typing.Optional[AssociatedField] = Field(
        default=None,
        description="How to interpret one or more observation fields to line up with thresholds"
    )
    prediction_field: typing.Optional[AssociatedField] = Field(
        default=None,
        description="How to interpret one or more prediction fields to line up with thresholds"
    )

    def __eq__(self, other: "ThresholdApplicationRules") -> bool:
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "threshold_field") or self.threshold_field != other.threshold_field:
            return False
        elif not hasattr(other, "observation_field") or self.observation_field != other.observation_field:
            return False

        return hasattr(other, "prediction_field") and self.prediction_field == other.prediction_field

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if "threshold_field" in configuration:
            threshold_field = configuration['threshold_field']

            if self.threshold_field:
                self.threshold_field.apply_configuration(
                    configuration=threshold_field,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.threshold_field = AssociatedField.create(
                    data=threshold_field,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

        if "observation_field" in configuration:
            observation_field = configuration['observation_field']

            if self.observation_field:
                self.observation_field.apply_configuration(
                    configuration=observation_field,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.observation_field = AssociatedField(
                    data=observation_field,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

        if "prediction_field" in configuration:
            prediction_field = configuration['prediction_field']

            if self.prediction_field:
                self.prediction_field.apply_configuration(
                    configuration=prediction_field,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.prediction_field = AssociatedField(
                    data=prediction_field,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

    def validate_self(self) -> typing.Sequence[str]:
        messages = list()

        if not self.threshold_field:
            messages.append(
                f"There is no definition for how manipulate a threshold in a {self.get_specification_description()}"
            )

        if not self.observation_field and not self.prediction_field:
            messages.append(
                f"There are no definitions for how to manipulate field values "
                f"in a {self.get_specification_description()}"
            )

        return messages

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        representation = f"The threshold built around {self.threshold_field}"

        if self.observation_field and self.prediction_field:
            representation += f" is applied to the observations aligned by {self.observation_field} " \
                              f"and the predictions aligned by {self.prediction_field}"
        elif self.observation_field:
            representation += f" is applied to the observations aligned by {self.observation_field}"
        else:
            representation += f" is applied to the predictions aligned by {self.prediction_field}"

        return representation


class ThresholdSpecification(LoaderSpecification):
    """
    Instructions for how to load and apply thresholds to observed and predicted data
    """
    definitions: typing.List[ThresholdDefinition] = Field(
        description="The thresholds to apply to data"
    )
    locations: typing.Optional[LocationSpecification] = Field(
        default=None,
        description="How locations are identified within the threshold data"
    )
    application_rules: typing.Optional[ThresholdApplicationRules] = Field(
        default=None,
        description="Extra transformations needed to match thresholds to their observations and predictions"
    )
    origin: typing.Optional[typing.Union[str, typing.Sequence[str]]] = Field(
        default=None,
        description="Where to start looking for threshold data within the threshold input"
    )

    def __eq__(self, other: ThresholdSpecification):
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "locations") or self.locations != other.locations:
            return False
        elif not hasattr(other, "origin") or not contents_are_equivalent(self.origin, other.origin):
            return False
        elif not hasattr(other, "definitions"):
            return False
        elif not contents_are_equivalent(Bag(self.definitions), Bag(other.definitions)):
            return False

        return hasattr(other, "application_rules") and self.application_rules == other.application_rules

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        super().apply_configuration(
            configuration=configuration,
            template_manager=template_manager,
            decoder_type=decoder_type
        )

        self.__set_origin(configuration.get("origin", self.origin))

        if "locations" in configuration:
            location_configuration = configuration['locations']

            if self.locations:
                self.locations.apply_configuration(
                    configuration=location_configuration,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.locations = LocationSpecification.create(
                    data=location_configuration,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

        for threshold_definition in configuration.get('definitions', []):
            if self.definitions:
                matching_definition = find(
                    self.definitions,
                    lambda definition: definition.identities_match(threshold_definition)
                )

                if matching_definition:
                    matching_definition.overlay_configuration(
                        configuration=threshold_definition,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                else:
                    self.definitions.append(
                        ThresholdDefinition.create(
                            data=threshold_definition,
                            template_manager=template_manager,
                            decoder_type=decoder_type
                        )
                    )
            else:
                self.definitions.append(
                    ThresholdDefinition.create(
                        data=threshold_definition,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                )

        application_rules = configuration.get("application_rules")

        if application_rules:
            if self.application_rules:
                self.application_rules.apply_configuration(
                    configuration=application_rules,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.application_rules = ThresholdApplicationRules.create(
                    data=application_rules,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

    def validate_self(self) -> typing.Sequence[str]:
        messages = list()

        if self.backend is None:
            messages.append(f"No backend was configured for a {self.get_specification_description()}")
        else:
            messages.extend(self.backend.validate_self())

        if self.locations:
            messages.extend(self.locations.validate_self())

        if len(self.definitions) == 0:
            messages.append("There are no threshold definitions defined within a threshold specification")

        for definition in self.definitions:
            messages.extend(definition.validate_self())

        return messages

    @validator("origin")
    def _interpret_origin(cls, value: typing.Union[str, bytes, typing.Sequence[str]] = None) -> typing.Sequence[str]:
        if isinstance(value, bytes):
            value = value.decode()

        if not value:
            value = ["$"]
        elif isinstance(value, str):
            origin_starts_at_root = value.startswith("/")
            value = value.split("/")

            if origin_starts_at_root and value[0] != "$":
                value.insert(0, "$")

        return value

    def __set_origin(self, origin: str = None):
        if self.origin == origin:
            return

        origin_starts_at_root = False

        if isinstance(origin, str):
            origin_starts_at_root = origin.startswith("/")
            origin = origin.split("/")
        elif isinstance(origin, bytes):
            origin = origin.decode()
            origin_starts_at_root = origin.startswith("/")
            origin = origin.split("/")
        elif not origin:
            origin = ["$"]

        if origin_starts_at_root and origin[0] != '$':
            origin.insert(0, "$")

        self.origin = origin

    @property
    def total_weight(self) -> float:
        """
        The weight of all defined thresholds
        """
        return sum([definition.weight for definition in self.definitions])

    def __contains__(self, definition_name) -> bool:
        matching_definitions = [
            definition
            for definition in self.definitions
            if definition.name.lower() == definition_name.lower()
        ]

        if matching_definitions:
            return True

        matching_definitions = [
            definition
            for definition in self.definitions
            if definition.field[-1].lower() == definition_name.lower()
        ]

        if matching_definitions:
            return True

        return False

    def __getitem__(self, definition_name: str) -> typing.Optional[ThresholdDefinition]:
        matching_definitions = [
            definition
            for definition in self.definitions
            if definition.name.lower() == definition_name.lower()
        ]

        if matching_definitions:
            return matching_definitions[0]

        matching_definitions = [
            definition
            for definition in self.definitions
            if definition.field[-1].lower() == definition_name.lower()
        ]

        if matching_definitions:
            return matching_definitions[0]

        return None
