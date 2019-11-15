"""
Handles everything needed to send the request to the MaaS
"""
import os

import requests
import json

from . import MaaSRequest
from . import validator


def dispatch(maas_request: MaaSRequest) -> requests.Response:
    """
    Sends the request to the configured endpoint for the MaaS

    :param MaaSRequest.MaaSRequest maas_request: The configured request
    :return: The response from the web request
    """
    # Use the validator as a final check to see if everything is valid
    validator.validate_request(json.loads(maas_request.to_json()))

    # Get the proper endpoint and path to the certificate
    endpoint = os.environ.get("MAAS_ENDPOINT", None)
    #endpoint = "https://***REMOVED***
    cert_path = os.environ.get("CERT_PATH", False)

    # If we can't find an endpoint, we can't do anything, so exit out
    if endpoint is None:
        raise ReferenceError("No MaaS endpoint is available")

    # Convert the request object to a context object
    configuration = maas_request.to_dict()

    # Send out the http request
    return requests.post(endpoint, verify=cert_path, json=configuration)