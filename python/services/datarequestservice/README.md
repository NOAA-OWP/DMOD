# API

The following API is exposed by this package for obtaining subsets.

## Validating Catchment ID

This endpoint can be used to check whether some catchment id is a recognized catchment id in the service's current hydrofabric.

* Endpoint: `/datarequest/valid`
* Message: POST
* JSON Format: `{"data_sources" : "<source-id>", "start_dates" : "%m/%d/%y: %H:%M:%S %Z", "stop_dates" : "%m/%d/%y: %H:%M:%S %Z", "variables" : ["<required-variables>"] }`
* Response: `{ "valid": <bool>}`
