import typing

import pandas

import dmod.metrics as metrics

from . import specification
from . import crosswalk
from . import data_retriever
from . import threshold
from . import measurement_units


class UnitConverter:
    """
    A callable that converts the value from one column in a pandas Series from its meaurement unit to
    that of another measurement unit
    """
    def __init__(self, value_field: str, from_unit_field: str, to_unit_field: str):
        self.__value_field = value_field
        self.__from_unit_field = from_unit_field
        self.__to_unit_field = to_unit_field

    def _conversion(self, row):
        """
        Helper function used to convert the values in a singular row

        Args:
            row: A row from a data source

        Returns:
            A value converted from one measurement unit to another
        """
        if row[self.__from_unit_field] == row[self.__to_unit_field]:
            return row[self.__value_field]

        return measurement_units.convert(
                row[self.__value_field],
                row[self.__from_unit_field],
                row[self.__to_unit_field]
        )

    def __call__(self, rows_to_convert: pandas.Series, *args, **kwargs) -> float:
        return rows_to_convert.apply(
                self._conversion,
                axis=1
        )


class Evaluator:
    def __init__(self, instructions: specification.EvaluationSpecification):
        self._instructions = instructions

        self._observed_location_field: typing.Optional[str] = None
        self._predicted_location_field: typing.Optional[str] = None
        self._observed_value_field: typing.Optional[str] = None
        self._predicted_value_field: typing.Optional[str] = None
        self._observed_xaxis: typing.Optional[str] = None
        self._predicted_xaxis: typing.Optional[str] = None

        self._set_field_names()
        self._converter = UnitConverter(self._predicted_value_field, "unit_prediction", "unit_observation")

    @property
    def instructions(self) -> specification.EvaluationSpecification:
        """
        The specification telling the Evaluator what to do
        """
        return self._instructions

    @property
    def maximum_score(self) -> float:
        total_threshold_weights = sum([configured_threshold for configured_threshold in self._instructions.thresholds])
        total_metric_weights = sum([metric.weight for metric in self._instructions.scheme.metric_functions])

        weight_per_location = total_metric_weights + total_threshold_weights
        return weight_per_location

    def _set_field_names(self):
        error_messages = list()

        observed_xaxis = None
        observed_value_field = None

        for observation_definition in self._instructions.observations:
            xaxis = observation_definition.x_axis
            value_field = observation_definition.value_field

            observed_xaxis_is_mismatched = observed_xaxis is not None and observed_xaxis != xaxis
            observed_value_field_is_mismatched = observed_value_field is not None
            observed_value_field_is_mismatched &= observed_value_field != value_field

            if observed_xaxis_is_mismatched:
                error_messages.append(f"Cannot collect observation data - the xaxis definition is not uniform")

            if observed_value_field_is_mismatched:
                error_messages.append(f"Cannot collect observation data - value label definitions are not uniform")

            if observed_xaxis_is_mismatched or observed_value_field_is_mismatched:
                break

            observed_xaxis = xaxis
            observed_value_field = value_field

        self._observed_xaxis = observed_xaxis
        self._observed_value_field = observed_value_field

        predicted_xaxis = None
        predicted_value_field = None

        for prediction_definition in self._instructions.predictions:
            xaxis = prediction_definition.x_axis
            value_field = prediction_definition.value_field

            predicted_xaxis_is_mismatched = predicted_xaxis is not None and predicted_xaxis != xaxis
            predicted_value_field_is_mismatched = predicted_value_field is not None
            predicted_value_field_is_mismatched &= predicted_value_field != value_field

            if predicted_xaxis_is_mismatched:
                error_messages.append(f"Cannot collect prediction data - the xaxis definition is not uniform")

            if predicted_value_field_is_mismatched:
                error_messages.append(f"Cannot collect prediction data - value label definitions are not uniform")

            if predicted_xaxis_is_mismatched or predicted_value_field_is_mismatched:
                break

            predicted_xaxis = xaxis
            predicted_value_field = value_field

        self._predicted_xaxis = predicted_xaxis or observed_xaxis
        self._predicted_value_field = predicted_value_field or observed_value_field

        observed_location_label = None
        predicted_location_label = None

        for crosswalk_definition in self._instructions.crosswalks:
            observed_is_mismatched = observed_location_label is not None
            observed_is_mismatched &= crosswalk_definition.observation_field_name != observed_location_label

            predicted_is_mismatched = predicted_location_label is not None
            predicted_is_mismatched &= crosswalk_definition.prediction_field_name != predicted_location_label

            if observed_is_mismatched and predicted_is_mismatched:
                raise ValueError(
                        f"Crosswalk cannot be compiled - new field names for observed locations and predicted "
                        f"locations ({crosswalk_definition.observation_field_name} and "
                        f"{crosswalk_definition.prediction_field_name}) don't match previous "
                        f"field names ({observed_location_label} and {predicted_location_label})"
                )
            elif observed_is_mismatched:
                raise ValueError(
                        f"Crosswalk cannot be compiled - the new field name for observed locations "
                        f"({crosswalk_definition.observation_field_name}) does not match the previous "
                        f"field name ({observed_location_label})"
                )
            elif predicted_is_mismatched:
                raise ValueError(
                        f"Crosswalk cannot be compiled - the new field name for prediction locations "
                        f"({crosswalk_definition.prediction_field_name}) does not match the previous "
                        f"field name ({predicted_location_label})"
                )

            observed_location_label = crosswalk_definition.observation_field_name
            predicted_location_label = crosswalk_definition.prediction_field_name

        self._observed_location_field = observed_location_label
        self._predicted_location_field = predicted_location_label or observed_location_label

    def evaluate(self) -> specification.EvaluationResults:
        """
        Uses stored Evaluator data to score predictions compared to observations

        Returns:
            Scoring results tied to crosswalk identifiers
        """
        crosswalk_data = self.get_crosswalk()
        data_to_evaluate = self.get_data_to_evaluate(crosswalk_data)
        data_to_evaluate = self.normalize_values(data_to_evaluate)
        thresholds = self.get_thresholds()
        scores = self.score(data_to_evaluate, thresholds)
        evaluation_results = specification.EvaluationResults(self._instructions, scores)
        return evaluation_results

    def get_crosswalk(self) -> pandas.DataFrame:
        """
        Gathers crosswalk data as specified via the instructions

        Returns:
            A DataFrame describing the mapping between observation and predicted locations
        """
        crosswalk_data: typing.Optional[pandas.DataFrame] = None

        for crosswalk_definition in self._instructions.crosswalks:
            found_crosswalk = crosswalk.get_data(crosswalk_definition)

            if found_crosswalk is None or found_crosswalk.empty:
                continue

            if crosswalk_data is None:
                crosswalk_data = found_crosswalk
            else:
                crosswalk_data = pandas.concat([crosswalk_data, found_crosswalk])

        if crosswalk_data is None or crosswalk_data.empty:
            raise ValueError("No crosswalk data could be found")

        return crosswalk_data

    def get_data_to_evaluate(self, crosswalk_data: pandas.DataFrame) -> pandas.DataFrame:
        """
        Uses internal specification and discovered crosswalk data to organize what data to evaluate and how

        Args:
            crosswalk_data:
                A DataFrame describing what locations bind together
        Returns:
            A DataFrame of observed and predicted data matched together for evaluation
        """
        observations: typing.Optional[pandas.DataFrame] = None

        for observation_definition in self._instructions.observations:
            found_observations = data_retriever.read(observation_definition)

            if found_observations is None or found_observations.empty:
                continue

            if observations is None:
                observations = found_observations
            else:
                observations = pandas.concat([observations, found_observations])

        predictions: typing.Optional[pandas.DataFrame] = None

        for prediction_definition in self._instructions.predictions:
            found_predictions = data_retriever.read(prediction_definition)

            if found_predictions is None or found_predictions.empty:
                continue

            if predictions is None:
                predictions = found_predictions
            else:
                predictions = pandas.concat([predictions, found_predictions])

        data = observations.merge(right=crosswalk_data, on=self._observed_location_field)
        data = data.merge(
                right=predictions,
                left_on=[self._predicted_location_field, self._observed_xaxis],
                right_on=[self._predicted_location_field, self._predicted_xaxis],
                suffixes=('_observation', '_prediction')
        )

        thresholds_with_rules = [
            threshold_spec
            for threshold_spec in self._instructions.thresholds
            if bool(threshold_spec.application_rules)
        ]

        for threshold_specification in thresholds_with_rules:
            observation_rule = threshold_specification.application_rules.observation_field
            prediction_rule = threshold_specification.application_rules.prediction_field

            index_fields = list()

            if observation_rule and observation_rule.name not in data.keys():
                def conversion_function(column_name_and_value: pandas.Series):
                    """
                    Converts a series of column names vs values to the desired data type

                    Args:
                        column_name_and_value:
                            A pandas Series mapping column names to values
                    Returns:
                        The converted value
                    """
                    converted_value = observation_rule.to_datatype([value for value in column_name_and_value])
                    return converted_value

                data[observation_rule.name] = data[observation_rule.path].apply(conversion_function, axis=1)
                index_fields.append(observation_rule.name)

            if prediction_rule and prediction_rule.name not in data.keys():
                def conversion_function(column_name_and_value: pandas.Series):
                    """
                    Converts a series of column names vs values to the desired data type

                    Args:
                        column_name_and_value:
                            A pandas Series mapping column names to values
                    Returns:
                        The converted value
                    """
                    converted_value = prediction_rule.to_datatype([value for value in column_name_and_value])
                    return converted_value

                data[prediction_rule.name] = data[prediction_rule.path].apply(conversion_function, axis=1)
                index_fields.append(prediction_rule.name)

            data = data.set_index(keys=index_fields, drop=True)

        return data

    def normalize_values(self, data_to_evaluate: pandas.DataFrame) -> pandas.DataFrame:
        """
        Converts passed data into a common form for evaluation

        For example: You can't readily compare data measured in cubic meters per second to data measured in
        thousands of cubic feet per second, so they are converted into a common measurement unit

        Args:
            data_to_evaluate:
                Matched data whose rows will be compared
        Returns:
            A version of the passed `data_to_evaluate` whose observed and predicted values are ready to compare
        """
        if data_to_evaluate['unit_prediction'].equals(data_to_evaluate['unit_observation']):
            return data_to_evaluate

        related_keys = [self._predicted_value_field, "unit_prediction", "unit_observation"]
        data_to_evaluate[self._predicted_value_field] = self._converter(data_to_evaluate[related_keys])

        data_to_evaluate["unit_prediction"] = data_to_evaluate["unit_observation"]

        return data_to_evaluate

    def get_thresholds(self) -> typing.Dict[str, typing.Sequence[metrics.Threshold]]:
        """
        Generates a mapping between all locations to be evaluated and the thresholds required to do so

        Returns:
            A mapping between all locations to be evaluated and a series of thresholds used to do so
        """
        thresholds: typing.Dict[str, typing.List[metrics.Threshold]] = dict()
        for threshold_definition in self._instructions.thresholds:
            found_thresholds = threshold.get_thresholds(threshold_definition)

            for location, threshold_list in found_thresholds.items():
                if location not in thresholds:
                    thresholds[location] = list()
                thresholds[location].extend(threshold_list)

        return thresholds

    def score(
            self,
            data_to_evaluate: pandas.DataFrame,
            thresholds: typing.Dict[str, typing.Sequence[metrics.Threshold]]
    ) -> typing.Dict[typing.Tuple[str, str], metrics.MetricResults]:
        """
        Performs the evaluation

        Args:
            data_to_evaluate:
                The values ready to compare
            thresholds:
                The thresholds used to compare values
        Returns:
            A mapping between the locations being evaluated and the results of the metrics performed on them
        """
        scheme = self._instructions.scheme.generate_scheme()

        groupby_columns = [
            self._observed_location_field,
            self._predicted_location_field
        ]

        scores: typing.Dict[typing.Tuple[str, str], metrics.MetricResults] = dict()

        for identifiers, group in data_to_evaluate.groupby(by=groupby_columns):  # type: tuple, pandas.DataFrame
            location_identifier = identifiers[0]
            location_thresholds = thresholds.get(location_identifier)
            if location_thresholds:
                location_scores = scheme.score(
                        group,
                        self._observed_value_field,
                        self._predicted_value_field,
                        location_thresholds
                )
                scores[identifiers] = location_scores

        return scores


def evaluate(definition: specification.EvaluationSpecification) -> specification.EvaluationResults:
    evaluator = Evaluator(definition)
    return evaluator.evaluate()
