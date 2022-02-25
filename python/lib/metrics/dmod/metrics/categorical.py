"""
Defines methods and structures that facilitate the evaluation of categorical metrics,
such as Probability of Detection and False alarm ratio

Attributes:
    PANDAS_DATA: A type indicating either a pandas DataFrame or a pandas Series
    NUMBER: A type indicating either a floating point or an integer
"""
import typing
import math

import pandas
import numpy

from ..metrics.threshold import Threshold

PANDAS_DATA = typing.Union[pandas.DataFrame, pandas.Series]

NUMBER = typing.Union[float, int]


def value_hit(observation: float, prediction: float) -> bool:
    return not numpy.isnan(observation) and not numpy.isnan(prediction)


def value_missed(observation: float, prediction: float) -> bool:
    return not numpy.isnan(observation) and numpy.isnan(prediction)


def nothing_happened(observation: float, prediction: float) -> bool:
    return numpy.isnan(observation) and numpy.isnan(prediction)


def value_was_a_false_positive(value: float, prediction: float) -> bool:
    return numpy.isnan(value) and not numpy.isnan(prediction)


def categorical_metric(
        minimum: float = -math.inf,
        maximum: float = math.inf,
        ideal: float = None,
        failure: float = None
):
    """
    Mixin used to attach several important attributes to categorical metrics used for interpretion after the fact.

    This adds:

        * is_metric: whether or not the passed object is a function (will always be True)
        * maximum: The maximum allowable value for the metric
        * minimum: The minimum allowable value for the metric
        * ideal: The value for the metric that indicates a perfect result
        * failure: A value indicating a total failure that renders all adjacent scores moot
        * lower_bounded: Whether or not there is a lower bound for the metric
        * upper_bounded: Whether or not there is a upper bound for the metric
        * partially_bounded: Whether or not there is a mutually exclusive upper or lower bound
        * bounded: Whether or not there are any bounds at all

    Args:
        minimum: The minimum possible value for the metric
        maximum: The maximum possible value for the metric
        ideal: The desired value for the metric
        failure: A value indicating a total failure for the metric

    Returns:
        The updated metric function

    """
    def inner(function):
        """
        Attaches attributes to the passed in function

        Args:
            function: The function to attach attributes to

        Returns:
            The updated metric function

        """
        setattr(function, "is_metric", True)
        setattr(function, 'maximum', maximum)
        setattr(function, 'minimum', minimum)
        setattr(function, 'ideal', ideal)
        setattr(function, 'failure', failure)
        setattr(function, 'lower_bounded', math.isfinite(minimum))
        setattr(function, 'upper_bounded', math.isfinite(maximum))
        setattr(function, 'partially_bounded', math.isfinite(minimum) ^ math.isfinite(maximum))
        setattr(function, 'bounded', math.isfinite(minimum) or math.isfinite(maximum))
        setattr(function, 'scale_reversed', minimum > maximum)
        return function

    return inner


class CategoricalMetricMetadata(object):
    """
    Class used to highlight metadata about a specific categorical metric within a truth table

    Attributes:
        name: The name of the categorical metric
        maximum: The maximum possible value for the metric
        minimum: The minimum possible value for the metric
        ideal: The desired value for the metric
        failure: A value indicating a failure condition for the metric
    """
    def __init__(self, name: str, maximum: NUMBER, minimum: NUMBER, ideal: NUMBER, failure: NUMBER):
        """
        Constructor

        Args:
            name: The name of the metric
            maximum: The maximum value for the metric
            minimum: The minimum value for the metric
            ideal: The desired value for the metric
            failure: A value indicating a failure condition for the metric
        """
        self.__name = name
        self.__maximum = maximum
        self.__minimum = minimum
        self.__ideal = ideal
        self.__failure = failure

    @property
    def name(self) -> str:
        """
        Returns:
            The name of the categorical metric
        """
        return self.__name

    @property
    def maximum(self) -> NUMBER:
        """
        Returns:
            The maximum value of the categorical metric
        """
        return self.__maximum

    @property
    def minimum(self) -> NUMBER:
        """
        Returns:
            The minimum value of the categorical metric
        """
        return self.__minimum

    @property
    def ideal(self) -> NUMBER:
        """
        Returns:
            The desired value of the categorical metric
        """
        return self.__ideal

    @property
    def failure(self) -> NUMBER:
        """
        Returns:
            A value that is considered to be an utter failure for the metric
        """
        return self.__failure

    @property
    def lower_bounded(self) -> bool:
        """
        Returns:
            Whether or not the metric has a lower bound
        """
        return math.isfinite(self.__minimum)

    @property
    def upper_bounded(self) -> bool:
        """
        Returns:
            Whether or not the metric has an upper bound
        """
        return math.isfinite(self.__maximum)

    @property
    def partially_bounded(self) -> bool:
        """
        Returns:
            Whether or not the metric has a mutually exclusive bound
        """
        return math.isfinite(self.__minimum) ^ math.isfinite(self.__maximum)

    @property
    def bounded(self) -> bool:
        """
        Returns:
            Whether or not there is at least a single bound
        """
        return math.isfinite(self.__minimum) or math.isfinite(self.__maximum)

    @property
    def scale_is_reversed(self) -> bool:
        """
        Returns:
            Whether or not a smaller value is preferrable to a larger value
        """
        return self.__minimum > self.__maximum


class TruthTable(object):
    """
    Represents and calculates the categorical metrics for a single threshold
    """
    @classmethod
    def metrics(cls) -> typing.Iterable[str]:
        """
        Returns:
            A collection of the names of every categorical metric that may be derived from the truth table
        """
        # Go through every item attached to the class and gather the names of everything
        # that has been decorated by the `categorical_metric` mixin
        categorical_metrics = {
            key: value
            for key, value in cls.__dict__.items()
            if hasattr(value, 'is_metric')
               and getattr(value, 'is_metric')
        }
        
        return [key for key in categorical_metrics.keys()]

    @classmethod
    def get_metric_metadata(cls, metric_name: str) -> CategoricalMetricMetadata:
        """
        Forms basic metadata about a given metric

        Args:
            metric_name: The name of the metric to get data for

        Returns:
            A `CategoricalMetricMetadata` object bearing the metadata for the function in an easy to access format
        """
        if metric_name not in cls.metrics():
            raise ValueError(f"'{metric_name}' is not a valid metric.")

        metric_function = getattr(cls, metric_name)
        clean_metric_name = metric_name.replace("_", " ").title()

        return CategoricalMetricMetadata(
            name=clean_metric_name,
            maximum=metric_function.maximum,
            minimum=metric_function.minimum,
            ideal=metric_function.ideal,
            failure=metric_function.failure
        )

    def __init__(self, observations: pandas.Series, predictions: pandas.Series, threshold: Threshold):
        """
        Constructor

        Args:
            observations: An ordered series of values representing all observations used to form the truth table
            predictions: An ordered series of values representing all predictions used to form the truth table
            threshold: The threshold used to indicate something that might constitute a notable event
        """
        self.__name = threshold.name or "Unknown"
        self.__threshold = threshold
        """
        Create a DataFrame with four columns:
            * observation_counts: The value of the observation if it fits the threshold, nan Otherwise
            * prediction_counts: The value of the prediction if it fits the threshold, nan otherwise
            * observations: All passed observed values
            * predictions: All passed simulated values
        """
        matches = pandas.DataFrame(
            {
                "observation_counts": threshold(observations),
                "prediction_counts": threshold(predictions),
                "observations": observations,
                "predictions": predictions
            }
        )

        self.__pairs = matches

        # Derive the four cells of the truth table
        matches['hit'] = matches.apply(
            lambda row: value_hit(row['observation_counts'], row['prediction_counts']),
            axis=1
        )
        matches['true_negative'] = matches.apply(
            lambda row: nothing_happened(row['observation_counts'], row['prediction_counts']),
            axis=1
        )
        matches['false_positive'] = matches.apply(
            lambda row: value_was_a_false_positive(row['observation_counts'], row['prediction_counts']),
            axis=1
        )
        matches['miss'] = matches.apply(
            lambda row: value_missed(row['observation_counts'], row['prediction_counts']),
            axis=1
        )

        self.__size = len(matches)

        # Store evaluated parameters so they don't have to be evaluated multiple times
        self.__observation_had_activity = len(matches[matches.observation_counts.notna()]) > 0
        self.__predictions_had_activity = len(matches[matches.prediction_counts.notna()]) > 0

        self.__hits = len(matches[matches.hit == True])
        self.__true_negatives = len(matches[matches.true_negative == True])
        self.__false_positives = len(matches[matches.false_positive == True])
        self.__misses = len(matches[matches.miss == True])

        self.__positives = self.__hits + self.__misses
        self.__negatives = self.__false_positives + self.__true_negatives
        self.__predicted_positives = self.__hits + self.__false_positives
        self.__predicted_negatives = self.__misses + self.__true_negatives

        self.__probability_of_detection = numpy.nan
        self.__false_alarm_ratio = numpy.nan
        self.__frequency_bias = numpy.nan
        self.__accuracy = numpy.nan
        self.__equitable_threat_score = numpy.nan
        self.__precision = numpy.nan
        self.__general_skill = numpy.nan
        self.__critical_success_index = numpy.nan

        # TODO: Change this to be a measure of information density
        self.__usefull = self.__observation_had_activity or self.__predictions_had_activity

    @categorical_metric(minimum=0.0)
    def hits(self) -> int:
        """
        Returns:
            The number of times both the observation AND the prediction fit within the threshold
        """
        return self.__hits

    @categorical_metric(minimum=0.0)
    def misses(self) -> int:
        """
        Returns:
            The number of times the observation fit within the threshold but the prediction did not
        """
        return self.__misses

    @categorical_metric(minimum=0.0)
    def false_positives(self) -> int:
        """
        Returns:
            The number of times the prediction fit within the threshold but the observation did not
        """
        return self.__false_positives

    @categorical_metric(minimum=0.0)
    def true_negatives(self) -> int:
        """
        Returns:
            The number of times neither the observation nor the prediction fit within the threshold
        """
        return self.__true_negatives

    @property
    def observation_had_activity(self) -> bool:
        """
        Returns:
            Whether or not any sort of activity in the set of observations fit within the threshold
        """
        return self.__observation_had_activity

    @property
    def predictions_had_activity(self) -> bool:
        """
        Returns:
            Whether or not any sort of activity in the set of predictions fit within the threshold
        """
        return self.__predictions_had_activity

    @property
    def name(self) -> str:
        """
        Returns:
            The name of the truth table
        """
        return self.__name

    @categorical_metric(minimum=0.0, maximum=1.0, ideal=1.0, failure=0.0)
    def probability_of_detection(self) -> float:
        """
        Calculates the chances that the predictions fit within the threshold when the observations did

        This is only calculated once, on demand

        Returns:
            The probability that the model would correctly cross the threshold when the observation does
        """
        if not numpy.isnan(self.__probability_of_detection):
            return self.__probability_of_detection

        top = self.__hits
        bottom = self.__positives

        if bottom == 0:
            return numpy.nan

        self.__probability_of_detection = top / bottom

        return self.__probability_of_detection

    @categorical_metric(minimum=0.0, maximum=1.0, ideal=0.0, failure=1.0)
    def false_alarm_ratio(self) -> float:
        """
        Calculates the chances that the predictions fit within the threshold when the observation doesn't

        This is only calculated once, on demand

        Returns:
            The probability that the predictions fit within the threshold when the observation doesn't
        """
        if not numpy.isnan(self.__false_alarm_ratio):
            return self.__false_alarm_ratio

        top = self.__false_positives
        bottom = self.__hits + self.__false_positives

        if bottom == 0:
            return numpy.nan

        self.__false_alarm_ratio = top / bottom

        return self.__false_alarm_ratio

    @categorical_metric(minimum=0, maximum=math.inf, ideal=1.0)
    def frequency_bias(self) -> float:
        """
        Calculates the ratio between the number of times the predictions fit within the threshold and the number of
        times the observations fit within the threshold

        This is only calculated once, on demand

        Returns:
            the ratio between the number of times the predictions fit within the threshold and the number of
            times the observations fit within the threshold
        """
        if not numpy.isnan(self.__frequency_bias):
            return self.__frequency_bias

        top = self.__hits + self.__false_positives
        bottom = self.__hits + self.__misses

        if bottom == 0:
            return numpy.nan

        self.__frequency_bias = top / bottom

        return self.__frequency_bias

    @categorical_metric(minimum=0.0, maximum=1.0, ideal=1.0)
    def critical_success_index(self) -> float:
        if not numpy.isnan(self.__critical_success_index):
            return self.__critical_success_index

        denominator = self.__hits + self.__misses + self.__false_positives

        if denominator == 0:
            return numpy.nan

        self.__critical_success_index = self.__hits / denominator

        return self.__critical_success_index

    @categorical_metric(minimum=0.0, maximum=1.0, ideal=1.0)
    def accuracy(self) -> float:
        """
        Calculates the rate that the predictions made the right call when saying that a value fell
        within or without the threshold

        Returns:
            The rate that the predictions made the right call when saying that a value fell
            within or without the threshold
        """
        if not numpy.isnan(self.__accuracy):
            return self.__accuracy

        if not (self.observation_had_activity or self.predictions_had_activity):
            return numpy.nan

        top = self.__hits + self.__true_negatives
        bottom = self.__size

        if bottom == 0:
            return numpy.nan

        self.__accuracy = top / bottom

        return self.__accuracy

    @categorical_metric(minimum=0.0, maximum=1.0, ideal=1.0, failure=0.0)
    def equitable_threat_score(self) -> float:
        """
        Calculates how well did the predicted values accurately fit within the threshold, accounting for hits
        due to chance

        This is calculated once, on demand

        Returns:
            How well did the predicted values accurately fit within the threshold, accounting for hits
            due to chance
        """
        if not numpy.isnan(self.__equitable_threat_score):
            return self.__equitable_threat_score

        random_hit_top = (self.__hits + self.__misses) * (self.__hits + self.__false_positives)
        random_hit_bottom = self.__size

        if random_hit_bottom == 0:
            return numpy.nan

        random_hits = random_hit_top / random_hit_bottom

        top = self.__hits - random_hits
        bottom = self.__hits + self.__misses + self.__false_positives - random_hits

        if bottom == 0:
            return numpy.nan

        self.__equitable_threat_score = top / bottom

        return self.__equitable_threat_score

    @categorical_metric(minimum=0.0, maximum=1.0, failure=0.0, ideal=1.0)
    def general_skill(self) -> float:
        """
        Calculates the the accuracy of the forecast relative to that of random chance, implemented via the
        Heidke Skill Score

        This is calculated once, on demand

        Returns:
            The accuracy of the forecast relative to that of random chance
        """
        if not numpy.isnan(self.__general_skill):
            return self.__general_skill

        # This is the Heidke skill
        top = (self.__hits * self.__true_negatives) - (self.__misses * self.__false_positives)
        top *= 2

        bottom = (self.__hits + self.__misses) * (self.__misses + self.__true_negatives)
        bottom += (self.__hits + self.__false_positives) * (self.__false_positives + self.__true_negatives)

        if bottom == 0:
            return numpy.nan

        self.__general_skill = top / bottom

        return self.__general_skill

    @categorical_metric(minimum=0.0, maximum=1.0, ideal=1.0)
    def precision(self) -> float:
        if not numpy.isnan(self.__precision):
            return self.__precision

        top = self.__hits
        bottom = self.__predicted_positives

        if bottom == 0:
            return numpy.nan

        self.__precision = top / bottom

        return self.__precision

    @property
    def threshold(self) -> Threshold:
        """
        The threshold that determines when something of note happens
        """
        return self.__threshold

    @property
    def weight(self) -> float:
        """
        The numerical weight expressing the significance of the table due to the significance of the threshold
        """
        return self.__threshold.weight

    @property
    def pairs(self) -> pandas.DataFrame:
        """
        TODO: Determine if this is necessary or an unneccessary memory sink

        Returns:
            The data used to calculate the truth table statistics
        """
        return self.__pairs.copy()

    @property
    def is_useful(self) -> bool:
        """
        Tells whether or not there was any useful information in this table or not.

        The table could report an absolutely perfect probability of detection and false alarm ratio, but that doesn't
        tell you much if no data fit within the threshold

        The table is deemed useful if any sort of data was detected within the threshold

        Returns:
            Whether or not there was any useful information caught in this table or not
        """
        return self.__usefull

    @property
    def usefulness(self) -> float:
        """
        Presents the numerical degree to how useful this table is

        TODO: Make this a function of information density

        Returns:
            The numerical degree to how useful this table is
        """
        return self.weight if self.is_useful else 0


class TruthTables(object):
    """
    A collection of truth tables organized by threshold
    """
    def __init__(
            self,
            observations: pandas.Series = None,
            predictions: pandas.Series = None,
            thresholds: typing.Iterable[Threshold] = None,
            tables: typing.Iterable[TruthTable] = None,
            weight: float = None,
    ):
        """
        Constructor

        NOTE: The weight is relative to other TruthTables and differs from the weights of the thresholds.

        Args:
            observations: The observations used to form each underlying table
            predictions: The predicted values used to form each underlying table
            thresholds: The thresholds used to define what does and does not make a table
            tables: An optional collection of premade tables to use
            weight: The relative significance of the data in the table. The value is 1 if none is passed.
                Must be either None or a positive number
        """
        if weight is not None and weight <= 0:
            raise ValueError(
                f"If defined, the weight of this truth table must be greater than 0; the passed weight was {weight}"
            )

        self.__tables: typing.Dict[str, TruthTable] = dict()

        has_usable_observations = observations is not None and isinstance(observations, pandas.Series)
        has_usable_predictions = predictions is not None and isinstance(predictions, pandas.Series)
        has_usable_thresholds = thresholds is not None and len([val for val in thresholds]) > 0

        if has_usable_observations and has_usable_predictions and has_usable_thresholds:
            for threshold in thresholds:
                self.create_table(observations, predictions, threshold)

        if tables is not None:
            for table in tables:
                self.add_table(table)

        if len(self.__tables) == 0:
            raise ValueError("No tables are available to provide metrics for")

        self.__weight = weight or 1

        self.__usefullness = numpy.nan

    def create_table(
            self,
            observations: pandas.Series,
            predictions: pandas.Series,
            threshold: Threshold
    ) -> "TruthTables":
        """
        Builds a new truth table and adds it to the collection of tables

        Args:
            observations: The observations to use to act as the truth values for the table
            predictions: The predicted values used to form the metrics for the table
            threshold: The threshold used to determine the criteria for what a hit or miss is

        Returns:
            The updated TruthTables instance
        """
        table = TruthTable(observations, predictions, threshold)
        return self.add_table(table)

    def add_table(self, table: TruthTable) -> "TruthTables":
        """
        Adds a new table to the collection.

        The table will be accessible by subscripting and by invoking the name of the table as an attribute
        on the collection

        For instance:
            >>> tables.add_table(table)
            >>> print(table.name)
            Example
            >>> print(tables['Example'].name)
            Example
            >>> print(tables.Example.name)
            Example

        NOTE: Only tables with whose name is a valid identifier will be added as an attribute

        Args:
            table: The truth table to add

        Returns:
            The updated TruthTables instance
        """
        if table.name in self.__tables:
            raise ValueError(
                f"There is already a truth table named '{table.name}' in this set of truth tables"
            )

        self.__tables[table.name] = table

        if table.threshold.name.isidentifier():
            setattr(self, table.name, table)

        self.__usefullness = numpy.nan

        return self

    @property
    def weight(self) -> float:
        """
        The relative significance of the set of truth tables
        """
        return self.__weight

    @property
    def hits(self) -> pandas.DataFrame:
        """
        A frame depicting the number of hits within each truth table
        """
        hit_count = [
            {
                "series_weight": self.__weight,
                "threshold": table.name,
                "threshold_weight": table.weight,
                "value": table.hits()
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(hit_count)

    @property
    def misses(self) -> pandas.DataFrame:
        """
        A frame depicting the number of misses within each truth table
        """
        miss_count = [
            {
                "series_weight": self.__weight,
                "threshold": table.name,
                "threshold_weight": table.weight,
                "value": table.misses()
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(miss_count)

    @property
    def false_positives(self) -> pandas.DataFrame:
        """
        A frame depicting the number of false positives within each truth table
        """
        false_positive_count = [
            {
                "series_weight": self.__weight,
                "threshold": table.name,
                "threshold_weight": table.weight,
                "value": table.false_positives()
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(false_positive_count)

    @property
    def true_negatives(self) -> pandas.DataFrame:
        """
        A frame depicting the number of true negatives within each truth table
        """
        true_negative_count = [
            {
                "series_weight": self.__weight,
                "threshold": table.name,
                "threshold_weight": table.weight,
                "value": table.true_negatives()
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(true_negative_count)

    @property
    def probability_of_detection(self) -> pandas.DataFrame:
        """
        A frame depicting the probability of detection for each truth table
        """
        probabilities_of_detection = [
            {
                "series_weight": self.__weight,
                "threshold": table.name,
                "threshold_weight": table.weight,
                "value": table.probability_of_detection()
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(probabilities_of_detection)

    @property
    def false_alarm_ratio(self) -> pandas.DataFrame:
        """
        A frame depicting the false alarm ratio for each truth table
        """
        probabilities_of_false_detection = [
            {
                "series_weight": self.__weight,
                "threshold": table.name,
                "threshold_weight": table.weight,
                "value": table.false_alarm_ratio()
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(probabilities_of_false_detection)

    @property
    def frequency_bias(self) -> pandas.DataFrame:
        """
        A frame depicting the frequency for each truth table
        """
        frequency_biases = [
            {
                "series_weight": self.__weight,
                "threshold": table.name,
                "threshold_weight": table.weight,
                "value": table.frequency_bias()
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(frequency_biases)

    @property
    def accuracy(self) -> pandas.DataFrame:
        """
        A frame depicting the accuracy of each truth table
        """
        accuracies = [
            {
                "series_weight": self.__weight,
                "threshold": table.name,
                "threshold_weight": table.weight,
                "value": table.accuracy()
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(accuracies)

    @property
    def precision(self) -> pandas.DataFrame:
        """
        A frame depicting the precision of each truth table
        """
        precision_rows = [
            {
                "series_weight": self.__weight,
                "threshold": table.name,
                "threshold_weight": table.weight,
                "value": table.precision()
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(precision_rows)

    @property
    def critical_success_index(self) -> pandas.DataFrame:
        """
        A frame depicting the critical success index of each truth table
        """
        indices = [
            {
                "series_weight": self.__weight,
                "threshold": table.name,
                "threshold_weight": table.weight,
                "value": table.critical_success_index()
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(indices)

    @property
    def equitable_threat_score(self) -> pandas.DataFrame:
        """
        A frame depicting the equitable threat score of each truth table
        """
        scores = [
            {
                "series_weight": self.__weight,
                "threshold": table.name,
                "threshold_weight": table.weight,
                "value": table.equitable_threat_score()
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(scores)

    @property
    def general_skill(self) -> pandas.DataFrame:
        """
        A frame depicting the general skill of each truth table
        """
        skills = [
            {
                "series_weight": self.__weight,
                "threshold": table.name,
                "threshold_weight": table.weight,
                "value": table.general_skill()
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(skills)

    @property
    def metrics(self) -> pandas.DataFrame:
        """
        A frame depicting all metrics for all tables
        """
        metric_data = list()

        for table in self.__tables.values():
            for metric in TruthTable.metrics():
                metric_data.append(
                    {
                        "series_weight": self.__weight,
                        "threshold": table.name,
                        "threshold_weight": table.weight,
                        "metric": metric,
                        "value": getattr(table, metric)()
                    }
                )

        return pandas.DataFrame(metric_data)

    @property
    def usefulness(self) -> float:
        """
        The numerical degree to which the set of truth tables bears value

        A table considered valueless if no activity was observed or predicted within it
        """
        if not numpy.isnan(self.__usefullness):
            return self.__usefullness

        # Evaluate usefulness
        max_possible_usefulness = max([table.weight for table in self.__tables.values()])
        current_usefulness = max([table.usefulness for table in self.__tables.values()])

        self.__usefullness = (current_usefulness / max_possible_usefulness) * self.weight

        return self.__usefullness

    def keys(self) -> typing.Iterable[str]:
        """
        The keys for each contained truth table.
        """
        return self.__tables.keys()

    def values(self) -> typing.Iterable[TruthTable]:
        """
        Every contained truth table
        """
        return self.__tables.values()

    def items(self) -> typing.ItemsView[str, TruthTable]:
        """
        Returns:
            An iterable collection of pairs of keys and their tables
        """
        return self.__tables.items()

    def __getitem__(self, key: typing.Union[Threshold, str]) -> TruthTable:
        """
        Attempts to retrieve a contained TruthTable by its name or a threshold name

        Args:
            key: A threshold or its name that should be within the collection

        Returns:
            The matching TruthTable. A KeyError is thrown if a matching TruthTable is not found
        """
        if isinstance(key, Threshold):
            key = key.name

        return self.__tables[key]

    def __len__(self):
        """
        Returns:
            The number of tables
        """
        return len(self.__tables)

    def __iter__(self):
        return self.__tables.__iter__()

    def __contains__(self, key: typing.Union[str, Threshold]) -> bool:
        """
        Determines whether or not there is a TruthTable present with the matching name or Threshold

        Args:
            key: The name of the table of interest or a threshold with the same name

        Returns:
            Whether or not there is a TruthTable present with the matching name or Threshold
        """
        if isinstance(key, Threshold):
            key = key.name

        return key in self.__tables
