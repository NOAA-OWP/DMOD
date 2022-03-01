#!/usr/bin/env python3
import typing
import os

from argparse import ArgumentParser

import pandas

from dmod.metrics.threshold import Threshold
import dmod.metrics.scoring as scoring
import dmod.metrics.metric as metrics

TEST_DIRECTORY = os.path.dirname(__file__)

OBSERVATIONS_SOURCE = "./observations.csv"
MODEL_DATA = {
    "Model 1": os.path.join(TEST_DIRECTORY, "model_1.csv"),
    "Model 2": os.path.join(TEST_DIRECTORY, "model_2.csv"),
    "Model 3": os.path.join(TEST_DIRECTORY, "model_3.csv"),
    "Model 4": os.path.join(TEST_DIRECTORY, "model_4.csv"),
    "Model 5": os.path.join(TEST_DIRECTORY, "model_5.csv")
}

OBSERVATION_VALUE_KEY = "Observations"
MODEL_VALUE_KEY = "value"


class Arguments(object):
    def __init__(self, *args):
        self.__option: typing.Optional[str] = None

        self.__parse_command_line(*args)

    @property
    def option(self) -> str:
        return self.__option

    def __parse_command_line(self, *args):
        parser = ArgumentParser("Put a description for your script here")

        # Add options
        parser.add_argument(
            "-o",
            metavar="option",
            dest="option",
            type=str,
            default="default",
            help="This is an example of an option"
        )

        # Parse the list of args if one is passed instead of args passed to the script
        if args:
            parameters = parser.parse_args(args)
        else:
            parameters = parser.parse_args()

        # Assign parsed parameters to member variables
        self.__option = parameters.option


def get_thresholds() -> typing.List[Threshold]:
    thresholds: typing.List[Threshold] = list()

    thresholds.append(
        Threshold(
            name="Minor",
            value=27,
            weight=5,
            observed_value_key=OBSERVATION_VALUE_KEY,
            predicted_value_key=MODEL_VALUE_KEY
        )
    )

    thresholds.append(
        Threshold(
            name="Moderate",
            value=36,
            weight=5,
            observed_value_key=OBSERVATION_VALUE_KEY,
            predicted_value_key=MODEL_VALUE_KEY
        )
    )

    thresholds.append(
        Threshold(
            name="Major",
            value=43,
            weight=5,
            observed_value_key=OBSERVATION_VALUE_KEY,
            predicted_value_key=MODEL_VALUE_KEY
        )
    )

    thresholds.append(
        Threshold(
            name="Record",
            value=60,
            weight=5,
            observed_value_key=OBSERVATION_VALUE_KEY,
            predicted_value_key=MODEL_VALUE_KEY
        )
    )

    return thresholds


def get_metrics() -> typing.List[scoring.Metric]:
    metric_functions: typing.List[scoring.Metric] = list()

    metric_functions.append(metrics.PearsonCorrelationCoefficient(5))
    metric_functions.append(metrics.NormalizedNashSutcliffeEfficiency(5))
    metric_functions.append(metrics.FalseAlarmRatio(5))
    metric_functions.append(metrics.ProbabilityOfDetection(5))
    metric_functions.append(metrics.EquitableThreatScore(5))
    metric_functions.append(metrics.Accuracy(5))
    metric_functions.append(metrics.GeneralSkill(5))
    metric_functions.append(metrics.FrequencyBias(5))
    metric_functions.append(metrics.KlingGuptaEfficiency(5))
    metric_functions.append(metrics.Precision(5))
    
    return metric_functions


def main():
    """
    Define your initial application code here
    """
    arguments = Arguments()
    scheme = scoring.ScoringScheme(get_metrics())
    thresholds = get_thresholds()

    print("Loading Observation data...")
    observations = pandas.read_csv(OBSERVATIONS_SOURCE, index_col="date", parse_dates=["date"])

    models: typing.Dict[str, pandas.DataFrame] = dict()

    for name, path in MODEL_DATA.items():
        print(f"Loading model data: {name}...")
        models[name] = pandas.read_csv(path, index_col="date", parse_dates=["date"])

    print("Forming pairs...")
    pairs: typing.Dict[str, pandas.DataFrame] = {
        name: observations.join(data).dropna(subset=[MODEL_VALUE_KEY])
        for name, data in models.items()
    }

    results: typing.Dict[str, scoring.MetricResults] = dict()
    print("Scoring models...")
    for name, pair_frame in pairs.items():
        print(f"Scoring {name}...")
        metric_results = scheme.score(pair_frame, OBSERVATION_VALUE_KEY, MODEL_VALUE_KEY, thresholds)
        results[name] = metric_results
    print("Scoring complete!")

    best_model = None
    model_score = None

    for name, metric_results in results.items():
        print(f"The total score for {name} was {metric_results.total}")

        if model_score is None or metric_results.total > model_score:
            best_model = name
            model_score = metric_results.total

    if best_model is not None:
        print(f"The best model was {best_model} with a score of {model_score}")


# Run the following if the script was run directly
if __name__ == "__main__":
    main()
