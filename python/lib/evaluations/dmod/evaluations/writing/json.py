import json
import typing

import numpy
import pandas

import dmod.metrics.metric as metrics

from ..specification import EvaluationResults
from .writer import OutputWriter
from .writer import OutputData


class JSONOutput(OutputData):
    def get_extension(self) -> str:
        if len(self) > 1:
            return "zip"
        return "json"

    def get_content_type(self) -> str:
        if len(self) > 1:
            return "application/zip"
        return "application/json"

    def get_bytes(self, index: int = None) -> bytes:
        data = self.get(index)
        return json.dumps(data, indent=4).encode()

    def next_bytes(self) -> bytes:
        data = self.next()
        return json.dumps(data, indent=4).encode()

    def get(self, index: int = None) -> dict:
        if index is not None and index >= len(self):
            raise IndexError(f"Cannot retrieve output at index {index}. There are only {len(self)} items to read.")

        if index is None:
            index = self._current_index

        with open(self._destinations[index], 'r') as data_file:
            return json.load(data_file)

    def next(self) -> dict:
        if self._current_index < len(self._destinations):
            with open(self._destinations[self._current_index], 'rb') as output_file:
                data = json.load(output_file)

            self._current_index += 1
            return data
        else:
            raise StopIteration()


class JSONWriter(OutputWriter):
    def retrieve_written_output(self, **kwargs) -> OutputData:
        if self.destination is None:
            raise ValueError("Cannot retrieve data that wasn't written to the given destination")

        output_generator = JSONOutput(self, **kwargs)
        return output_generator

    @classmethod
    def requires_destination_address_or_buffer(cls) -> bool:
        return True

    @classmethod
    def get_format_name(cls) -> str:
        return "json"

    @classmethod
    def get_extension(cls) -> str:
        return "json"

    def _results_to_dictionary(
            self,
            evaluation_results: EvaluationResults,
            include_specification: bool = None
    ) -> typing.Dict[str, typing.Any]:
        """
        Converts the results into a dictionary

        Args:
            include_specification: Whether to include the specifications for how to conduct the evaluation

        Returns:
            The evaluation results in the form of a nested dictionary
        """
        data = dict()

        data['total'] = evaluation_results.value
        data['grade'] = "{:.2f}%".format(evaluation_results.grade)
        data['max_possible_total'] = evaluation_results.max_possible_value
        data['mean'] = evaluation_results.mean
        data['median'] = evaluation_results.median
        data['standard_deviation'] = evaluation_results.standard_deviation

        data['results'] = list()

        include_specification = bool(include_specification)

        if include_specification:
            data['specification'] = evaluation_results.instructions.to_dict()

        data['metrics'] = list()

        for metric_function in evaluation_results.instructions.scheme.metric_functions:
            found_metric = metrics.get_metric(metric_function.name, metric_function.weight)
            data['metrics'].append({
                "name": found_metric.name,
                "description": found_metric.get_descriptions(),
                "weight": found_metric.weight
            })

        for (observation_location, prediction_location), results in evaluation_results:
            result_data = {
                "observation_location": observation_location,
                "prediction_location": prediction_location,
                'total': results.total,
                "results": list()
            }

            for score_threshold, scores in results:  # type: metrics.Threshold, typing.List[metrics.scoring.Score]
                threshold_results: typing.Dict[str, typing.Any] = {
                    "name": score_threshold.name,
                    "weight": score_threshold.weight,
                    "scores": list(),
                }

                if isinstance(score_threshold.value, pandas.DataFrame) \
                        and len(score_threshold.value) == 1 \
                        and len(score_threshold.value.keys()) == 1:
                    first_column = [key for key in score_threshold.value.keys()][0]
                    threshold_value = float(score_threshold.value[first_column].values[0])
                elif isinstance(score_threshold.value, pandas.Series) and len(score_threshold.value) == 1:
                    threshold_value = float(score_threshold.value.values[0])
                elif isinstance(score_threshold.value, typing.Sequence) and len(score_threshold.value) == 1:
                    threshold_value = float(score_threshold.value[0])
                elif isinstance(score_threshold.value, (pandas.DataFrame, pandas.Series, typing.Sequence)):
                    threshold_value = "varying"
                else:
                    threshold_value = float(score_threshold.value)

                threshold_results['threshold_value'] = threshold_value

                threshold_total = 0
                maximum_value = 0

                for score in scores:
                    threshold_total += 0 if numpy.isnan(score.scaled_value) else score.scaled_value
                    maximum_value += score.metric.weight
                    score_data = {
                        "metric": score.metric.name,
                        "weight": score.metric.weight,
                        "value": None if numpy.isnan(score.value) else score.value,
                        "scaled_value": None if numpy.isnan(score.scaled_value) else score.scaled_value
                    }

                    threshold_results['scores'].append(score_data)

                total_factor = threshold_total / maximum_value
                threshold_results['result'] = threshold_total
                threshold_results['maximum_result'] = maximum_value
                threshold_results['scaled_result'] = score_threshold.weight * total_factor
                result_data['results'].append(threshold_results)

            data['results'].append(result_data)

        return data

    def write(
            self,
            evaluation_results: EvaluationResults,
            buffer: typing.IO = None,
            include_specification: bool = None,
            **kwargs
    ):
        if self.destination is None and buffer is None:
            raise ValueError("A buffer must be passed in if no destination is declared")

        data_to_write: typing.Dict[str, typing.Hashable] = self._results_to_dictionary(
                evaluation_results,
                include_specification
        )

        indent = kwargs.get("indent", 4)

        buffer_was_created_here = buffer is None

        try:
            if buffer is None:
                buffer = open(self.destination, 'w')

            json.dump(data_to_write, buffer, indent=indent)
        finally:
            if buffer_was_created_here and buffer is not None:
                buffer.close()
