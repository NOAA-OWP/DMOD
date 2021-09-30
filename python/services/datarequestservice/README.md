# API

The following API is exposed by this package for obtaining subsets.

## Validating Catchment ID

This endpoint can be used to check whether some catchment id is a recognized catchment id in the service's current hydrofabric.

* Endpoint: `/datarequest/valid`
* Message: POST
* JSON Format: `{"data-provider" : "<provider-id>", "start_date" : <start_date>, "stop-date" : <stop_date>, "required-variables" : <required-variables> }`
* Response: `{ "valid": <bool>}`


