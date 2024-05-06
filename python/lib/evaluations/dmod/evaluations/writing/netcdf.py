import typing

import numpy
import pandas
import xarray

import dmod.metrics.metric as metric_functions

from . import writer
from .writer import OutputData
from .. import specification


class NetcdfOutput(writer.OutputData):
    def get_extension(self) -> str:
        if len(self) > 1:
            return ".zip"
        return ".nc"

    def get_content_type(self) -> str:
        if len(self) > 1:
            return "application/zip"
        return "application/x-netcdf"

    def get_bytes(self, index: int = None) -> bytes:
        data = self.get(index)
        return data.to_netcdf()

    def next_bytes(self) -> bytes:
        data = self.next()
        return data.to_netcdf()

    def get(self, index: int = None) -> xarray.Dataset:
        if index is not None and index >= len(self):
            raise IndexError(f"Cannot retrieve output at index {index}. There are only {len(self)} items to read.")

        if index is None:
            index = self._current_index

        return xarray.load_dataset(self._destinations[index])

    def next(self) -> xarray.Dataset:
        if len(self) == 0:
            raise IndexError("There are no datasets to load")
        if self._current_index >= len(self):
            self._current_index = 0

        dataset = xarray.load_dataset(self._destinations[self._current_index])
        self._current_index += 1
        return dataset


class NetcdfWriter(writer.OutputWriter):
    def retrieve_written_output(self, **kwargs) -> OutputData:
        if self.destination is None:
            raise ValueError("Cannot retrieve data that wasn't written to the given destination")

        output_generator = NetcdfOutput(self, **kwargs)
        return output_generator

    @classmethod
    def requires_destination_address_or_buffer(cls) -> bool:
        return True

    @classmethod
    def get_extension(cls) -> str:
        return "nc"

    @classmethod
    def get_format_name(cls) -> str:
        return "netcdf"

    def _to_xarray(self, evaluation_results: specification.EvaluationResults) -> xarray.Dataset:
        result_frames = evaluation_results.to_frames()
        combined_frames = pandas.concat([frame for frame in result_frames.values()])

        del result_frames

        location_data = combined_frames[['observed_location', 'predicted_location']].drop_duplicates()
        threshold_data = combined_frames[['threshold_name', 'threshold_weight']].drop_duplicates()

        coordinates = {
            "location_index": numpy.array([index for index in range(len(location_data))], dtype=numpy.uint32),
            "threshold_index": numpy.array([index for index in range(len(threshold_data.threshold_name))], dtype=numpy.uint8)
        }

        data_variables = {
            "threshold_name": (("threshold_index",), threshold_data.threshold_name),
            "threshold_weight": (("threshold_index",), numpy.array(threshold_data.threshold_weight, dtype=numpy.uint8)),
            "predicted_location": (('location_index',), location_data.predicted_location),
            "observed_location": (('location_index',), location_data.observed_location)
        }

        del location_data

        for metric_name, metric_frame in combined_frames.groupby("metric"):  # type: str, pandas.DataFrame
            weight = int(metric_frame.metric_weight.drop_duplicates().values[0])
            metric_function: metric_functions.scoring.Metric = metric_functions.get_metric(metric_name, weight)
            result_attributes = {
                "long_name": metric_function.get_name(),
                "description": metric_function.get_descriptions(),
                "ideal_value": metric_function.ideal_value,
                "greater_is_better": metric_function.greater_is_better,
                "lower_bound": metric_function.lower_bound,
                "upper_bound": metric_function.upper_bound
            }

            scaled_result_attributes = {
                "long_name": "Scaled " + metric_function.get_name(),
                "description": metric_function.get_descriptions(),
                "ideal_value": weight,
            }
            clean_metric_name = metric_name.replace(" ", "_")
            result_name = f'{clean_metric_name}_result'
            scaled_result_name = f'scaled_{clean_metric_name}_result'
            data_variables[result_name] = (
                ("location_index", "threshold_index"),
                numpy.full(
                        shape=(len(coordinates['location_index']), len(coordinates['threshold_index'])),
                        fill_value=numpy.nan,
                        dtype=numpy.float32
                ),
                result_attributes
            )
            data_variables[scaled_result_name] = (
                ("location_index", "threshold_index"),
                numpy.full(
                        shape=(len(coordinates['location_index']), len(coordinates['threshold_index'])),
                        fill_value=numpy.nan,
                        dtype=numpy.float32
                ),
                scaled_result_attributes
            )

            location_indices = dict()
            threshold_indices = dict()

            for row_index_value, row in metric_frame.iterrows():
                observed_location = row.observed_location
                predicted_location = row.predicted_location
                threshold_name = row.threshold_name

                location_index = None
                if (observed_location, predicted_location) in location_indices:
                    location_index = location_indices[(observed_location, predicted_location)]
                else:
                    for index in coordinates['location_index']:
                        possible_matching_predicted_location = data_variables['predicted_location'][1].iloc[index]
                        possible_matching_observed_location = data_variables['observed_location'][1].iloc[index]

                        observed_locations_match = observed_location == possible_matching_observed_location
                        predicted_locations_match = predicted_location == possible_matching_predicted_location
                        if observed_locations_match and predicted_locations_match:
                            location_indices[(observed_location, predicted_location)] = index
                            location_index = index
                            break

                threshold_index = None
                if threshold_name in threshold_indices:
                    threshold_index = threshold_indices[threshold_name]
                else:
                    for index in coordinates['threshold_index']:
                        if data_variables['threshold_name'][1].iloc[index] == threshold_name:
                            threshold_indices[threshold_name] = index
                            threshold_index = index
                            break

                if location_index is None or threshold_index is None:
                    raise ValueError("Values for locations and thresholds are missing or misaligned")

                data_variables[result_name][1][location_index, threshold_index] = row.result
                data_variables[scaled_result_name][1][location_index, threshold_index] = row.scaled_result

        output = xarray.Dataset(
                coords=coordinates,
                data_vars=data_variables,
                attrs={
                    "result": evaluation_results.value,
                    "max_possible_result": evaluation_results.max_possible_value,
                    "grade": evaluation_results.grade,
                    "mean": evaluation_results.mean,
                    "median": evaluation_results.median,
                    "standard_deviation": evaluation_results.standard_deviation
                }
        )
        return output

    def write(self, evaluation_results: specification.EvaluationResults, buffer: typing.IO = None, **kwargs):
        if self.destination is None and buffer is None:
            raise ValueError("A buffer must be passed in if no destination is declared")

        converted_output = self._to_xarray(evaluation_results)
        responsible_for_buffer = buffer is None

        try:
            if responsible_for_buffer:
                buffer = open(self.destination, 'wb')

            raw_netcdf = converted_output.to_netcdf()

            buffer.write(raw_netcdf)
        finally:
            if responsible_for_buffer and buffer is not None and not buffer.closed:
                buffer.close()
