# Specification

Evaluation workflows are highly configurable via the use of required evaluation specifications. There are a lot
of different options, but this level of complexity may be mitigated through the use of [templates](#templates).

## Table of Contents

- [A Word on Templates](#templates)
- [Evaluation Specification](#EvaluationSpecification)
    - [Examples](#EvaluationSpecificationExamples)
- [Data Source Specification](#DataSourceSpecification)
    - [Examples](#DataSourceSpecificationExamples)
- [Backend Specification](#BackendSpecification)
    - [Examples](#BackendSpecificationExamples)
- [Associated Field](#AssociatedField)
    - [How to Use Paths](#AssociatedFieldPaths)
    - [Examples](#AssociatedFieldExamples)
- [Field Mapping Specification](#FieldMappingSpecification)
    - [Examples](#FieldMappingSpecificationExamples)
- [Value Selector](#ValueSelector)
    - [How to Use Paths](#ValueSelectorPaths)
    - [Examples](#ValueSelectorExamples)
- [Crosswalk Specification](#CrosswalkSpecification)
    - [Examples](#CrosswalkSpecificationExamples)
- [Location Specification](#LocationSpecification)
    - [Examples](#LocationSpecificationExamples)
- [Metric Specification](#MetricSpecification)
    - [Examples](#MetricSpecificationExamples)
- [Threshold Specification](#ThresholdSpecification)
    - [Examples](#ThresholdSpecificationExamples)
- [Threshold Definition](#ThresholdDefinition)
    - [Examples](#ThresholdDefinitionExamples)
- [Threshold Application Rules](#ThresholdApplicationRules)
    - [Examples](#ThresholdApplicationRulesExamples)
- [Unit Definition](#UnitDefinition)
    - [Examples](#UnitDefinitionExamples)
- [Scheme Specification](#SchemeSpecification)
    - [Examples](#SchemeSpecification)
- [All Specification Elements](#all-elements)

<a id="templates"></a>
## A word on templates

Templating in evaluation specifications is a means of using preconfigured logic within new configurations.
Many configurations may be the same or they may be mostly the same. Configuring full or partial configurations
and attaching a template name to a configuration will apply the template settings prior to the application of
passed configurations.

Templates are supported on any model that has the `template_name` property. To use an existing template,
all that must be done to include it is to set the value of `template_name` to it:

```json
{
    "observations": [
        {
            "template_name": "Observation Template"
        }
    ]
}
```

<a id="EvaluationSpecification"></a>
## Evaluation Specification

![Instructions for how different aspect of an evaluation should work](../../../images/dmod.evaluations.specification.evaluation.EvaluationSpecification.png)

<a id="DataSourceSpecification"></a>
## Data Source Specification

![Specification for where to get the actual data for evaluation](../../../images/dmod.evaluations.specification.data.DataSourceSpecification.png)

<a id="BackendSpecification"></a>
## Backend Specification

![A specification for how data should be loaded](../../../images/dmod.evaluations.specification.backend.BackendSpecification.png)

<a id="BackendSpecificationExamples"></a>
### Example
Load a local RDB file stored at "resources/nwis_stat_thresholds.rdb":
```json
{
    "backend_type": "file",
    "format": "rdb",
    "address": "resources/nwis_stat_thresholds"
}
```

Retrieve streamflow data from NWIS' Instantaneous Values service for locations "0214657975" and
"0214655255", with values ocurring between midnight 2022-12-01 and midnight 2022-12-31:
```json
{
    "backend_type": "rest",
    "format": "json",
    "address": "https://nwis.waterservices.usgs.gov/nwis/iv",
    "params": {
        "format": "json",
        "indent": "on",
        "sites": "0214657975,0214655255",
        "startDT": "2022-12-01T00:00%2b0000",
        "endDT": "2022-12-31T00:00%2b0000",
        "parameterCd": "00060"
    }
}
```

Use the "Instantaneous NWIS Streamflow" template to retrieve streamflow data from location "0214657975"
from between midnight 2023-09-01 and midnight 2023-09-14:
```json
{
    "template_name": "Instantaneous NWIS Streamflow",
    "params": {
        "sites": "0214657975",
        "startDT": "2023-09-01T00:00%2b0000",
        "endDT": "2023-09-14T00:00%2b0000"
    }
}
```

Retrieve data "path/to/file.json" in the style handled by the "JSON File" template
```json
{
    "template_name": "JSON File",
    "address": "path/to/file.json"
}
```

<a id="AssociatedField"></a>
## Associated Field

![A specification for additional data that should accompany selected data](../../../images/dmod.evaluations.specification.fields.AssociatedField.png)

<a id="AssociatedFieldPaths"></a>
### How to Use Paths

<a id="AssociatedFieldExamples"></a>
### Example

Use data at `sourceInfo.siteCode[0].value`, starting from the current origin, as the accompanying location
for the currently identified measurement
```json
{
    "name":"observation_location",
    "path": ["sourceInfo", "siteCode", "[0]", "value"],
    "datatype": "string"
}
```

Consider the adjacent `date` field as a `datetime` object for read measurements
```json
{
    "name": "date",
    "datatype": "datetime"
}
```

<a id="FieldMappingSpecification"></a>
## Field Mapping Specification

![Details on how a field should be aliased](../../../images/dmod.evaluations.specification.fields.FieldMappingSpecification.png)

<a id="FieldMappingSpecificationExamples"></a>
### Example

Rename the "date" field as "value_date" for processing
```json
{
    "field": "value_date",
    "map_type": "column",
    "value": "date"
}
```

Consider the value of "site_no" as the field named "location"
```json
{
    "field": "location",
    "map_type": "value",
    "value": "site_no"
}
```

<a id="ValueSelector"></a>
## Value Selector

![Instructions for how to retrieve values from a data source](../../../images/dmod.evaluations.specification.fields.ValueSelector.png)

<a id="ValueSelectorPaths"></a>
### How to use paths


<a id="ValueSelectorExamples"></a>
### Example

Use each value located at `"values[*].value[*].value"`, starting from every node found at
`"$.value.timeSeries[*]"` as a floating point number used for a field named `observation`. When selecting that value, 
also select `"values[*].value[*].datetime"` as a `datetime` field named `"value_date"`, `"sourceInfo.siteCode[0].value"` 
as a string for a field named 'observation_location', and `"variable.unit.unitCode"` as a string field named "unit".

```json
{
    "name": "observation",
    "where": "value",
    "path": ["values[*]", "value[*]", "value"],
    "datatype": "float",
    "origin": ["$", "value", "timeSeries[*]"],
    "associated_fields": [
        {
            "name":"value_date",
            "path": ["values[*]", "value[*]", "dateTime"],
            "datatype": "datetime"
        },
        {
            "name":"observation_location",
            "path": ["sourceInfo", "siteCode", "[0]", "value"],
            "datatype": "string"
        },
        {
            "name":"unit",
            "path": ["variable", "unit", "unitCode"],
            "datatype": "string"
        }
    ]
}
```

This will select values that might look like:

| observation | value_date                    | observation_location | unit  |
|-------------|-------------------------------|----------------------|-------|
| 46.9        | 2015-11-30T20:00:00.000-05:00 | 0214655255           | ft3/s |
| 50.2        | 2015-11-30T20:05:00.000-05:00 | 0214655255           | ft3/s |
| 48.2        | 2015-11-30T20:10:00.000-05:00 | 0214655255           | ft3/s |

The following might yield the same result:
```json
{
    "name": "observation",
    "where": "value",
    "path": ["values[*]", "value[*]", "value"],
    "datatype": "float",
    "origin": ["$", "value", "timeSeries[*]"],
    "associated_fields": [
        {
            "template_name": "NWIS Value Date"
        },
        {
            "template_name": "NWIS Observation Location"
        },
        {
            "template_name": "NWIS Unit"
        }
    ]
}
```

Use the column named '"predicted"' and match it with the adjacent column named '"date"':
```json
{
    "name": "predicted",
    "where": "column",
    "associated_fields": [
        {
            "name": "date",
            "datatype": "datetime"
        }
    ]
}
```

<a id="CrosswalkSpecification"></a>
## Crosswalk Specification

![Specifies how locations in the observations should be linked to locations in the predictions](../../../images/dmod.evaluations.specification.locations.CrosswalkSpecification.png)

<a id="CrosswalkSpecificationExamples"></a>

Load the local `JSON` file at "resources/crosswalk.json" and extract the keys found at `"* where site_no"` 
(everything that has a `site_no` field) to use as a "prediction_location" and use its contained value 
`"site_no"` as a field named "observation_location":
```json
{
    "backend": {
        "backend_type": "file",
        "address": "resources/crosswalk.json",
        "format": "json"
    },
    "observation_field_name": "observation_location",
    "prediction_field_name": "prediction_location",
    "field": {
        "name": "prediction_location",
        "where": "key",
        "path": ["* where site_no"],
        "origin": "$",
        "datatype": "string",
        "associated_fields": [
            {
                "name": "observation_location",
                "path": "site_no",
                "datatype": "string"
            }
        ]
    }
}
```

Using templates, this may be represented as:
```json
{
    "backend": {
        "template_name": "JSON File",
        "address": "resources/crosswalk.json"
    },
    "observation_field_name": "observation_location",
    "prediction_field_name": "prediction_location",
    "field": {
        "template_name": "Prediction Key to Observed Site Crosswalk"
    }
}
```

This might yield something that looks like:

| observation_location | prediction_location |
|----------------------|---------------------|
| 0214655255           | cat-52              |
| 02146562             | cat-67              |
| 0214655255           | cat-27              |

The following JSON will instruct evaluations to pair observed data to predicted data where the observation's 
`observation_location` field matches the indicated value in the prediction's `predicted_location` field:

```json
{
    "observation_field_name": "observation_location",
    "prediction_field_name": "prediction_location"
}
```

<a id="LocationSpecification"></a>
## Location Specification

![A specification for where location data should be found](../../../images/dmod.evaluations.specification.locations.LocationSpecification.png)

<a id="LocationSpecificationExamples"></a>
### Example

Identify locations as those being from the `site_no` column:
```json
{
    "identify": true,
    "from_field": "column",
    "pattern": "site_no"
}
```

Identify location names based on the filename from files with names like `cat-27` and `cat-52` from files 
like `cat-27.csv` and `cat-52_cms.csv`:
```json
{
    "identify": true,
    "from_field": "filename",
    "pattern": "cat-\\d\\d"
}
```


<a id="ThresholdDefinition"></a>
## Threshold Definition

![A definition of a single threshold, where it comes from, and its significance](../../../images/dmod.evaluations.specification.threshold.ThresholdDefinition.png)

<a id="ThresholdDefinitionExamples"></a>
### Examples

Use a threshold named `75th Percentile` with values from the `p75_va` field measured in `ft^3/s` with a weight of 10.
```json
{
    "name": "75th Percentile",
    "field": "p75_va",
    "weight": 10,
    "unit": {
        "value": "ft^3/s"
    }
}
```

<a id="ThresholdApplicationRules"></a>
## Threshold Application Rules

![Add rules for how thresholds should be applied](../../../images/dmod.evaluations.specification.threshold.ThresholdApplicationRules.png)

<a id="ThresholdApplicationRulesExamples"></a>
### Examples

Apply the threshold to observation data by creating two new columns, one named `threshold_day` in the threshold data 
created by converting the `month_nu` and `day_nu` integer fields into one `Day` field, and another named 
`threshold_day`, created by converting the `value_date` field into one `Day` field.
```json
{
    "name": "Date to Day",
    "threshold_field": {
        "name": "threshold_day",
        "path": [
            "month_nu",
            "day_nu"
        ],
        "datatype": "Day"
    },
    "observation_field": {
        "name": "threshold_day",
        "path": [
            "value_date"
        ],
        "datatype": "Day"
    }
}
```

<a id="ThresholdSpecification"></a>
## Threshold Specification

![Instructions for how to load and apply thresholds to observed and predicted data](../../../images/dmod.evaluations.specification.threshold.ThresholdSpecification.png)

<a id="ThresholdSpecificationExamples"></a>
### Example

The following two examples load an RDB file named `resources/nwis_stat_thresholds.rdb`, 
names locations based off of the identified `site_no` column, matches loaded thresholds onto two new columns, the first 
being `threshold_day` on the threshold data, created by converting the `month_nu` and `day_nu` fields into `Day` objects, 
the second being named `threshold_day` on the observation data, created by converting the `value_date` field into 
`Day` objects. Use the `p75_va`, `p80_va`, and `p50_va` fields as thresholds named `"75th Percentile"`, 
`"80th Percentile"`, and `"Median"`, respectively, measured in `ft^3/s` and weighing `10`, `5`, and `1`, respectively.
The `75th Percentile` threshold will be considered 10 times more important than the `Median`, while the 
`80th Percentile` will be considered half as important as the `75th Percentile`, but 5 times as important as the
`Median`.

```json
{
    "name": "NWIS Stat Percentiles",
    "backend": {
        "backend_type": "file",
        "format": "rdb",
        "address": "resources/nwis_stat_thresholds.rdb"
    },
    "locations": {
        "identify": true,
        "from_field": "column",
        "pattern": "site_no"
    },
    "application_rules": {
        "threshold_field": {
            "name": "threshold_day",
            "path": [
                "month_nu",
                "day_nu"
            ],
            "datatype": "Day"
        },
        "observation_field": {
            "name": "threshold_day",
            "path": [
                "value_date"
            ],
            "datatype": "Day"
        }
    },
    "definitions": [
        {
            "name": "75th Percentile",
            "field": "p75_va",
            "weight": 10,
            "unit": {
                "value": "ft^3/s"
            }
        },
        {
            "name": "80th Percentile",
            "field": "p80_va",
            "weight": 5,
            "unit": {
                "value": "ft^3/s"
            }
        },
        {
            "name": "Median",
            "field": "p50_va",
            "weight": 1,
            "unit": {
                "value": "ft^3/s"
            }
        }
    ]
}
```

```json
{
    "backend": {
        "template_name": "NWIS Stat Thresholds"
    },
    "locations": {
        "template_name": "Site Number Column"
    },
    "application_rules": {
        "template_name": "Date to Day"
    },
    "definitions": [
        {
            "template_name": "75th Percentile"
        },
        {
            "template_name": "80th Percentile"
        },
        {
            "template_name": "Median"
        }
    ]
}
```

<a id="UnitDefinition"></a>
## Unit Definition

![A definition of what a measurement unit is or where to find it](../../../images/dmod.evaluations.specification.unit.UnitDefinition.png)

<a id="UnitDefinitionExamples"></a>
### Examples

Use the values in the `unit` field as the name of the measurement unit:
```json
{
    "field": "unit"
}
```

Use the value `"ft^3/s"` as the unit of measurement for every piece of data loaded in this context:
```json
{
    "value": "ft^3/s"
}
```


<a id="MetricSpecification"></a>
## Metric Specification

![The definition for what metric should be used and how important it should be](../../../images/dmod.evaluations.specification.scoring.MetricSpecification.png)

<a id="MetricSpecificationExamples"></a>
### Example

Use the metric named "Pearson Correlation Coefficient" with a relative weight of `10`
```json
{
    "name": "Pearson Correlation Coefficient",
    "weight": 10
}
```

Use the metric named "pRoBabIliTyOfDeTecTiOn" with a relative weight of `4`
```json
{
    "name": "pRoBabIliTyOfDeTecTiOn",
    "weight": 4
}
```

Using the above two examples at the same time will tell the evaluation that the result of the 
"Pearson Correlation Coefficient" is 250% more important than the result of "Probability of Detection"

<a id="SchemeSpecification"></a>
## Schema Specification

![A definition of what a measurement unit is or where to find it](../../../images/dmod.evaluations.specification.scoring.SchemeSpecification.png)

<a id="SchemeSpecificationExamples"></a>
### Examples

Use the metrics "Pearson Correlation Coefficient", "Normalized Nash-Sutcliffe Efficiency", 
"Kling-Gupta Efficiency", "Probability of Detection", and "False Alarm Ratio", but consider "Pearson Correlation Coefficient"
as the most important metric, followed by "Normalized Nash-Sutcliffe Efficiency" and "Kling-Gupta Efficiency", then followed by
"False Alarm Ratio" and "Probability of Detection". 

```json
{
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
```

<a id="DataSourceSpecificationExamples"></a>
### Data Source Specification Examples
The following examples all describe the exact same datasource.

A full configuration using no templates
```json
{
    "name": "Observations",
    "value_field": "observation",
    "value_selectors": [
        {
            "name": "observation",
            "where": "value",
            "path": ["values[*]", "value[*]", "value"],
            "datatype": "float",
            "origin": ["$", "value", "timeSeries[*]"],
            "associated_fields": [
                {
                    "name":"value_date",
                    "path": ["values[*]", "value[*]", "dateTime"],
                    "datatype": "datetime"
                },
                {
                    "name":"observation_location",
                    "path": ["sourceInfo", "siteCode", "[0]", "value"],
                    "datatype": "string"
                },
                {
                    "name":"unit",
                    "path": ["variable", "unit", "unitCode"],
                    "datatype": "string"
                }
            ]
        }
    ],
    "backend": {
        "backend_type": "file",
        "format": "json",
        "address": "resources/observations.json"
    },
    "locations": {
        "identify": true,
        "from_field": "value"
    },
    "unit": {
        "field": "unit"
    },
    "x_axis": "value_date"
}
```

A configuration using templates

```json
{
    "name": "Observations from Templates",
    "value_field": "observation",
    "value_selectors": [
        {
            "template_name": "NWIS Record"
        }
    ],
    "backend": {
        "template_name": "JSON File",
        "address": "resources/observations.json"
    },
    "locations": {
        "template_name": "From Value"
    },
    "unit": {
        "field": "unit"
    },
    "x_axis": "value_date"
}
```

A configuration using a mixture of manual configuration and templates:

```json
{
    "name": "Observations from Templates",
    "value_field": "observation",
    "value_selectors": [
        {
            "name": "observation",
            "where": "value",
            "path": ["values[*]", "value[*]", "value"],
            "datatype": "float",
            "origin": ["$", "value", "timeSeries[*]"],
            "associated_fields": [
                {
                    "name":"value_date",
                    "path": ["values[*]", "value[*]", "dateTime"],
                    "datatype": "datetime"
                },
                {
                    "name":"observation_location",
                    "path": ["sourceInfo", "siteCode", "[0]", "value"],
                    "datatype": "string"
                },
                {
                    "name":"unit",
                    "path": ["variable", "unit", "unitCode"],
                    "datatype": "string"
                }
            ]
        }
    ],
    "backend": {
        "template_name": "JSON File",
        "address": "resources/observations.json"
    },
    "locations": {
        "template_name": "From Value"
    },
    "unit": {
        "field": "unit"
    },
    "x_axis": "value_date"
}
```

<a id="EvaluationSpecificationExamples"></a>
### Evaluation Specification Examples

The following examples all describe the exact same evaluation:

A full configuration using no templates
```json
{
    "observations": [
        {
            "name": "Observations",
            "value_field": "observation",
            "value_selectors": [
                {
                    "name": "observation",
                    "where": "value",
                    "path": ["values[*]", "value[*]", "value"],
                    "datatype": "float",
                    "origin": ["$", "value", "timeSeries[*]"],
                    "associated_fields": [
                        {
                            "name":"value_date",
                            "path": ["values[*]", "value[*]", "dateTime"],
                            "datatype": "datetime"
                        },
                        {
                            "name":"observation_location",
                            "path": ["sourceInfo", "siteCode", "[0]", "value"],
                            "datatype": "string"
                        },
                        {
                            "name":"unit",
                            "path": ["variable", "unit", "unitCode"],
                            "datatype": "string"
                        }
                    ]
                }
            ],
            "backend": {
                "backend_type": "file",
                "format": "json",
                "address": "resources/observations.json"
            },
            "locations": {
                "identify": true,
                "from_field": "value"
            },
            "unit": {
                "field": "unit"
            },
            "x_axis": "value_date"
        }
    ],
    "predictions": [
        {
            "name": "Predictions",
            "value_field": "prediction",
            "value_selectors": [
                {
                    "name": "predicted",
                    "where": "column",
                    "associated_fields": [
                        {
                            "name": "date",
                            "datatype": "datetime"
                        }
                    ]
                }
            ],
            "backend": {
                "backend_type": "file",
                "format": "csv",
                "address": "resources/cat.*cfs.csv",
                "parse_dates": ["date"]
            },
            "locations": {
                "identify": true,
                "from_field": "filename",
                "pattern": "cat-\\d\\d"
            },
            "field_mapping": [
                {
                    "field": "prediction",
                    "map_type": "column",
                    "value": "predicted"
                },
                {
                    "field": "prediction_location",
                    "map_type": "column",
                    "value": "location"
                },
                {
                    "field": "value_date",
                    "map_type": "column",
                    "value": "date"
                }
            ],
            "unit": {
                "value": "ft^3/s"
            },
            "x_axis": "value_date"
        }
    ],
    "crosswalks": [
        {
            "name": "Crosswalk",
            "backend": {
                "backend_type": "file",
                "address": "resources/crosswalk.json",
                "format": "json"
            },
            "observation_field_name": "observation_location",
            "prediction_field_name": "prediction_location",
            "field": {
                "name": "prediction_location",
                "where": "key",
                "path": ["* where site_no"],
                "origin": "$",
                "datatype": "string",
                "associated_fields": [
                    {
                        "name": "observation_location",
                        "path": "site_no",
                        "datatype": "string"
                    }
                ]
            }
        }
    ],
    "thresholds": [
        {
            "name": "NWIS Stat Percentiles",
            "backend": {
                "name": "NWIS Stat Thresholds",
                "backend_type": "file",
                "format": "rdb",
                "address": "resources/nwis_stat_thresholds.rdb"
            },
            "locations": {
                "identify": true,
                "from_field": "column",
                "pattern": "site_no"
            },
            "application_rules": {
                "name": "Date to Day",
                "threshold_field": {
                    "name": "threshold_day",
                    "path": [
                        "month_nu",
                        "day_nu"
                    ],
                    "datatype": "Day"
                },
                "observation_field": {
                    "name": "threshold_day",
                    "path": [
                        "value_date"
                    ],
                    "datatype": "Day"
                }
            },
            "definitions": [
                {
                    "name": "75th Percentile",
                    "field": "p75_va",
                    "weight": 10,
                    "unit": {
                        "value": "ft^3/s"
                    }
                },
                {
                    "name": "80th Percentile",
                    "field": "p80_va",
                    "weight": 5,
                    "unit": {
                        "value": "ft^3/s"
                    }
                },
                {
                    "name": "Median",
                    "field": "p50_va",
                    "weight": 1,
                    "unit": {
                        "value": "ft^3/s"
                    }
                }
            ]
        }
    ],
    "scheme": {
        "name": "Prefer Pearson, then Nash and Kling, then POD and FAR",
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

A configuration using templates

```json
{
    "observations": [
        {
            "template_name": "REST Observations",
            "backend": {
                "params": {
                    "sites": "0214657975,0214655255",
                    "startDT": "2022-12-01T00:00%2b0000",
                    "endDT": "2022-12-31T00:00%2b0000"
                }
            }
        }
    ],
    "predictions": [
        {
            "template_name": "Predictions"
        }
    ],
    "crosswalks": [
        {
            "template_name": "Templated Crosswalk"
        }
    ],
    "thresholds": [
        {
            "template_name": "All Templates for NWIS Stat Percentiles"
        }
    ],
    "scheme": {
        "template_name": "Prefer Pearson, then Nash and Kling, then POD and FAR"
    }
}
```

A configuration using templates with overridden values

```json
{
    "observations": [
        {
            "template_name": "Observations from Templates"
        }
    ],
    "predictions": [
        {
            "template_name": "Predictions"
        }
    ],
    "crosswalks": [
        {
            "template_name": "Templated Crosswalk"
        }
    ],
    "thresholds": [
        {
            "template_name": "All Templates for NWIS Stat Percentiles"
        }
    ],
    "scheme": {
        "template_name": "Prefer Pearson, then Nash and Kling, then POD and FAR"
    }
}
```

<a id="all-elements"></a>
## All Elements

When put together, the entire object tree looks like:

![All Specifications](../../../images/all-from-dmod.evaluations.specification.png)