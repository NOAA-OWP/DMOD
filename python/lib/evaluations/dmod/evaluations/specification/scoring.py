"""
Defines the classes used to define how to score an evaluation
"""
from __future__ import annotations

import typing
import json

import dmod.metrics as metrics
import dmod.metrics.metric as metric_functions

from dmod.core.common import find
from dmod.core.common import contents_are_equivalent
from dmod.core.common import Bag
from pydantic import Field

from .base import TemplatedSpecification

from .template import TemplateManager


class MetricSpecification(TemplatedSpecification):
    weight: typing.Union[float] = Field(description="A relative rating of the significance of this metric")

    def __eq__(self, other: MetricSpecification) -> bool:
        if not super().__eq__(other):
            return False
        if not hasattr(other, "name") or self.name != other.name:
            return False

        return hasattr(other, 'weight') and self.weight == other.weight

    def validate_self(self) -> typing.Sequence[str]:
        return list()

    def __str__(self) -> str:
        description = f"{self.name} = {self.weight}"

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
            self.weight = float(configuration['weight'])


class SchemeSpecification(TemplatedSpecification):
    metric_functions: typing.List[MetricSpecification] = Field(
        description="The metrics to perform within the evaluation",
        alias="metrics"
    )

    def __eq__(self, other: SchemeSpecification) -> bool:
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "metric_functions"):
            return False

        return contents_are_equivalent(Bag(self.metric_functions), Bag(other.metric_functions))

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
                self.metric_functions,
                predicate=lambda metric_definition: metric_definition.name == name
            )

            if matching_definition:
                matching_definition.overlay_configuration(
                    configuration=definition,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.metric_functions.append(
                    MetricSpecification.create(
                        data=definition,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                )

    def validate_self(self) -> typing.Sequence[str]:
        messages = list()

        for metric in self.metric_functions:
            messages.extend(metric.validate_self())

        return messages

    @property
    def total_weight(self) -> float:
        return sum([metric.weight for metric in self.metric_functions])

    def generate_scheme(self, communicators: metrics.CommunicatorGroup = None) -> metrics.ScoringScheme:
        generated_metrics: typing.List[metrics.Metric] = [
            metric_functions.get_metric(metric.name, metric.weight)
            for metric in self.metric_functions
        ]
        return metrics.ScoringScheme(
            metrics=generated_metrics,
            communicators=communicators
        )

    def __str__(self) -> str:
        details = {
            "metrics": [str(metric) for metric in self.metric_functions],
        }

        if self.properties:
            details["properties"] = self.properties

        return str(details)
