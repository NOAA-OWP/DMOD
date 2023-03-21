"""
@TODO: Put a module wide description here
"""
import typing
import json

from dmod.core.common import find

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

    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields.update({
            "field": self.__field,
            "unit": self.__unit.to_dict(),
            "weight": self.__weight
        })
        return fields

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if 'unit' in configuration:
            if self.__unit:
                self.__unit.overlay_configuration(
                    configuration=configuration['unit'],
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.__set_unit_definition(configuration.get('unit'))

        if 'field' in configuration:
            self.__set_field(configuration['field'])

        if 'weight' in configuration:
            self.__weight = float(configuration['weight'])

    def validate(self) -> typing.Sequence[str]:
        validation_messages = list()

        if not isinstance(self.__unit, UnitDefinition):
            validation_messages.append(f"{self.get_specification_type()} is missing a unit definition")

        if not isinstance(self.__weight, (str, int, float)):
            validation_messages.append(f"{self.get_specification_type()} is missing a weight value")

        if not isinstance(self.__field, typing.Iterable):
            validation_messages.append(f"{self.get_specification_type()} is missing a field indication")

        if not isinstance(self.name, str):
            validation_messages.append(f"{self.get_specification_type()} is missing a name")

        return validation_messages

    __slots__ = ["__field", "__weight", "__unit"]

    def __init__(
        self,
        field: typing.Union[str, bytes, typing.Sequence[str]] = None,
        weight: typing.Union[str, float] = None,
        unit: typing.Union[UnitDefinition, str, dict] = None,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.__field: typing.Optional[typing.Sequence[str]] = None

        self.__set_field(field)

        self.__weight = weight

        self.__unit: typing.Optional[UnitDefinition] = None
        self.__set_unit_definition(unit)

    def __set_unit_definition(self, unit: typing.Union[UnitDefinition, str, dict]):
        if isinstance(unit, str):
            unit = UnitDefinition(value=unit)
        elif isinstance(unit, dict):
            unit = UnitDefinition.create(unit)

        self.__unit = unit

    def __set_field(self, field: typing.Union[str, bytes, typing.Sequence[str]] = None):
        if field is None:
            return

        if isinstance(field, bytes):
            field = field.decode()

        if isinstance(field, str):
            self.__field = field.split("/")
        else:
            self.__field = field

    @property
    def field(self) -> typing.Sequence[str]:
        """
        Returns:
            The name of the field in the datasource where these values are supposed to come from
        """
        return self.__field

    @property
    def weight(self) -> float:
        """
        Returns:
            The significance of the threshold
        """
        return self.__weight

    @property
    def unit(self) -> UnitDefinition:
        return self.__unit

    def __str__(self) -> str:
        return f"{self.name}, weighing {self.__weight}, from the '{self.__field}' field."

    def __repr__(self) -> str:
        return str(self.to_dict())


class ThresholdApplicationRules(TemplatedSpecification):
    """
    Added rules for how thresholds should be applied
    """

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
                self.__threshold_field = AssociatedField.create(
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
                self.__observation_field = AssociatedField(
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
                self.__prediction_field = AssociatedField(
                    data=prediction_field,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields['threshold_field'] = self.threshold_field.to_dict()

        if self.observation_field:
            fields['observation_field'] = self.observation_field.to_dict()

        if self.prediction_field:
            fields['prediction_field'] = self.prediction_field.to_dict()

        return fields

    __slots__ = ['__threshold_field', '__observation_field', '__prediction_field']

    def validate(self) -> typing.Sequence[str]:
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

    def __init__(
        self,
        threshold_field: AssociatedField,
        observation_field: AssociatedField = None,
        prediction_field: AssociatedField = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.__threshold_field = threshold_field
        self.__observation_field = observation_field
        self.__prediction_field = prediction_field

    @property
    def threshold_field(self) -> AssociatedField:
        return self.__threshold_field

    @property
    def observation_field(self) -> typing.Optional[AssociatedField]:
        return self.__observation_field

    @property
    def prediction_field(self) -> typing.Optional[AssociatedField]:
        return self.__prediction_field

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        representation = f"The threshold built around {self.__threshold_field}"

        if self.__observation_field and self.__prediction_field:
            representation += f" is applied to the observations aligned by {self.__observation_field} " \
                              f"and the predictions aligned by {self.__prediction_field}"
        elif self.__observation_field:
            representation += f" is applied to the observations aligned by {self.__observation_field}"
        else:
            representation += f" is applied to the predictions aligned by {self.__prediction_field}"

        return representation


class ThresholdSpecification(LoaderSpecification):
    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields.update({
            "locations": self.__locations.to_dict(),
            "origin": self.__origin,
            "definitions": [definition.to_dict() for definition in self.__definitions],
        })

        if self.application_rules:
            fields['application_rules'] = self.__application_rules.to_dict()

        return fields

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

        self.__set_origin(configuration.get("origin", self.__origin))

        if "locations" in configuration:
            location_configuration = configuration['locations']

            if self.locations:
                self.locations.apply_configuration(
                    configuration=location_configuration,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.__locations = LocationSpecification.create(
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
                    self.__definitions.append(
                        ThresholdDefinition.create(
                            data=threshold_definition,
                            template_manager=template_manager,
                            decoder_type=decoder_type
                        )
                    )
            else:
                self.__definitions.append(
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
                self.__application_rules = ThresholdApplicationRules.create(
                    data=application_rules,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

    def validate(self) -> typing.Sequence[str]:
        messages = list()

        if self.backend is None:
            messages.append(f"No backend was configured for a {self.get_specification_description()}")
        else:
            messages.extend(self.backend.validate())

        if self.locations:
            messages.extend(self.locations.validate())

        if len(self.__definitions) == 0:
            messages.append("There are no threshold definitions defined within a threshold specification")

        for definition in self.__definitions:
            messages.extend(definition.validate())

        return messages

    __slots__ = ["__locations", "__definitions", "__origin", "__application_rules"]

    def __init__(
        self,
        definitions: typing.Sequence[ThresholdDefinition],
        locations: LocationSpecification = None,
        application_rules: ThresholdApplicationRules = None,
        origin: typing.Union[str, typing.Sequence[str]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.__definitions: typing.MutableSequence[ThresholdDefinition] = list()

        if definitions:
            self.__definitions.extend([definition for definition in definitions])

        self.__locations = locations
        self.__application_rules = application_rules
        self.__origin = None

        if origin:
            self.__set_origin(origin)

    def __set_origin(self, origin: str = None):
        if self.__origin == origin:
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

        self.__origin = origin

    @property
    def backend(self) -> BackendSpecification:
        return self._backend

    @property
    def definitions(self) -> typing.Sequence[ThresholdDefinition]:
        return self.__definitions

    @property
    def locations(self) -> typing.Optional[LocationSpecification]:
        return self.__locations

    @property
    def origin(self) -> typing.Optional[typing.Sequence[str]]:
        return self.__origin

    @property
    def application_rules(self) -> ThresholdApplicationRules:
        return self.__application_rules

    @property
    def total_weight(self) -> float:
        """
        The weight of all defined thresholds
        """
        return sum([definition.weight for definition in self.__definitions])

    def __contains__(self, definition_name) -> bool:
        matching_definitions = [
            definition
            for definition in self.__definitions
            if definition.name.lower() == definition_name.lower()
        ]

        if matching_definitions:
            return True

        matching_definitions = [
            definition
            for definition in self.__definitions
            if definition.field[-1].lower() == definition_name.lower()
        ]

        if matching_definitions:
            return True

        return False

    def __getitem__(self, definition_name) -> typing.Optional[ThresholdDefinition]:
        matching_definitions = [
            definition
            for definition in self.__definitions
            if definition.name.lower() == definition_name.lower()
        ]

        if matching_definitions:
            return matching_definitions[0]

        matching_definitions = [
            definition
            for definition in self.__definitions
            if definition.field[-1].lower() == definition_name.lower()
        ]

        if matching_definitions:
            return matching_definitions[0]

        return None
