"""
Defines a view that may be used to execute models on different frameworks
"""

import json
import logging

from typing import Dict
from typing import Tuple

from django.conf import settings

from django.http import HttpRequest, QueryDict
from django.http import JsonResponse

from rest_framework.views import APIView

from dmod.communication import ExternalRequestResponse

from .. import processors
from ..client import JobRequestClient
from datetime import datetime
import re

LOGGER = logging.getLogger("gui_log")


# A cache for JobRequestClients; key is (Framework, Address of endpoint)
CLIENTS: Dict[Tuple[str, str], JobRequestClient] = dict()


def get_client(framework: str, endpoint_uri: str = None) -> JobRequestClient:
    """
    Either get a preexisting JobRequestClient from the cache or create and add one.

    The key for the cache is (framework, endpoint_uri)

    Parameters
    ----------
    framework : str
        The name of the modelling framework to use
    endpoint_uri : str
        The optional endpoint to attempt to communicate with. The configured endpoint for the server will be used if
        one isn't specified

    Returns
    -------
    JobRequestClient
        A client through which jobs may be issued
    """
    if framework in CLIENTS:
        client = CLIENTS[(framework, endpoint_uri)]
    else:
        processor = processors.get_processor(framework)

        client = JobRequestClient(
            processor=processor,
            endpoint_uri=settings.GET_MAAS_ENDPOINT(framework) if endpoint_uri is None else endpoint_uri
        )
        CLIENTS[(framework, endpoint_uri)] = client

    return client


class Execute(APIView):
    """
    API view for executing a configured model on a specified framework
    """

    def _parse_post_keys(self, data: dict, feature_key: str, formulation_key: str) -> dict:
        applicable = dict()

        applicable['formulation-type'] = formulation_key
        applicable['forcing-pattern'] = data['{}-forcing-pattern'.format(feature_key)]

        properties_to_retype = dict()

        #property_key_pattern = re.compile(r'(' + feature_key + '):::([^:].+[^:]):::([^:].+[^:])(::([^:].+))?')
        property_key_pattern = re.compile(r'(' + feature_key + '):::(.+?):::(.+)')
        meta_property_subpattern = re.compile(r'(.+):::(.+)')

        for k, value in data.items():
            if value == '':
                continue

            match_obj = property_key_pattern.match(k)
            if match_obj is None:
                continue

            matched_feature = match_obj.group(1)
            matched_form = match_obj.group(2)

            # Skip if no match, or if either the matched feature or formulation is not of interest
            if matched_feature != feature_key or matched_form != formulation_key:
                continue

            prop_meta_match_obj = meta_property_subpattern.match(match_obj.group(3))
            if prop_meta_match_obj is None:
                applicable[match_obj.group(3)] = value
            elif prop_meta_match_obj.group(2) == 'config-type':
                properties_to_retype[prop_meta_match_obj.group(1)] = value

        for prop_key, type_str in properties_to_retype.items():
            if type_str.lower() == 'text' or prop_key not in applicable:
                continue
            if type_str.lower() == 'number':
                applicable[prop_key] = float(applicable[prop_key])
            elif type_str.lower() == 'numbers':
                applicable[prop_key] = [float(s.strip()) for s in applicable[prop_key].split(',')]
            elif type_str.lower() == 'list':
                applicable[prop_key] = [s.strip() for s in applicable[prop_key].split(',')]

        return applicable

    def _parse_config_request(self, post_data: QueryDict) -> dict:
        features = post_data['features'].split('|')
        formulations_map = json.loads(post_data['formulations'])

        global_formulation_key = formulations_map[post_data['global-formulation-type']]

        # TODO: add other properties besides formulations configs (e.g., list of features)
        config_properties = dict()
        config_properties['features'] = features
        config_properties['cpu_count'] = post_data['requested-cpu-count']
        config_properties['start'] = datetime.strptime(post_data['start-time'], settings.DATE_TIME_FORMAT)
        config_properties['end'] = datetime.strptime(post_data['end-time'], settings.DATE_TIME_FORMAT)
        feature_configs = dict()
        feature_configs['global'] = self._parse_post_keys(data=post_data, feature_key='global', formulation_key=global_formulation_key)

        for feature in features:
            formulation_type_key = post_data['{}-formulation-type'.format(feature)]
            if formulation_type_key == 'global':
                continue
            formulation_type = formulations_map[formulation_type_key]
            feature_configs[feature] = self._parse_post_keys(data=post_data, feature_key=feature, formulation_key=formulation_type)

        config_properties['formulations'] = feature_configs
        return config_properties

    def post(self, request: HttpRequest):
        """
        The post handler

        Gets a client, forms a request based on it, issues said request, and returns metadata for said job

        Parameters
        ----------
        request
            The HttpRequest that called the API

        Returns
        -------
        JsonResponse
            JSON describing the state of the job that is run
        """
        # Output debugging information for development and diagnostics
        LOGGER.debug("Request for model run:")
        LOGGER.debug(json.dumps(request.POST, indent=4))

        # Get the appropriate framework that the configuration will be run on
        framework = request.POST.get("framework", None)

        # Nothing can be done if a framework isn't found, so go ahead and thrown an error
        if framework is None or framework == "":
            raise ValueError("No model type was passed into the configuration compiler")
        elif framework not in processors.get_processor_types():
            # Throw an error if there isn't a valid processor for the framework
            raise ValueError("'{}' is not a valid model framework".format(framework))

        # Grab the client that the model run will be routed through
        client = get_client(framework, request.POST.get("endpoint_uri", None))

        # Allow the caller to determine whether or not a new session should be created
        force_new_session = request.POST.get("force_new_session", False)

        framework_name = request.POST.get('framework', None)

        if framework_name == 'ngen':
            parsed_config = self._parse_config_request(request.POST)
            # TODO: implement to process config details from GUI, creating any necessary realization config datasets
            required_datasets_names = self._process_ngen_configuration_into_datasets(parsed_config)
        else:
            raise RuntimeError('Unsupported framework {}'.format(None))

        # Issue the request
        # TODO: modify the way client makes requires to be regular client
        response: ExternalRequestResponse = client.make_maas_request(request, force_new_session)

        # Throw an error if the request could not be successfully issued
        if response is None:
            raise Exception("A request could not be issued.")

        # Get the data from the response and wrap it in a response object that is easy for humans and applications to
        # parse
        http_response = JsonResponse(data=response.to_dict())

        # Set a cookie if a job was started and we have the id (rely on client to manage multiple job ids)
        if response is not None and 'job_id' in response.data:
            # TODO: make sure that the client displays this job id somehow
            http_response.set_cookie('new_job_id', response.data['job_id'])

        # Set cookies if a new session was acquired
        if client.is_new_session:
            http_response.set_cookie('maas_session_id', client.session_id)
            http_response.set_cookie('maas_session_secret', client.session_secret)
            http_response.set_cookie('maas_session_created', client.session_created)

        return http_response
