"""
Defines classes used to intrepret locations and how to link them together
"""
import json
import typing

from dmod.core.common import is_true
from dmod.core.common import contents_are_equivalent
from dmod.core.common import Bag

from .template import TemplateManager
from .base import TemplatedSpecification

from .backend import BackendSpecification
from .backend import LoaderSpecification

from .fields import ValueSelector


class LocationSpecification(TemplatedSpecification):
    """
    A specification for where location data should be found
    """

    def __eq__(self, other: "LocationSpecification") -> bool:
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
        self.__from_field = configuration.get("from_field", self.__from_field)
        self.__pattern = configuration.get("pattern", self.__pattern)

        if 'ids' in configuration:
            ids = configuration.get("ids")
            if isinstance(ids, str):
                ids = list(ids)
            elif ids is None:
                ids = list()

            self.__ids = ids

        self.__should_identify(configuration.get("identify", self.__identify))

    def validate(self) -> typing.Sequence[str]:
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

    __slots__ = ["__identify", "__from_field", "__pattern", "__ids"]

    def __init__(
        self,
        identify: bool = None,
        from_field: str = None,
        pattern: typing.Union[str, typing.Sequence[str]] = None,
        ids: typing.List[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)

        if isinstance(ids, str):
            ids = list(ids)
        elif ids is None:
            ids = list()

        if from_field or ids:
            identify = True

        if identify is None:
            identify = False

        if from_field != 'filename' and isinstance(pattern, str):
            pattern_starts_at_root = pattern.startswith("/")
            pattern = pattern.split("/")

            if pattern_starts_at_root:
                pattern.insert(0, "$")

        self.__identify = None
        self.__from_field = from_field
        self.__pattern = pattern
        self.__ids = ids

        self.__should_identify(identify)

    def __should_identify(self, identify: bool = None):
        if self.__from_field or self.__ids:
            identify = True

        if identify is None:
            identify = False

        self.__identify = is_true(identify)

    @property
    def ids(self) -> typing.List[str]:
        """
        A list of specific ids to use for locations
        """
        return self.__ids

    @property
    def from_field(self) -> str:
        """
        A field from which to retrieve location names from a source

        This would be where you'd indicate that the location name came from the filename, for example
        """
        return self.__from_field

    @property
    def pattern(self) -> typing.Sequence[str]:
        """
        An optional regex for how to retrieve the name

        If the data are in files like `cat-67.json`, a regex like `^[A-Za-z]+-\d+` would indicate that the name
        should be interpreted as `cat-67` and not `cat-67.json`
        """
        return self.__pattern

    @property
    def identify(self) -> bool:
        """
        Whether locations should even be attempted to be identified

        Location identification isn't really necessary for single location evaluations, for example
        """
        return self.__identify

    def __str__(self) -> str:
        if self.__from_field and self.__pattern:
            return f"Identify locations matching '{self.__pattern}' from the '{self.__from_field}'"
        elif self.__from_field:
            return f"Identify locations from the '{self.__from_field}'"
        elif self.__ids:
            return f"Use the ids with the names: {', '.join(self.__ids)}"
        return "Don't identify locations"

    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields.update({
            "identify": self.__identify,
            "from_field": self.__from_field,
            "pattern": self.__pattern,
            "ids": self.__ids
        })
        return fields


class CrosswalkSpecification(LoaderSpecification):
    """
    Specifies how locations in the observations should be linked to locations in the predictions
    """

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

    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields.update({
            "backend": self._backend.to_dict(),
            "origin": self.origin,
            "field": self.__field.to_dict(),
            "prediction_field_name": self.__prediction_field_name,
            "observation_field_name": self.__observation_field_name
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

        if 'field' in configuration:
            if self.__field:
                self.__field.overlay_configuration(
                    configuration=configuration['field'],
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.__field = ValueSelector.create(
                    data=configuration['field'],
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

        if 'origin' in configuration:
            origin = configuration['origin'] or "$"

            self.__origin = origin.split(".") if isinstance(origin, str) else origin

        self.__observation_field_name = configuration.get("observation_field_name", self.__observation_field_name)
        self.__prediction_field_name = configuration.get("prediction_field_name", self.__prediction_field_name)

    def validate(self) -> typing.Sequence[str]:
        backend_validation = self._backend.validate()
        validation_messages = list()

        if backend_validation:
            validation_messages.append(
                f"The backend specification for the crosswalk specification is not valid: "
                f"{', '.join(backend_validation)}"
            )

        return validation_messages

    __slots__ = ['__origin', "__field", '__prediction_field_name', '__observation_field_name']

    def __init__(
        self,
        backend: BackendSpecification,
        field: ValueSelector,
        observation_field_name: str,
        prediction_field_name: str = None,
        origin: typing.Union[str, typing.Sequence[str]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        if origin is None:
            origin = "$"

        self._backend = backend
        self.__origin = origin.split(".") if isinstance(origin, str) else origin
        self.__field = field
        self.__observation_field_name = observation_field_name
        self.__prediction_field_name = prediction_field_name if prediction_field_name else observation_field_name

    @property
    def backend(self) -> BackendSpecification:
        return self._backend

    @property
    def field(self) -> ValueSelector:
        return self.__field

    @property
    def prediction_field_name(self) -> str:
        return self.__prediction_field_name

    @property
    def observation_field_name(self) -> str:
        return self.__observation_field_name

    @property
    def origin(self) -> typing.Sequence[str]:
        return self.__origin

    def __str__(self) -> str:
        return f"Crosswalk from: {str(self._backend)} with observed values from {str(self.__field)}"
