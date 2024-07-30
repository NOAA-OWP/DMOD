# API

The following API is exposed by this package for obtaining subsets.

## Validating Catchment ID

This endpoint can be used to check whether some catchment id is a recognized catchment id in the service's current hydrofabric.

* Endpoint: `/subset/cat_id_valid`
* Message: POST
* JSON Format: `{"id" : "<catchment_id>"}`
* Response: `{"catchment_id": "<catchment_id>", "valid": <bool>}`

## Get Subset for Given Catchments

This endpoint can be used to get a subset of a provided collection of catchments, _AND_ each's immediate downstream nexus.

* Endpoint: `/subset/for_cat_id`
* Message: POST
* JSON Format:
  * `{"ids" : "[<catchment_id>]"}`
  * `{"ids" : "[<catchment_id_1>, <catchment_id_2>, ...]"}`
* Response:
  * `{"catchment_ids": "[<catchment_id_1>, ...]", "nexus_ids": [<nexus_id_1>, ...]}`

## Get Upstream Subset for Given Catchments

This endpoint can be used to get an upstream subset.  For a single catchment, the upstream subset is the catchment, its upstream nexus, the catchments upstream for that nexus, etc., as far as this network can be traveled.  Multiple starting catchments can be supplied, in which case the network for each is individually traveled, and then these are combined.

* Endpoint: `/subset/upstream`
* Message: POST
* JSON Format:
    * `{"ids" : "[<catchment_id>]"}`
    * `{"ids" : "[<catchment_id_1>, <catchment_id_2>, ...]"}`
* Response:
    * `{"catchment_ids": "[<catchment_id_1>, ...]", "nexus_ids": [<nexus_id_1>, ...]}`