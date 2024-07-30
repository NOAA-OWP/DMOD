# How to Interpret Scores

----

## What determines how the combination of metrics across an evaluation should be interpretted?

Setting up an evaluation to run requires the configuration of a decision matrix by assigning weights to individual
metrics and individual thresholds. Consider the following evaluation configuration:

```json
{
    "observations": [],
    "predictions": [],
    "crosswalks": [],
    "thresholds": [
        {
            "backend": {},
            "locations": {},
            "definitions": [
                {
                    "name": "75th Percentile",
                    "field": "p75_va",
                    "weight": 10,
                    "unit": {
                        "value": "ft^3/s"
                    }
                }
            ]
        },
        {
            "backend": {},
            "locations": {},
            "definitions": [
                {
                    "name": "Action",
                    "field": "calc_flow_values/action",
                    "weight": 3,
                    "unit": {
                        "path": "metadata/calc_flow_units"
                    }
                },
                {
                    "name": "Flood",
                    "field": "calc_flow_values/flood",
                    "weight": 2,
                    "unit": {
                        "path": "metadata/calc_flow_units"
                    }
                }
            ]
        }
    ],
    "scheme": {
        "metrics": [
            {
                "name": "False Alarm Ratio",
                "weight": 10
            },
            {
                "name": "Probability of Detection",
                "weight": 10
            },
            {
                "name": "Kling-Gupta Efficiency",
                "weight": 15
            },
            {
                "name": "Normalized Nash-Sutcliffe Efficiency",
                "weight": 15
            },
            {
                "name": "Pearson Correlation Coefficient",
                "weight": 18
            }
        ]
    }
}
```

Three thresholds and five metrics are defined. The values for the thresholds are `10`, `3`, and `2`, meaning that the
evaluation is weighted _heavily_ in favor of the result of the `"75th Percentile"` threshold. The results of
`"Action"` and `"Flood"` may be poor but won't necessarily tank the entire evaluation. This is useful for including
thresholds that may provide very little useful data. At the end of the day,
the `"Action"` and `"Flood"` thresholds will only have a small effect on the overall evaluation. I can modify that to
fit my personal interests and needs by adjusting those values. If I want `"Flood"` to be a more important factor,
but still not as great as the `"75th Percentile"`, I can just increase its weight to `5`. There are no upper bounds as
to what these weights may be as they just define ratios. A `9:12:18` ratio, for example, would have the same sort of
result as `3:4:6` or `27:36:54`.

Similarly, each metric is weighted. In the above example, each metric is weighted as `10`, `10`, `15`, `15`, and `18`.
In this configuration, absolutely perfect scores for `"False Alarm Ratio"` and `"Probability of Detection"`
cannot make up for a very poor performance for `"Pearson Correlation Coefficient"`. If I were more concerned with
"Was this forecast able to detect if something did or didn't happen?", though, I could just increase
`"Probability of Detection"` and `"False Alarm Ratio"` high above the others or just lower the other values to make
the two metrics of interest far more significant.

The performance of an evaluation is determined by the performance of each threshold in terms of their weight within
the context of the weight of the defined metrics. The performance across each layer is given by its scaled value.
An evaluation, a location, a metric, and a threshold within a metric may all have their own scaled values.
Aggregating each level of scaled values may then be used to grade the entire evaluation, stating whether the
generated data was good or bad based on a scale from 0 to 100.

Results generated through different decision matrices are _not_ comparable. One set of model results may have two
__very__ different results depending on the matrices used during evaluation. It is the responsibility of the evaluator
to determine what matrices are appropriate for their individual interests.

## Types of Communicated Scores

As of 2022-01-17, scores are delivered in three types of messages:

1. `"metric"`
2. `"location_scores"`
3. `"evaluation_scores"`


### `"metric"` Messages

Metric messages are sent as individual metrics are run on each location. These messages may look like:

```json
{
    "event": "metric",
    "type": "send_message",
    "time": "2023-01-10 03:57:33 PM CST",
    "data": {
        "metric": "False Alarm Ratio",
        "description": "The probability that something was falsely reported as happening. Sensitive to false alarms, but ignores misses. Very sensitive to the climatological frequency of the event. Should be used in conjunction with the probability of detection.",
        "weight": 10,
        "total": 15.369990979426152,
        "scores": {
            "total": 15.369990979426152,
            "scaled_value": 9.6,
            "grade": "96.06%",
            "scores": {
                "p50_va": {
                    "value": 0,
                    "scaled_value": 1,
                    "sample_size": 741,
                    "failed": false,
                    "weight": 1,
                    "grade": 100
                },
                "p75_va": {
                    "value": 0.03,
                    "scaled_value": 9.64,
                    "sample_size": 741,
                    "failed": false,
                    "weight": 10,
                    "grade": 96.443
                },
                "p80_va": {
                    "value": 0.05,
                    "scaled_value": 4.72,
                    "sample_size": 741,
                    "failed": false,
                    "weight": 5,
                    "grade": 94.512
                }
            }
        },
        "metadata": {
            "observed_location": "0214655255",
            "predicted_location": "cat-27"
        }
    }
}
```

They show what metric was run, what location it pertains to, what the resultant values for threshold was,
scaled values for each threshold, and a scaled value for the singular metric for the specific location.

An example of a score for a threshold from the above example can be seen as:

```json
{
    "data": {
        "scores": {
            "scores": {
                "p75_va": {
                    "value": 0.03,
                    "scaled_value": 9.64,
                    "sample_size": 741,
                    "failed": false,
                    "weight": 10,
                    "grade": 96.443
                }
            }
        }
    }
}
```

This is for threshold `p75_va`. We see that the calculated value was `0.03`, which is very close to ideal -
the ideal value for this metric is 0. Therefore, the closer to 0 this is, the better the result. We also see that
the weight of the threshold is `10`. The displayed value is truncated, but is likely ~`0.036` in the calculation.
Since this is an inverted value (with 0 being ideal and 1 being a fail state), our factor for scaling would be
1 - ~0.036, yielding ~0.964. We now multiply the weight by the factor to get `9.64` - the resulting scaled value of
the threshold for the metric. Each threshold for this metric will have its own scaled value. Add each scaled
value together and divide by the maximum possible value across each threshold (the sum of all weights), and you can
determine the factor to use to determine the overall performance for the metric. The sum of all scaled values is
~`15.36999`, with the maximum possible value being `16`. Divide the sum of the scaled values by the maximum possible
value for each threshold and you get ~`0.96` as a factor of the weight of the metric. Multiply the weight of the metric
(`10`) and you get the performance of this metric for this location: ~`9.6`. This value can later be used to calculate
the overall performance for the location.

The performance of `"False Alarm Ratio"` for this location is almost perfect and will help build the case for this
location performing well.

### `"location_scores"` Messages

`"location_scores"` messages are transmitted once the sum total of all metrics have been run across an entire location.
These messages may look like:

```json
{
    "event": "location_scores",
    "type": "send_message",
    "time": "2023-01-10 03:57:33 PM CST",
    "data": {
        "observed_location": "0214655255",
        "predicted_location": "cat-27",
        "scores": {
            "weight": 1,
            "scaled_value": 0.6238284165154896,
            "total": 42.420332323053294,
            "maximum_possible_value": 68,
            "scores": {
                "False Alarm Ratio": {
                    "total": 15.369,
                    "maximum_possible_value": 16,
                    "scaled_value": 9.606244362141345,
                    "metric_weight": 10,
                    "p50_va": {
                        "value": 0,
                        "scaled_value": 1,
                        "sample_size": 741,
                        "failed": false,
                        "weight": 1,
                        "threshold": "p50_va",
                        "grade": 100
                    },
                    "p75_va": {
                        "value": 0.03,
                        "scaled_value": 9.64,
                        "sample_size": 741,
                        "failed": false,
                        "weight": 10,
                        "threshold": "p75_va",
                        "grade": 96.44381223328593
                    },
                    "p80_va": {
                        "value": 0.05,
                        "scaled_value": 4.72,
                        "sample_size": 741,
                        "failed": false,
                        "weight": 5,
                        "threshold": "p80_va",
                        "grade": 94.51219512195121
                    }
                },
                "Probability Of Detection": {
                    "total": 14.866,
                    "maximum_possible_value": 16,
                    "scaled_value": 9.291523039740087,
                    "metric_weight": 10,
                    "p50_va": {
                        "value": 1,
                        "scaled_value": 1,
                        "sample_size": 741,
                        "failed": false,
                        "weight": 1,
                        "threshold": "p50_va",
                        "grade": 100
                    },
                    "p75_va": {
                        "value": 0.94,
                        "scaled_value": 9.46,
                        "sample_size": 741,
                        "failed": false,
                        "weight": 10,
                        "threshold": "p75_va",
                        "grade": 94.6927374301676
                    },
                    "p80_va": {
                        "value": 0.87,
                        "scaled_value": 4.39,
                        "sample_size": 741,
                        "failed": false,
                        "weight": 5,
                        "threshold": "p80_va",
                        "grade": 87.94326241134752
                    }
                },
                "Kling-Gupta Efficiency": {
                    "total": 5.959,
                    "maximum_possible_value": 16,
                    "scaled_value": 5.587086130555756,
                    "metric_weight": 15,
                    "p50_va": {
                        "value": 0.27,
                        "scaled_value": 0.27,
                        "sample_size": 741,
                        "failed": false,
                        "weight": 1,
                        "threshold": "p50_va",
                        "grade": 27.897750687244738
                    },
                    "p75_va": {
                        "value": 0.37,
                        "scaled_value": 3.7,
                        "sample_size": 716,
                        "failed": false,
                        "weight": 10,
                        "threshold": "p75_va",
                        "grade": 37.03777745010943
                    },
                    "p80_va": {
                        "value": 0.39,
                        "scaled_value": 1.97,
                        "sample_size": 705,
                        "failed": false,
                        "weight": 5,
                        "threshold": "p80_va",
                        "grade": 39.53606574752164
                    }
                },
                "Normalized Nash-Sutcliffe Efficiency": {
                    "total": 6.805,
                    "maximum_possible_value": 16,
                    "scaled_value": 6.380578647250093,
                    "metric_weight": 15,
                    "p50_va": {
                        "value": 0.37,
                        "scaled_value": 0.37,
                        "sample_size": 741,
                        "failed": false,
                        "weight": 1,
                        "threshold": "p50_va",
                        "grade": 37.368219870938724
                    },
                    "p75_va": {
                        "value": 0.42,
                        "scaled_value": 4.23,
                        "sample_size": 716,
                        "failed": false,
                        "weight": 10,
                        "threshold": "p75_va",
                        "grade": 42.37778397794087
                    },
                    "p80_va": {
                        "value": 0.43,
                        "scaled_value": 2.19,
                        "sample_size": 705,
                        "failed": false,
                        "weight": 5,
                        "threshold": "p80_va",
                        "grade": 43.889799211265824
                    }
                },
                "Pearson Correlation Coefficient": {
                    "total": 10.271,
                    "maximum_possible_value": 16,
                    "scaled_value": 11.554900143366014,
                    "metric_weight": 18,
                    "p50_va": {
                        "value": 0.58,
                        "scaled_value": 0.58,
                        "sample_size": 741,
                        "failed": false,
                        "weight": 1,
                        "threshold": "p50_va",
                        "grade": 58.315969612863015
                    },
                    "p75_va": {
                        "value": 0.64,
                        "scaled_value": 6.4,
                        "sample_size": 716,
                        "failed": false,
                        "weight": 10,
                        "threshold": "p75_va",
                        "grade": 64.07197010152888
                    },
                    "p80_va": {
                        "value": 0.65,
                        "scaled_value": 3.28,
                        "sample_size": 705,
                        "failed": false,
                        "weight": 5,
                        "threshold": "p80_va",
                        "grade": 65.61331286754321
                    }
                }
            },
            "grade": 62.38284165154896
        }
    }
}
```

They show what metrics were run across what thresholds for what location. Like the above example in the `metric`
message section, we see values for `"False Alarm Ratio"`, but we also see the data for every other metric.
As above, we see that `"False Alarm Ratio"` performed very well, along with `"Probability of Detection"`. Despite this,
there was poor performance for the `"Kling-Gupta Efficiency"`, the `"Normalized Nash-Sutcliffe Efficiency"`,
and the `"Pearson Correlation Coefficient"`. This is unfortunate since the significance of these poorly performing
metrics (with weights of `15`, `15`, and `18`, respectively) are greater than the two well performing metrics
(with weights of `10` and `10`). As a result, the overall scaled value for this location was ~`0.6238284`,
resulting in a grade of ~`62.38%`, otherwise considered as a `D-` in academic letter grades.

This location did __not__ perform well based on our defined decision matrix. A different matrix weighing the two
better performing metrics at a __much__ high level of significance and the three poorly performing metrics at a
__much__ lower level of significance may communicate a better overall performance for this location under this
different interpretation context.

### `evaluation_scores` Messages

`evaluation_scores` messages highlight the scores for all locations in an evaluation. These outputs should look like:

```json
{
    "event": "evaluation_result",
    "type": "send_message",
    "time": "2023-01-10 03:57:33 PM CST",
    "data": {
        "total": 13.410101153701667,
        "performance": 0.2833262552670501,
        "grade": 28.33,
        "max_possible_total": 32,
        "mean": 6.705050576850834,
        "median": 6.705050576850834,
        "standard_deviation": 0.5177923498706796,
        "results": [
            {
                "observation_location": "0214655255",
                "prediction_location": "cat-27",
                "weight": 1,
                "scaled_value": 0.6238284165154896,
                "total": 42.420332323053294,
                "maximum_possible_value": 68,
                "scores": {
                    "False Alarm Ratio": {
                        "total": 15.369,
                        "maximum_possible_value": 16,
                        "scaled_value": 9.606244362141345,
                        "metric_weight": 10,
                        "p50_va": {
                            "value": 0,
                            "scaled_value": 1,
                            "sample_size": 741,
                            "failed": false,
                            "weight": 1,
                            "threshold": "p50_va",
                            "grade": 100
                        },
                        "p75_va": {
                            "value": 0.03,
                            "scaled_value": 9.64,
                            "sample_size": 741,
                            "failed": false,
                            "weight": 10,
                            "threshold": "p75_va",
                            "grade": 96.44381223328593
                        },
                        "p80_va": {
                            "value": 0.05,
                            "scaled_value": 4.72,
                            "sample_size": 741,
                            "failed": false,
                            "weight": 5,
                            "threshold": "p80_va",
                            "grade": 94.51219512195121
                        }
                    },
                    "Probability Of Detection": {
                        "total": 14.866,
                        "maximum_possible_value": 16,
                        "scaled_value": 9.291523039740087,
                        "metric_weight": 10,
                        "p50_va": {
                            "value": 1,
                            "scaled_value": 1,
                            "sample_size": 741,
                            "failed": false,
                            "weight": 1,
                            "threshold": "p50_va",
                            "grade": 100
                        },
                        "p75_va": {
                            "value": 0.94,
                            "scaled_value": 9.46,
                            "sample_size": 741,
                            "failed": false,
                            "weight": 10,
                            "threshold": "p75_va",
                            "grade": 94.6927374301676
                        },
                        "p80_va": {
                            "value": 0.87,
                            "scaled_value": 4.39,
                            "sample_size": 741,
                            "failed": false,
                            "weight": 5,
                            "threshold": "p80_va",
                            "grade": 87.94326241134752
                        }
                    },
                    "Kling-Gupta Efficiency": {
                        "total": 5.959,
                        "maximum_possible_value": 16,
                        "scaled_value": 5.587086130555756,
                        "metric_weight": 15,
                        "p50_va": {
                            "value": 0.27,
                            "scaled_value": 0.27,
                            "sample_size": 741,
                            "failed": false,
                            "weight": 1,
                            "threshold": "p50_va",
                            "grade": 27.897750687244738
                        },
                        "p75_va": {
                            "value": 0.37,
                            "scaled_value": 3.7,
                            "sample_size": 716,
                            "failed": false,
                            "weight": 10,
                            "threshold": "p75_va",
                            "grade": 37.03777745010943
                        },
                        "p80_va": {
                            "value": 0.39,
                            "scaled_value": 1.97,
                            "sample_size": 705,
                            "failed": false,
                            "weight": 5,
                            "threshold": "p80_va",
                            "grade": 39.53606574752164
                        }
                    },
                    "Normalized Nash-Sutcliffe Efficiency": {
                        "total": 6.805,
                        "maximum_possible_value": 16,
                        "scaled_value": 6.380578647250093,
                        "metric_weight": 15,
                        "p50_va": {
                            "value": 0.37,
                            "scaled_value": 0.37,
                            "sample_size": 741,
                            "failed": false,
                            "weight": 1,
                            "threshold": "p50_va",
                            "grade": 37.368219870938724
                        },
                        "p75_va": {
                            "value": 0.42,
                            "scaled_value": 4.23,
                            "sample_size": 716,
                            "failed": false,
                            "weight": 10,
                            "threshold": "p75_va",
                            "grade": 42.37778397794087
                        },
                        "p80_va": {
                            "value": 0.43,
                            "scaled_value": 2.19,
                            "sample_size": 705,
                            "failed": false,
                            "weight": 5,
                            "threshold": "p80_va",
                            "grade": 43.889799211265824
                        }
                    },
                    "Pearson Correlation Coefficient": {
                        "total": 10.271,
                        "maximum_possible_value": 16,
                        "scaled_value": 11.554900143366014,
                        "metric_weight": 18,
                        "p50_va": {
                            "value": 0.58,
                            "scaled_value": 0.58,
                            "sample_size": 741,
                            "failed": false,
                            "weight": 1,
                            "threshold": "p50_va",
                            "grade": 58.315969612863015
                        },
                        "p75_va": {
                            "value": 0.64,
                            "scaled_value": 6.4,
                            "sample_size": 716,
                            "failed": false,
                            "weight": 10,
                            "threshold": "p75_va",
                            "grade": 64.07197010152888
                        },
                        "p80_va": {
                            "value": 0.65,
                            "scaled_value": 3.28,
                            "sample_size": 705,
                            "failed": false,
                            "weight": 5,
                            "threshold": "p80_va",
                            "grade": 65.61331286754321
                        }
                    }
                },
                "grade": 62.38284165154896
            },
            {
                "observation_location": "0214657975",
                "prediction_location": "cat-52",
                "weight": 1,
                "scaled_value": 0.7459713867820127,
                "total": 50.726054301176866,
                "maximum_possible_value": 68,
                "scores": {
                    "False Alarm Ratio": {
                        "total": 15.135,
                        "maximum_possible_value": 16,
                        "scaled_value": 9.459971409260165,
                        "metric_weight": 10,
                        "p50_va": {
                            "value": 0,
                            "scaled_value": 1,
                            "sample_size": 697,
                            "failed": false,
                            "weight": 1,
                            "threshold": "p50_va",
                            "grade": 100
                        },
                        "p75_va": {
                            "value": 0.04,
                            "scaled_value": 9.58,
                            "sample_size": 697,
                            "failed": false,
                            "weight": 10,
                            "threshold": "p75_va",
                            "grade": 95.83931133428982
                        },
                        "p80_va": {
                            "value": 0.08,
                            "scaled_value": 4.55,
                            "sample_size": 697,
                            "failed": false,
                            "weight": 5,
                            "threshold": "p80_va",
                            "grade": 91.04046242774567
                        }
                    },
                    "Probability Of Detection": {
                        "total": 16,
                        "maximum_possible_value": 16,
                        "scaled_value": 10,
                        "metric_weight": 10,
                        "p50_va": {
                            "value": 1,
                            "scaled_value": 1,
                            "sample_size": 697,
                            "failed": false,
                            "weight": 1,
                            "threshold": "p50_va",
                            "grade": 100
                        },
                        "p75_va": {
                            "value": 1,
                            "scaled_value": 10,
                            "sample_size": 697,
                            "failed": false,
                            "weight": 10,
                            "threshold": "p75_va",
                            "grade": 100
                        },
                        "p80_va": {
                            "value": 1,
                            "scaled_value": 5,
                            "sample_size": 697,
                            "failed": false,
                            "weight": 5,
                            "threshold": "p80_va",
                            "grade": 100
                        }
                    },
                    "Kling-Gupta Efficiency": {
                        "total": 10.499,
                        "maximum_possible_value": 16,
                        "scaled_value": 9.843441056936772,
                        "metric_weight": 15,
                        "p50_va": {
                            "value": 0.65,
                            "scaled_value": 0.65,
                            "sample_size": 697,
                            "failed": false,
                            "weight": 1,
                            "threshold": "p50_va",
                            "grade": 65.8818200357591
                        },
                        "p75_va": {
                            "value": 0.65,
                            "scaled_value": 6.55,
                            "sample_size": 668,
                            "failed": false,
                            "weight": 10,
                            "threshold": "p75_va",
                            "grade": 65.55765196203832
                        },
                        "p80_va": {
                            "value": 0.65,
                            "scaled_value": 3.28,
                            "sample_size": 630,
                            "failed": false,
                            "weight": 5,
                            "threshold": "p80_va",
                            "grade": 65.70174128342265
                        }
                    },
                    "Normalized Nash-Sutcliffe Efficiency": {
                        "total": 9.877,
                        "maximum_possible_value": 16,
                        "scaled_value": 9.259761637420176,
                        "metric_weight": 15,
                        "p50_va": {
                            "value": 0.62,
                            "scaled_value": 0.62,
                            "sample_size": 697,
                            "failed": false,
                            "weight": 1,
                            "threshold": "p50_va",
                            "grade": 62.39523791829951
                        },
                        "p75_va": {
                            "value": 0.61,
                            "scaled_value": 6.17,
                            "sample_size": 668,
                            "failed": false,
                            "weight": 10,
                            "threshold": "p75_va",
                            "grade": 61.7719157928107
                        },
                        "p80_va": {
                            "value": 0.61,
                            "scaled_value": 3.07,
                            "sample_size": 630,
                            "failed": false,
                            "weight": 5,
                            "threshold": "p80_va",
                            "grade": 61.51870242901579
                        }
                    },
                    "Pearson Correlation Coefficient": {
                        "total": 10.811,
                        "maximum_possible_value": 16,
                        "scaled_value": 12.16288019755975,
                        "metric_weight": 18,
                        "p50_va": {
                            "value": 0.68,
                            "scaled_value": 0.68,
                            "sample_size": 697,
                            "failed": false,
                            "weight": 1,
                            "threshold": "p50_va",
                            "grade": 68.5145587136938
                        },
                        "p75_va": {
                            "value": 0.67,
                            "scaled_value": 6.76,
                            "sample_size": 668,
                            "failed": false,
                            "weight": 10,
                            "threshold": "p75_va",
                            "grade": 67.639559678795
                        },
                        "p80_va": {
                            "value": 0.67,
                            "scaled_value": 3.36,
                            "sample_size": 630,
                            "failed": false,
                            "weight": 5,
                            "threshold": "p80_va",
                            "grade": 67.24695018962234
                        }
                    }
                },
                "grade": 74.59713867820128
            }
        ],
        "metrics": [
            {
                "name": "False Alarm Ratio",
                "weight": 10,
                "description": "The probability that something was falsely reported as happening. Sensitive to false alarms, but ignores misses. Very sensitive to the climatological frequency of the event. Should be used in conjunction with the probability of detection."
            },
            {
                "name": "Probability Of Detection",
                "weight": 10,
                "description": "The probability that something was detected. Sensitive to hits, but ignores false alarms. Very sensitive to the climatological frequency of the event. Good for rare events."
            },
            {
                "name": "Kling-Gupta Efficiency",
                "weight": 15,
                "description": "A goodness-of-fit measure providing a diagnostically interesting decomposition of the Nash-Sutcliffe efficiency"
            },
            {
                "name": "Normalized Nash-Sutcliffe Efficiency",
                "weight": 15,
                "description": "A normalized statistic that measures the relative magnitude of noise compared to information"
            },
            {
                "name": "Pearson Correlation Coefficient",
                "weight": 18,
                "description": "A measure of linear correlation between two sets of data"
            }
        ]
    }
}
```

Despite some organizational differences, these messages contain all the data from the `location_scores` messages
wrapped up in one package, complete with extra metadata, such as additional details describing individual metrics.
This message is sent exactly once per evaluation, at the very end.
