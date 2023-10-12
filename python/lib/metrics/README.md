# Distributed Model on Demand - Metrics

The Distributed Model on Demand (DMOD) metrics package is a python library dedicated exclusively 
to describing available functionality and performing mathematical operations upon provided data.

## How are metrics called?

There lies a class at `dmod.scoring` named `ScoringScheme` that manages operations.
You first provide it a list of all metrics you intend to gather from your input data and a set of
`Communicator` objects to help distribute information generated during evaluation. Next, you can
call the `ScoringScheme` as a function with prepared pairs, where to find "observed" values within
the pairs, where to find the "predicted" values within the pairs, and thresholds. This invocation
will yield a `MetricResults` object.

This same `ScoringScheme` may be called many times over with different sets of data, usually 
corresponding to different locations, while maintaining a common standard of expected results.

## What do `MetricResults` provide?

`dmod.metrics.MetricResults` objects provide access to individual metrics and tools for interpreting 
results in different ways and making it easier to serialize results for further communication.

## How can `MetricResults` interpret the outcome of an evaluation?

Each `MetricResults` object contains the evaluated metrics performed on a singular set of data.
When providing the `Metric`s that are run to the `ScoringScheme`, a weight is passed along for 
each metric and passing thresholds to the invocation will provide weights for each threshold. This
provides a basis for determine a hierarchy of importance for each metric and threshold. For an
evaluation, the `Critical Success Index` may be deemed as twice as important as the results for
the `Normalized Nash-Sutcliffe Efficiency` and results for the "Major" threshold may be deemed
1.5 times more important than the results for the "Moderate" threshold.

These weights, along with metadata for each metric provides a means of scaling and grading. The 
`PearsonCorrelationCoefficient` `Metric` class, for example, knows that the maximum value is `1`,
the minimum value is `-1`, the ideal value is `1`, and `0` marks a total failure of the predicted
data to correlate in some fashion to the observed data (negative values aren't considered a total
failure since they indicate some degree of negative correlation whereas `0` is absolutely none
whatsoever). For the following example, let us say that the result of a given instance of 
`PearsonCorrelationCoefficent` with a weight of `7` has a result of `0.6734` for the "Major" 
threshold. This is interpreted as a scaled value of `4.7138`. Now let us say we have an
instance of `ProbabilityOfFalseDetection` with a weight of `3` that has a result of `0.12`.
This is interpreted as having a scaled value of `2.64`. If those are the only metrics considered
for the "Major" threshold, the maximum possible value for that threshold is `10` (
`PearsonCorrelationCoefficient` with a weight of `7` and `ProbabilityOfFalseDetection` with
a weight of `3`). Since those results were `4.7138` and `2.64`, their total value was `7.3538`
out of `10`, or a grade of `73.538%`. Now say the only other threshold being evaluated was 
"Moderate" with a weight of `3` and a total of `2.73`, or a grade of `91%`. The overall result
of the combination of these two thresholds is now `7.3538` + `2.73` out of `10` + `3`, or
`10.0838` out of `13`, with a grade of `77.567%`.

## What is a `Metric` in the codebase?

An instance of `dmod.metrics.scoring.Metric` is an object that may be called to provide scores 
for a collection of pairs when filtered via thresholds. Examples of these 
`dmod.metrics.scoring.Metric` classes are `dmod.metrics.ProbabilityOfFalseDetection`
and `dmod.metrics.PearsonCorrelationCoefficient`. These are constructed with a given weight, so 
an instance of `dmod.metrics.ProbabilityOfDetection` may be created with a weight of `3` and
an instance of `dmod.metrics.KlingGuptaEfficiency` may be created with a weight of `8`.

New metrics may be implemented simply by declaring the new class and implementing `get_description`,
which will allow outside code to discover what this new metric is expected to do, `get_name`, which
provides an easy to identify name, and `__call__`, which is where the actual operation will be
performed.

A very simple example would be:

```python
class VolumeError(scoring.Metric):
    @classmethod
    def get_descriptions(cls):
        return "The difference between the observed volume and the predicted volume"

    @classmethod
    def get_name(cls) -> str:
        return "Volume Error"

    def __init__(self, weight: NUMBER):
        """
        Constructor

        Args:
            weight: The relative significance of the metric
        """
        super().__init__(
            weight=weight,
            ideal_value=0,
            greater_is_better=False
        )

    def __call__(
        self,
        pairs: pandas.DataFrame,
        observed_value_label: str,
        predicted_value_label: str,
        thresholds: typing.Sequence[Threshold] = None,
        *args,
        **kwargs
    ) -> scoring.Scores:
        scores: typing.List[scoring.Score] = list()

        for volume_threshold in thresholds:
            filtered_pairs = volume_threshold(pairs)
            difference = 0
            if not filtered_pairs.empty:
                dates: typing.List[int] = [value.astype("int") for value in filtered_pairs.index.values]
                area_under_observations = sklearn.metrics.auc(dates, filtered_pairs[observed_value_label])
                area_under_predictions = sklearn.metrics.auc(dates, filtered_pairs[predicted_value_label])
                difference = area_under_predictions - area_under_observations
            scores.append(scoring.Score(self, difference, volume_threshold, sample_size=len(filtered_pairs)))

        return scoring.Scores(self, scores)
```

This provides everything needed to use outside logic provided by `SciKit-Learn` _and_ make the metric
easy to explore.

## What about categorical metrics?

`dmod.metrics` has a wide range of support for categorical metrics primarily due to their bounded nature.
This means that they naturally have well-defined information for scaling and grading.

Implementing categorical metrics is relatively easy since they rely on truth tables. Probability of Detection,
for example, is incredibly easy to implement:

```python
class ProbabilityOfDetection(CategoricalMetric):
    @classmethod
    def get_descriptions(cls):
        return "The probability that something was detected. Sensitive to hits, but ignores false alarms. " \
               "Very sensitive to the climatological frequency of the event. Good for rare events."

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.probability_of_detection.iterrows()

    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("probability_of_detection")
```

All this ends up doing is gathering the `probability_of_detection` function that has already been defined
on `TruthTables` collections that hold `TruthTable` objects:

```python
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
                "value": table.probability_of_detection(),
                "sample_size": len(table)
            }
            for table in self.__tables.values()
        ]

        return pandas.DataFrame(probabilities_of_detection)
```

## What is meant by "Discoverability"?

Metadata may be collected about each implemented Metric without any sort of outside code or any
needed hardcoding. Anything that may invoke `dmod.metrics` may be able to perform operations such as:

```python
from pprint import pprint
import dmod.metrics as metrics

pprint(metrics.get_metric_options())
```

and see:

```shell
[{'description': 'The probability that something was detected. Sensitive to '
                 'hits, but ignores false alarms. Very sensitive to the '
                 'climatological frequency of the event. Good for rare events.',
  'identifier': 'probabilityofdetection',
  'name': 'Probability Of Detection'},
 {'description': 'The probability that something was falsely reported as '
                 'happening. Sensitive to false alarms, but ignores misses. '
                 'Very sensitive to the climatological frequency of the event. '
                 'Should be used in conjunction with the probability of '
                 'detection.',
  'identifier': 'falsealarmratio',
  'name': 'False Alarm Ratio'},
 {'description': 'Sensitive to false alarms, but ignores misses. Can be '
                 "artificially improved by issuing fewer 'yes' forecasts to "
                 'reduce the number of false alarms. Not often reported for '
                 'deterministic forecasts, but is an important component of '
                 'the Relative Operating Characteristic (ROC) used widely for '
                 'probabilistic forecasts.',
  'identifier': 'probabilityoffalsedetection',
  'name': 'Probability Of False Detection'},
  ...
```

This provides more than enough information needed to build user interfaces or gather information
to provide further context to data. Say I receive a value for `"equitablethreatscore"`. What does
that value indicate? Well, the metadata explains that the `"equitablethreatscore"` may be
displayed as `"Equitable Threat Score"` and describes `'How well did the forecast "yes" events correspond 
to the observed "yes" events (accounting for hits due to chance)? Sensitive to hits. Because it 
penalises both misses and false alarms in the same way, it does not distinguish the source of 
forecast error.'`

## What is a `Communicator`?

A `dmod.metrics.Communicator` is an event based mechanism for handling data emission events.
`Communicator`s are stored within `dmod.metrics.CommunicatorGroup`s which may handle more wide scale
communication operations. An example can be found in the `score` function of 
`dmod.metrics.ScoringScheme` where each evaluation of a metric is announced:

```python
        for metric in self.__metrics:  # type: Metric
            self.__communicators.info(f"Calling {metric.name}", verbosity=Verbosity.LOUD, publish=True)
            ...
```

This means that the `info` event will be triggered on each held `Communicator`, but only on those set to handle 
messages of a verbosity of `LOUD` or greater, and to call the `write` event after doing so.

Say I have three communicators:

1. Writes errors to stderr with a verbosity of `LOUD` (operates when very little data is necessary)
2. Writes information with a verbosity of `QUIET` to a file
3. Sends `LOUD` messages through Redis channels 
(see `dmod.evaluation_service.utilities.communication.RedisCommunicator`)

Per the above example, `Communicator` 1 won't perform any operations because it only handles errors and this 
was just standard information. `Communicator` 2 won't perform operations because the given message was meant to be loud
and `Communicator` 2 is meant to only handle `QUIET` data. `Communicator` 3, though, will handle the message by
transforming the information into a common format, adding it to a list in a specified Redis instance, and call the
`write` command on it. The `write` command will send the message to all clients listening to that redis channel
and send that transformed data to any added handlers for the `write` event.

## How can I invoke a metric?

There's not a lot of complexity when it comes to just calling metrics:

```python
from pprint import pprint

import pandas

import dmod.metrics as metrics

pearson = metrics.PearsonCorrelationCoefficient(5)
observation_key = "observed"
model_key = "modeled"
data = pandas.DataFrame({observation_key: [1, 2, 3, 4, 5], model_key: [2, 3, 4, 5, 6]})
results = pearson(data, observation_key, model_key)
pprint(results.to_dict())
```

which yields:

```shell
{'grade': '100.00%',
 'scaled_value': 4.99,
 'scores': {'All': {'failed': False,
                    'grade': 99.999,
                    'sample_size': 5,
                    'scaled_value': 0.99,
                    'value': 0.99,
                    'weight': 1}},
 'total': 0.9999999999999999}
```

`dmod.evaluations` provides functionality that helps with more advanced operations 
(such as adding thresholds and operating upon many metrics)