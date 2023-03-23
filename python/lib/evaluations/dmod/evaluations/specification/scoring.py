"""
@TODO: Put a module wide description here
"""
import typing
import json

import dmod.metrics as metrics
import dmod.metrics.metric as metric_functions

from dmod.core.common import find
from dmod.core.common import contents_are_equivalent

from .base import TemplatedSpecification

from .template import TemplateManager


class MetricSpecification(TemplatedSpecification):
    def __eq__(self, other: "MetricSpecification") -> bool:
        if not super().__eq__(other):
            return False
        if not hasattr(other, "name") or self.name != other.name:
            return False

        return hasattr(other, 'weight') and self.weight == other.weight

    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields['weight'] = self.weight
        return fields

    def validate(self) -> typing.Sequence[str]:
        return list()

    __slots__ = ["__weight"]

    def __init__(
        self,
        weight: float,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.__weight = weight

    @property
    def weight(self) -> float:
        return self.__weight

    def __str__(self) -> str:
        description = f"{self.name} = {self.__weight}"

        if self.properties:
            description += f" ({str(self.properties)}"")"

        return description

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if 'weight' in configuration:
            self.__weight = float(configuration['weight'])


class SchemeSpecification(TemplatedSpecification):
    def __eq__(self, other: "SchemeSpecification") -> bool:
        if not super().__eq__(other):
            return False

        return hasattr(other, "metrics") and contents_are_equivalent(self.metric_functions, other.metric_functions)

    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields.update({
            "metrics": [metric.to_dict() for metric in self.__metrics]
        })
        return fields

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        metric_definitions = configuration.get("metrics", list())

        for definition in metric_definitions:
            name = definition.get("name")

            if not name:
                continue

            matching_definition = find(
                self.__metrics,
                predicate=lambda metric_definition: metric_definition.name == name
            )

            if matching_definition:
                matching_definition.overlay_configuration(
                    configuration=definition,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.__metrics.append(
                    MetricSpecification.create(
                        data=definition,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                )

    def validate(self) -> typing.Sequence[str]:
        messages = list()

        for metric in self.__metrics:
            messages.extend(metric.validate())

        return messages

    __slots__ = ["__metrics"]

    def __init__(
        self,
        metrics: typing.Sequence[MetricSpecification],
        **kwargs
    ):
        super().__init__(**kwargs)

        self.__metrics = [metric for metric in metrics]

    @property
    def metric_functions(self) -> typing.Sequence[MetricSpecification]:
        return [metric for metric in self.__metrics]

    @property
    def total_weight(self) -> float:
        return sum([metric.weight for metric in self.__metrics])

    def generate_scheme(self, communicators: metrics.CommunicatorGroup = None) -> metrics.ScoringScheme:
        generated_metrics: typing.List[metrics.Metric] = [
            metric_functions.get_metric(metric.name, metric.weight)
            for metric in self.__metrics
        ]
        return metrics.ScoringScheme(
            metrics=generated_metrics,
            communicators=communicators
        )

    def __str__(self) -> str:
        details = {
            "metrics": [str(metric) for metric in self.__metrics],
        }

        if self.__properties:
            details["properties"] = self.__properties

        return str(details)
