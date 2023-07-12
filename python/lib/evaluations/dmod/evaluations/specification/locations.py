"""
Defines classes used to intrepret locations and how to link them together
"""
from __future__ import annotations

import json
import typing

import pydantic
from dmod.core.common import is_true
from dmod.core.common import contents_are_equivalent
from dmod.core.common import Bag
from pydantic import root_validator
from pydantic import validator

from .template import TemplateManager
from .base import TemplatedSpecification

from .backend import BackendSpecification
from .backend import LoaderSpecification

from .fields import ValueSelector


class LocationSpecification(TemplatedSpecification):
    """
    A specification for where location data should be found
    """

    identify: typing.Optional[bool] = pydantic.Field(
        default=False,
        description="""Whether locations should even be attempted to be identified

Location identification isn't really necessary for single location evaluations, for example"""
    )
    from_field: typing.Optional[str] = pydantic.Field(
        default=None,
        description="""A field from which to retrieve location names from a source
This would be where you'd indicate that the location name came from the filename, for example"""
    )
    pattern: typing.Optional[typing.Union[str, typing.Sequence[str]]] = pydantic.Field(
        default=None,
        description="""An optional regex for how to retrieve the name

If the data are in files like `cat-67.json`, a regex like `^[A-Za-z]+-\d+` would indicate that the name
should be interpreted as `cat-67` and not `cat-67.json`"""
    )
    ids: typing.Optional[typing.List[str]] = pydantic.Field(
        default=None,
        description="A list of specific ids to use for locations"
    )

    def __eq__(self, other: LocationSpecification) -> bool:
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "ids") or not contents_are_equivalent(Bag(self.ids), Bag(other.ids)):
            return False
        elif not hasattr(other, "from_field") or self.from_field != other.from_field:
            return False
        elif not hasattr(other, "pattern") or not contents_are_equivalent(self.pattern, other.pattern):
            return False

        return hasattr(other, "identify") and self.identify == other.identify

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        self.from_field = configuration.get("from_field", self.from_field)
        self.pattern = configuration.get("pattern", self.pattern)

        if 'ids' in configuration:
            ids = configuration.get("ids")
            if isinstance(ids, str):
                ids = list(ids)
            elif ids is None:
                ids = list()

            self.ids = ids

        self.__should_identify(configuration.get("identify", self.identify))

    def validate_self(self) -> typing.Sequence[str]:
        messages = list()

        if self.identify and not (self.from_field or self.pattern or self.ids):
            messages.append(
                "A from_field, a pattern, or a list of ids are required if locations are supposed to be identified"
            )

        if self.pattern and not self.from_field:
            messages.append(
                "A from_field is required if a location is to be found from a pattern"
            )
        elif self.from_field and self.ids:
            messages.append(
                "Locations may be discovered from a static list or a field, but not both"
            )

        return messages

    @root_validator
    def _interpret_field_values(cls, values: typing.Dict[str, typing.Any]):
        pattern = values.get("pattern")
        from_field = values.get("from_field")
        ids = values.get("ids", list())

        if isinstance(ids, str):
            ids = [ids]

        if from_field or ids or is_true(values.get("identify")):
            identify = True
        else:
            identify = False

        if from_field != "filename" and isinstance(pattern, str):
            pattern_starts_at_root = pattern.startswith("/")
            pattern = pattern.split("/")

            if pattern_starts_at_root:
                pattern.insert(0, "$")

            pattern = [
                part
                for part in pattern
                if part not in ("", None)
            ]

        values['identify'] = identify
        values['pattern'] = pattern
        values['ids'] = ids
        values['from_field'] = from_field
        return values

    def __should_identify(self, identify: bool = None):
        if self.from_field or self.ids:
            identify = True

        if identify is None:
            identify = False

        self.identify = is_true(identify)

    def __str__(self) -> str:
        if self.from_field and self.pattern:
            return f"Identify locations matching '{self.pattern}' from the '{self.from_field}'"
        elif self.from_field:
            return f"Identify locations from the '{self.from_field}'"
        elif self.ids:
            return f"Use the ids with the names: {', '.join(self.ids)}"
        return "Don't identify locations"


class CrosswalkSpecification(LoaderSpecification):
    """
    Specifies how locations in the observations should be linked to locations in the predictions
    """
    backend: BackendSpecification = pydantic.Field(description="How to load crosswalk data")
    field: ValueSelector = pydantic.Field(description="How to interpret values within the data")
    observation_field_name: str = pydantic.Field(
        description="The field within the data that describes the names of observed locations"
    )
    prediction_field_name: typing.Optional[str] = pydantic.Field(
        default=None,
        description="The field within the data that describes the identifiers of predicted locations"
    )
    origin: typing.Optional[typing.Union[str, typing.Sequence[str]]] = pydantic.Field(
        default=None,
        description="Where to start looking for the needed data within the loaded data"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __eq__(self, other: "CrosswalkSpecification"):
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "field") or self.field != other.field:
            return False
        elif not hasattr(other, 'prediction_field_name') or self.prediction_field_name != other.prediction_field_name:
            return False
        elif not hasattr(other, "observation_field_name") or self.observation_field_name != other.observation_field_name:
            return False

        return hasattr(other, "origin") and contents_are_equivalent(self.origin, other.origin)

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

        if 'field' in configuration:
            if self.field:
                self.field.overlay_configuration(
                    configuration=configuration['field'],
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.field = ValueSelector.create(
                    data=configuration['field'],
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

        if 'origin' in configuration:
            origin = configuration['origin'] or "$"

            self.origin = origin.split(".") if isinstance(origin, str) else origin

        self.observation_field_name = configuration.get("observation_field_name", self.observation_field_name)
        self.prediction_field_name = configuration.get("prediction_field_name", self.prediction_field_name)

    def validate_self(self) -> typing.Sequence[str]:
        backend_validation = self.backend.validate_self()
        validation_messages = list()

        if backend_validation:
            validation_messages.append(
                f"The backend specification for the crosswalk specification is not valid: "
                f"{', '.join(backend_validation)}"
            )

        return validation_messages

    @root_validator
    def _assign_defaults(cls, values: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        origin = values.get("origin")

        if isinstance(origin, bytes):
            origin = origin.decode()

        if origin in (None, ""):
            values['origin'] = ["$"]
        elif not isinstance(origin, typing.Sequence) or isinstance(origin, str):
            values['origin'] = origin.split(".") if isinstance(origin, str) else str(origin)

        if "prediction_field_name" not in values:
            values['prediction_field_name'] = values.get("observation_field_name")

        return values

    def __str__(self) -> str:
        return f"Crosswalk from: {str(self.backend)} with observed values from {str(self.field)}"
