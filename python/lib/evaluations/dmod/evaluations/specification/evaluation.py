"""
Defines how to define the overall specification for an evaluation and how to receive the results
"""
import json
import typing
import collections

import numpy
import pandas

from pydantic import Field

import dmod.metrics as metrics

from dmod.core.common import find
from dmod.core.common import truncate
from dmod.core.common import contents_are_equivalent
from dmod.core.common import Bag
from dmod.core.common import order_dictionary

from .base import TemplateManagerProtocol
from .base import TemplatedSpecification

from .data import DataSourceSpecification

from .locations import CrosswalkSpecification

from .scoring import SchemeSpecification

from .threshold import ThresholdSpecification


class EvaluationSpecification(TemplatedSpecification):
    observations: typing.List[DataSourceSpecification] = Field(
        description="Information on what data to use as 'true' data for the evaluation"
    )
    predictions: typing.List[DataSourceSpecification] = Field(
        description="Information on what data to evaluate"
    )
    crosswalks: typing.List[CrosswalkSpecification] = Field(
        description="Specifications for how to tie locations from the observations to the predictions"
    )

    thresholds: typing.List[ThresholdSpecification] = Field(
        description="Specifications for how different ranges of values should be treated and selected"
    )

    scheme: SchemeSpecification = Field(
        description="Instructions for how to evaluate the specified data"
    )

    def __eq__(self, other: "EvaluationSpecification") -> bool:
        if not super().__eq__(other):
            return False
        if not hasattr(other, "observations"):
            return False
        if not hasattr(other, "predictions"):
            return False
        elif not hasattr(other, "crosswalks"):
            return False
        elif not hasattr(other, "thresholds"):
            return False

        if not contents_are_equivalent(Bag(self.observations), Bag(other.observations)):
            return False
        elif not contents_are_equivalent(Bag(self.predictions), Bag(other.predictions)):
            return False
        elif not contents_are_equivalent(Bag(self.crosswalks), Bag(other.crosswalks)):
            return False
        elif not contents_are_equivalent(Bag(self.thresholds), Bag(other.thresholds)):
            return False

        return hasattr(other, "scheme") and self.scheme == other.scheme

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManagerProtocol,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if 'observations' in configuration:
            for observation_configuration in configuration.get("observations"):
                matching_observations = find(
                    self.observations,
                    lambda observations: observations.name == observation_configuration.get("name", )
                )

                if matching_observations:
                    matching_observations.overlay_configuration(
                        configuration=observation_configuration,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                else:
                    self.observations.append(
                        DataSourceSpecification.create(
                            data=observation_configuration,
                            template_manager=template_manager,
                            decoder_type=decoder_type
                        )
                    )

        if 'predictions' in configuration:
            for prediction_configuration in configuration.get("predictions"):
                matching_predictions = find(
                    self.predictions,
                    lambda predictions: predictions.name == prediction_configuration.get("name", )
                )

                if matching_predictions:
                    matching_predictions.overlay_configuration(
                        configuration=prediction_configuration,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                else:
                    self.predictions.append(
                        DataSourceSpecification.create(
                            data=prediction_configuration,
                            template_manager=template_manager,
                            decoder_type=decoder_type
                        )
                    )

        if 'crosswalks' in configuration:
            crosswalk_configurations = configuration.get("crosswalks")

            if isinstance(crosswalk_configurations, dict):
                crosswalk_configurations = [crosswalk_configurations]

            for configuration in crosswalk_configurations:
                matching_crosswalk = find(
                    self.crosswalks,
                    lambda crosswalk: crosswalk.identities_match(configuration)
                )

                if matching_crosswalk:
                    matching_crosswalk.apply_configuration(
                        configuration=configuration,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                else:
                    self.crosswalks.append(
                        CrosswalkSpecification.create(
                            data=configuration,
                            template_manager=template_manager,
                            decoder_type=decoder_type
                        )
                    )

        thresholds = configuration.get("thresholds")

        if thresholds:
            if isinstance(thresholds, dict):
                thresholds = [thresholds]

            for threshold_specification in thresholds:
                matching_specification = find(
                    self.thresholds,
                    lambda threshold: threshold.identities_match(threshold_specification)
                )

                if matching_specification:
                    matching_specification.apply_configuration(
                        configuration=threshold_specification,
                        template_manager=template_manager,
                        decoder_type=decoder_type
                    )
                else:
                    self.thresholds.append(
                        ThresholdSpecification.create(
                            data=threshold_specification,
                            template_manager=template_manager,
                            decoder_type=decoder_type
                        )
                    )

        scheme_configuration = configuration.get("scheme")

        if scheme_configuration:
            if self.scheme:
                self.scheme.apply_configuration(
                    configuration=configuration,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self.scheme = SchemeSpecification.create(
                    data=configuration,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )


    def validate_self(self) -> typing.Sequence[str]:
        messages = list()

        for observation_source in self.observations:
            messages.extend(observation_source.validate_self())

        for prediction_source in self.predictions:
            messages.extend(prediction_source.validate_self())

        for crosswalk_source in self.crosswalks:
            messages.extend(crosswalk_source.validate_self())

        for threshold_source in self.thresholds:
            messages.extend(threshold_source.validate_self())

        messages.extend(self.scheme.validate_self())

        return messages

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "observations": [specification.to_dict() for specification in self.observations],
            "predictions": [specification.to_dict() for specification in self.predictions],
            "crosswalks": [crosswalk.to_dict() for crosswalk in self.crosswalks],
            "thresholds": [thresholds.to_dict() for thresholds in self.thresholds],
            "scheme": self.scheme.to_dict()
        }

        if self.properties:
            dictionary['properties'] = self.properties

        return dictionary

    @property
    def weight_per_location(self) -> float:
        """
        The maximum value each location can have
        """
        total_threshold_weight = sum([threshold.total_weight for threshold in self.thresholds])

        return total_threshold_weight + self.scheme.total_weight


class EvaluationResults:
    def __init__(
        self,
        instructions: EvaluationSpecification,
        raw_results: typing.Dict[typing.Tuple[str, str], metrics.MetricResults]
    ):
        self._instructions = instructions
        self._original_results = raw_results.copy()
        self._location_map: typing.Dict[str, typing.Dict[str, metrics.MetricResults]] = collections.defaultdict(dict)

        self._total = sum(
            [
                metric_result.scaled_value
                for metric_result in raw_results.values()
                if not numpy.isnan(metric_result.scaled_value)
            ]
        )

        self._maximum_value = sum(
            [
                metric_result.weight
                for metric_result in raw_results.values()
                if not numpy.isnan(metric_result.weight)
            ]
        )

        for (observed_location, predicted_location), metric_result in self._original_results.items():
            self._location_map[observed_location][predicted_location] = metric_result
            self._location_map[predicted_location][observed_location] = metric_result

    def __getitem__(self, item: str) -> typing.Dict[str, metrics.MetricResults]:
        return self._location_map[item]

    def __iter__(self):
        return iter(self._original_results.items())

    def __len__(self):
        return len(self._original_results)

    def __str__(self):
        locations_in_calculations = [
            f"{observation_location} vs. {prediction_location}"
            for (observation_location, prediction_location) in self._original_results.keys()
        ]
        return f"{', '.join(locations_in_calculations)}: {self._total}"

    def to_frames(self, include_metadata: bool = None) -> typing.Dict[str, pandas.DataFrame]:
        """
        Converts two or more dimensional results into a DataFrame

        NOTE: Scalar values, such as the final results, will not be included

        Returns:
            A DataFrame describing the results of all scores, across all thresholds, across all location pairings
        """
        if include_metadata is None:
            include_metadata = False

        frames: typing.Dict[str, pandas.DataFrame] = dict()

        for (observation_location, prediction_location), results in self._original_results.items():
            results_frame = results.to_dataframe(include_metadata=include_metadata)
            results_frame['observed_location'] = observation_location
            results_frame['predicted_location'] = prediction_location
            frames[f"{observation_location} vs. {prediction_location}"] = results_frame

        return frames

    @property
    def performance(self) -> float:
        """
        Returns an aggregate value demonstrating the performance of each location within the evaluation

            n
            Σ   self._original_results.values()[i].scaled_value
          i = 0
        """
        return self._total / self._maximum_value if self._maximum_value else 0.0

    def to_dict(self, include_specification: bool = None) -> typing.Dict[str, typing.Any]:
        """
        Converts the results into a dictionary

        Args:
            include_specification: Whether to include the specifications for how to conduct the evaluation

        Returns:
            The evaluation results in the form of a nested dictionary
        """
        data = dict()

        data['total'] = self._total
        data['performance'] = self.performance
        data['grade'] = self.grade
        data['max_possible_total'] = self.max_possible_value
        data['mean'] = self.mean
        data['median'] = self.median
        data['standard_deviation'] = self.standard_deviation

        data['results'] = list()

        include_specification = bool(include_specification)

        if include_specification:
            data['specification'] = self._instructions.to_dict()

        included_metrics: typing.List[dict] = list()

        for result in self._original_results.values():  # type: metrics.MetricResults
            for _, scores in result:
                for score in scores:
                    if not [metric for metric in included_metrics if metric['name'] == score.metric.name]:
                        included_metrics.append(
                            {
                                "name": score.metric.name,
                                "weight": score.metric.weight,
                                "description": score.metric.get_descriptions()
                            }
                        )

        data['metrics'] = sorted(included_metrics, key=lambda entry: entry['name'])

        for (observation_location, prediction_location), results in self._original_results.items():
            result_data = {
                "observation_location": observation_location,
                "prediction_location": prediction_location,
            }

            result_data.update(results.to_dict())

            data['results'].append(result_data)

        data['results'] = sorted(
            data['results'],
            key=lambda entry: (entry['observation_location'], entry['prediction_location'])
        )

        return data

    @property
    def value(self) -> float:
        """
        The resulting value for the evaluation over all location pairings
        """
        return self._total

    @property
    def instructions(self) -> EvaluationSpecification:
        """
        The specifications that told the system how to evaluate
        """
        return self._instructions

    @property
    def max_possible_value(self) -> float:
        """
        The highest possible value that can be achieved with the given instructions
        """
        return self._maximum_value

    @property
    def grade(self) -> float:
        """
        The total weighted grade percentage result across all location pairings. Scales from 0.0 to 100.0
        """
        return truncate(self.performance * 100.0, 2)

    @property
    def mean(self) -> float:
        """
        The mean total value across all evaluated location pairings
        """
        return float(
            numpy.mean(
                [
                    result.scaled_value / result.weight
                    for result in self._original_results.values()
                ]
            )
        )

    @property
    def median(self) -> float:
        """
        The median total value across all evaluated location pairings
        """
        return float(
            numpy.median(
                [
                    result.scaled_value / result.weight
                    for result in self._original_results.values()
                ]
            )
        )

    @property
    def standard_deviation(self) -> float:
        """
        The standard deviation for result values across all location pairings
        """
        return float(
            numpy.std(
                [
                    result.scaled_value / result.weight
                    for result in self._original_results.values()
                ]
            )
        )

    def __eq__(self, other: "EvaluationResults"):
        return order_dictionary(self.to_dict()) == order_dictionary(other.to_dict())
