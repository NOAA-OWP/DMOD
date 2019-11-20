"""
Defines a view that may be used to configure a MaaS request
"""
import asyncio
import json
import os
import pathlib
import ssl
import websockets
from .. import MaaSRequest
from ..validator import JsonAuthRequestValidator, JsonJobRequestValidator
from django.http import HttpRequest, HttpResponse
from django.views.generic.base import View
from django.shortcuts import render


class RequestFormProcessor:
    """
    Class that receives and HTTP POST request of the form submission for a desired job, and converts this to a
    MaasRequest to be submitted.
    """
    def __init__(self, post_request: HttpRequest, maas_secret):
        """The HttpRequest received, used to submit the form for the job to request from the MaaS."""
        self.post_request = post_request
        self._errors = None
        self.warnings = list()
        self.info = list()
        self.model = post_request.POST['model']
        self.version = float(post_request.POST['version'])
        self.output = post_request.POST['output']
        self.maas_secret = maas_secret
        self._maas_request = None

        # This will give us the parameters that were configured for the model we want to use
        # If we configured that we want to tweak 'example_parameter' for the model named 'YetAnother',
        # then change our minds and decide to tweak 'land_cover' for the 'NWM' model, this will filter
        # out the configuration from 'YetAnother'
        self.parameter_keys = [
            parameter
            for parameter in post_request.POST
            if post_request.POST[parameter] == 'on' and parameter.startswith(self.model)
        ]

        self._parameters = None
        self._maas_request = None

    def _init_parameters(self):
        """
        Initialize the :attr:`_parameters` mapping object from the parameters of this instance's :attr:`request`, which
        also results in the :attr:`_errors` list being initialized.
        """
        self._parameters = dict()
        self._errors = list()
        # We want to form all of the proper Scalar and Distribution configurations
        for parameter in self.parameter_keys:
            # We first grab the human readable name if we want to write out any messages
            human_name = " ".join(parameter.replace(self.model + "_", "").split("_")).title()

            # Form the keys that will be in the POST mapping that will lead us to our desired values
            scalar_name_key = parameter + "_scalar"
            distribution_min_key = parameter + "_distribution_min"
            distribution_max_key = parameter + "_distribution_max"
            distribution_type_key = parameter + "_distribution_type"

            parameter_type_key = parameter + "_parameter_type"
            parameter_type = self.post_request.POST[parameter_type_key]

            # If the parameter was configured to be a distribution, we want to process that here
            if parameter_type == 'distribution':
                distribution_min_value = self.post_request.POST[distribution_min_key]
                distribution_max_value = self.post_request.POST[distribution_max_key]
                distribution_type_value = self.post_request.POST[distribution_type_key]

                # If a value was missing, create a message for it and move on since it can't be used
                if distribution_type_value == '' or distribution_max_value == '' or distribution_min_value == '':
                    self._errors.append("All distribution values for {} must be set.".format(human_name))
                    continue

                # Create the distribution and add it to the list
                distribution = MaaSRequest.Distribution(
                    int(distribution_min_value),
                    int(distribution_max_value),
                    distribution_type_value
                )
                self._parameters[parameter.replace(self.model + "_", "")] = distribution
            else:
                # Otherwise we want to create a Scalar configuration
                scalar_value = self.post_request.POST[scalar_name_key]

                # If the user wants a scalar, but didn't provide a value, we create a message to send back to them
                if scalar_value == '':
                    self._errors.append("A scalar value for {} must be set".format(human_name))
                    # Move on since this parameter was proven to be bunk
                    continue

                # Create the Scalar and add it to the list
                scalar = MaaSRequest.Scalar(int(scalar_value))
                self._parameters[parameter.replace(self.model + "_", "")] = scalar

    @property
    def errors(self):
        return self._errors

    @property
    def maas_request(self):
        if self._maas_request is None:
            if len(self.errors) == 0:
                self._maas_request = MaaSRequest.get_request(self.model, self.version, self.output, self.parameters,
                                                             self.maas_secret)
        return self._maas_request

    @property
    def parameters(self):
        if self._parameters is None:
            self._init_parameters()
        return self._parameters


class EditView(View):

    @staticmethod
    async def _authenticate_over_websocket(websocket):
        # Right now, it doesn't matter as long as it is valid
        json_msg = json.loads({'username': 'someone', 'user_secret': 'something'})
        # TODO: validate before sending
        await websocket.send(json.dumps(json_msg))
        auth_response = await websocket.recv()
        data = json.loads(auth_response)
        maas_session_id = data['session_id']
        maas_session_secret = data['session_secret']
        maas_session_created = data['created']
        return maas_session_id, maas_session_secret, maas_session_created

    @property
    def client_ssl_context(self):
        if not hasattr(self, '_client_ssl_context') or self._client_ssl_context is None:
            current_dir = pathlib.Path(__file__).resolve().parent
            self._client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            endpoint_pem = current_dir.parent.parent.joinpath('ssl', 'certificate.pem')
            host_name = os.environ.get('MAAS_ENDPOINT_HOST')
            print("***** Endpoint PEM: " + str(endpoint_pem) + '*******')
            self._client_ssl_context.load_verify_locations(endpoint_pem)
        return self._client_ssl_context

    @property
    def maas_endpoint_uri(self):
        if not hasattr(self, '_maas_endpoint_uri') or self._maas_endpoint_uri is None:
            self._maas_endpoint_uri = 'wss://' + os.environ.get('MAAS_ENDPOINT_HOST') + ':'
            self._maas_endpoint_uri += os.environ.get('MAAS_ENDPOINT_PORT')
            print("**************** Endpoint: " + self._maas_endpoint_uri + " ****************")
        return self._maas_endpoint_uri

    """
    A view used to configure a MaaS request
    """
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The handler for 'get' requests.  This will render the 'edit.html' template with all models, all
        possible model outputs, the parameters that are configurable on each model, distribution types
        that may be used on each, and any sort of necessary messages

        :param HttpRequest request: The request asking to render this page
        :param args: An ordered list of arguments
        :param kwargs: A dictionary of named arguments
        :return: A rendered page
        """
        # If a list of error messages wasn't passed, create one
        if 'errors' not in kwargs:
            errors = list()
        else:
            # Otherwise continue to use the passed in list
            errors = kwargs['errors']  # type: list

        # If a list of warning messages wasn't passed create one
        if 'warnings' not in kwargs:
            warnings = list()
        else:
            # Otherwise continue to use the passed in list
            warnings = kwargs['warnings']  # type: list

        # If a list of basic messages wasn't passed, create one
        if 'info' not in kwargs:
            info = list()
        else:
            # Otherwise continue to us the passed in list
            info = kwargs['info']  # type: list

        # Define a function that will make words friendlier towards humans. Text like 'hydro_whatsit' will
        # become 'Hydro Whatsit'
        def humanize(words: str) -> str:
            split = words.split("_")
            return " ".join(split).title()

        models = list(MaaSRequest.get_available_models().keys())
        outputs = list()
        distribution_types = list()

        # Create a mapping between each output type and a friendly representation of it
        for output in MaaSRequest.get_available_outputs():
            output_definition = dict()
            output_definition['name'] = humanize(output)
            output_definition['value'] = output
            outputs.append(output_definition)

        # Create a mapping between each distribution type and a friendly representation of it
        for distribution_type in MaaSRequest.get_distribution_types():
            type_definition = dict()
            type_definition['name'] = humanize(distribution_type)
            type_definition['value'] = distribution_type
            distribution_types.append(type_definition)

        # Package everything up to be rendered for the client
        payload = {
            'models': models,
            'outputs': outputs,
            'parameters': MaaSRequest.get_parameters(),
            'distribution_types': distribution_types,
            'errors': errors,
            'info': info,
            'warnings': warnings
        }

        # Return the rendered page
        return render(request, 'maas/edit.html', payload)

    async def authenticate_over_websocket(self):
        async with websockets.connect(self.maas_endpoint_uri, ssl=self.client_ssl_context) as websocket:
        #async with websockets.connect(self.maas_endpoint_uri) as websocket:
            # return await EditView._authenticate_over_websocket(websocket)
            # Right now, it doesn't matter as long as it is valid
            json_as_dict = {'username': 'someone', 'user_secret': 'something'}
            # TODO: validate before sending
            await websocket.send(json.dumps(json_as_dict))
            auth_response = await websocket.recv()
            data = json.loads(auth_response)
            maas_session_id = data['session_id']
            maas_session_secret = data['session_secret']
            maas_session_created = data['created']
            return maas_session_id, maas_session_secret, maas_session_created

    async def make_job_request(self, maas_request: MaaSRequest):
        async with websockets.connect(self.maas_endpoint_uri, ssl=self.client_ssl_context) as websocket:
            await websocket.send(maas_request.to_json)
            response = await websocket.recv()
            return json.dumps(response)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The handler for 'post' requests. This will attempt to submit the request and rerender the page
        like a 'get' request

        :param HttpRequest request: The request asking to render this page
        :param args: An ordered list of arguments
        :param kwargs: A dictionary of named arguments
        :return: A rendered page
        """

        if 'maas_session_secret' in request.COOKIES.keys():
            maas_session_id = request.COOKIES['maas_session_id']
            maas_session_secret = request.COOKIES['maas_session_secret']
            maas_session_created = request.COOKIES['maas_session_created']
        else:
            maas_session_id, maas_session_secret, maas_session_created = asyncio.get_event_loop().run_until_complete(
                self.authenticate_over_websocket())

        form_processor = RequestFormProcessor(post_request=request, maas_secret=maas_session_secret)
        maas_request = form_processor.maas_request

        is_valid, error = JsonJobRequestValidator().validate_request(maas_request.to_dict())

        if is_valid:
            # TODO: validate responses also
            req_response_json = asyncio.get_event_loop().run_until_complete(self.make_job_request(maas_request))
            # TODO: display this perhaps, or do something with it
            job_id = req_response_json['data']['job_id']
        else:
            job_id = None

    #post_proc.send_request_to_handler()

        # errors = list()
        # warnings = list()
        # info = list()
        # model = request.POST['model']
        # version = float(request.POST['version'])
        # output = request.POST['output']
        #
        # # This will give us the parameters that were configured for the model we want to use
        # # If we configured that we want to tweak 'example_parameter' for the model named 'YetAnother',
        # # then change our minds and decide to tweak 'land_cover' for the 'NWM' model, this will filter
        # # out the configuration from 'YetAnother'
        # parameter_keys = [
        #     parameter
        #     for parameter in request.POST
        #     if request.POST[parameter] == 'on' and parameter.startswith(model)
        # ]
        #
        # parameters = dict()
        #
        # # We want to form all of the proper Scalar and Distribution configurations
        # for parameter in parameter_keys:
        #     # We first grab the human readable name if we want to write out any messages
        #     human_name = " ".join(parameter.replace(model + "_", "").split("_")).title()
        #
        #     # Form the keys that will be in the POST mapping that will lead us to our desired values
        #     scalar_name_key = parameter + "_scalar"
        #     distribution_min_key = parameter + "_distribution_min"
        #     distribution_max_key = parameter + "_distribution_max"
        #     distribution_type_key = parameter + "_distribution_type"
        #
        #     parameter_type_key = parameter + "_parameter_type"
        #     parameter_type = request.POST[parameter_type_key]
        #
        #     # If the parameter was configured to be a distribution, we want to process that here
        #     if parameter_type == 'distribution':
        #         distribution_min_value = request.POST[distribution_min_key]
        #         distribution_max_value = request.POST[distribution_max_key]
        #         distribution_type_value = request.POST[distribution_type_key]
        #
        #         # If a value was missing, create a message for it and move on since it can't be used
        #         if distribution_type_value == '' or distribution_max_value == '' or distribution_min_value == '':
        #             errors.append("All distribution values for {} must be set.".format(human_name))
        #             continue
        #
        #         # Create the distribution and add it to the list
        #         distribution = MaaSRequest.Distribution(
        #             int(distribution_min_value),
        #             int(distribution_max_value),
        #             distribution_type_value
        #         )
        #         parameters[parameter.replace(model + "_", "")] = distribution
        #     else:
        #         # Otherwise we want to create a Scalar configuration
        #         scalar_value = request.POST[scalar_name_key]
        #
        #         # If the user wants a scalar, but didn't provide a value, we create a message to send back to them
        #         if scalar_value == '':
        #             errors.append("A scalar value for {} must be set".format(human_name))
        #             # Move on since this parameter was proven to be bunk
        #             continue
        #
        #         # Create the Scalar and add it to the list
        #         scalar = MaaSRequest.Scalar(int(scalar_value))
        #         parameters[parameter.replace(model + "_", "")] = scalar
        #
        # now = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
        #
        # # If everything went smoothly and there weren't any errors, attempt to send the request
        # if len(errors) == 0:
        #     try:
        #         # Form the request object
        #         maas_request = MaaSRequest.get_request(model, version, output, parameters)
        #
        #         # Print it to the terminal so we can see what it generated
        #         # TODO: Remove once this pretty much does what we want it to do
        #         print(maas_request.to_json())
        #
        #         # Attempt to send the request
        #         response = dispatch.dispatch(maas_request)
        #
        #         if response.status_code < 400:
        #             # Add a message confirming that the request went through so the user knows what's going on
        #             info.append("Request submitted.")
        #
        #             # TODO: Add handling of a websocket here if we want that
        #         else:
        #             # This is pretty primitive and we don't necessarily want to expose the user to this sort of
        #             # implementation detail, but we send the message explaining the issue
        #             message = "Request could not be made to MaaS; {}: {}".format(response.status_code, response.reason)
        #             errors.append(message)
        #
        #             message = "[{}]: {}".format(now, message)
        #             sys.stderr.write(message)
        #             print(message)
        #     except Exception as error:
        #         errors.append(str(error))
        #
        #         message = "[{}]: {}".format(now, str(error))
        #         sys.stderr.write(message)
        #         print(message)

        # Rerender the page
        response = self.get(request, errors=form_processor.errors, warnings=form_processor.warnings, info=form_processor.info, *args, **kwargs)
        response.set_cookie('maas_session_id', maas_session_id)
        response.set_cookie('maas_session_secret', maas_session_secret)
        response.set_cookie('maas_session_created', maas_session_created)
        if job_id is not None:
            response.set_cookie('maas_job_id', job_id)
        return response