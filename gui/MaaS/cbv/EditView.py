"""
Defines a view that may be used to configure a MaaS request
"""
import asyncio
import json
import os
import pathlib
import ssl
import traceback
import websockets
from .. import MaaSRequest
from ..validator import JsonAuthRequestValidator, JsonJobRequestValidator
from abc import ABC, abstractmethod
from django.http import HttpRequest, HttpResponse
from django.views.generic.base import View
from django.shortcuts import render


class RequestFormProcessor:
    """
    Class that receives an HTTP POST request of the form submission for a desired job, and converts this to a
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
        self._is_valid = None
        self._validation_error = None

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
    def errors(self) -> list:
        if self._errors is None:
            self._init_parameters()
        return self._errors

    @property
    def is_valid(self) -> bool:
        """
        Return whether the MaaS job request represented by :attr:post_request is valid, lazily perform validation if it
        has not already been done.

        Returns
        -------
        bool
            whether the MaaS job request represented by :attr:post_request is valid
        """
        if self._is_valid is None:
            self._is_valid, self._validation_error = JsonJobRequestValidator().validate_request(
                self.maas_request.to_dict())
        return self._is_valid

    @property
    def maas_request(self) -> MaaSRequest:
        """
        Get the :obj:MaaSRequest instance (which could be a subclass of this type) represented by :attr:post_request,
        lazily instantiating the former if necessary.

        Returns
        -------
        :obj:MaaSRequest
            the :obj:MaaSRequest instance represented by :attr:post_request
        """
        if self._maas_request is None:
            if len(self.errors) == 0:
                self._maas_request = MaaSRequest.get_request(self.model, self.version, self.output, self.parameters,
                                                             self.maas_secret)
        return self._maas_request

    @property
    def parameters(self) -> dict:
        if self._parameters is None:
            self._init_parameters()
        return self._parameters

    @property
    def validation_error(self):
        """
        Return any error encountered when validating the MaaS job request represented by :attr:post_request, performing
        a call to the :attr:is_valid property to ensure validation has been performed.

        Returns
        -------
        Any error encountered during validation
        """
        lazy_load_if_needed_via_side_effect_of_this_property = self.is_valid
        return self._validation_error


class JobRequestClient(ABC):

    def __init__(self, endpoint_uri: str):
        self.endpoint_uri = endpoint_uri

        self._client_ssl_context = None
        current_dir = pathlib.Path(__file__).resolve().parent
        self.client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        endpoint_pem = current_dir.parent.parent.joinpath('ssl', 'certificate.pem')
        host_name = os.environ.get('MAAS_ENDPOINT_HOST')
        self.client_ssl_context.load_verify_locations(endpoint_pem)

        # TODO: get full session implementation if possible
        self._session_id, self._session_secret, self._session_created, self._is_new_session = None, None, None, None

        self._maas_job_request = None
        self._errors = None
        self._warnings = None
        self._info = None
        self.resp_as_json = None
        self.job_id = None

    async def async_send_job_request(self, maas_request: MaaSRequest):
        async with websockets.connect(self.endpoint_uri, ssl=self.client_ssl_context) as websocket:
            await websocket.send(maas_request.to_json())
            response = await websocket.recv()
            # return json.dumps(response)
            return response

    # TODO: ...
    async def authenticate_over_websocket(self):
        async with websockets.connect(self.endpoint_uri, ssl=self.client_ssl_context) as websocket:
            #async with websockets.connect(self.maas_endpoint_uri) as websocket:
            # return await EditView._authenticate_over_websocket(websocket)
            # Right now, it doesn't matter as long as it is valid
            # TODO: Fix this to not be ... fixed ...
            json_as_dict = {'username': 'someone', 'user_secret': 'something'}
            # TODO: validate before sending
            await websocket.send(json.dumps(json_as_dict))
            auth_response = json.loads(await websocket.recv())
            print('*************** Auth response: ' + json.dumps(auth_response))
            maas_session_id = auth_response['data']['session_id']
            maas_session_secret = auth_response['data']['session_secret']
            maas_session_created = auth_response['data']['created']
            return maas_session_id, maas_session_secret, maas_session_created

    def _acquire_session_info(self, force_new: bool = False):
        """
        Attempt to set the session information properties needed to submit a maas job request.

        Attempt to set the session information properties needed to submit a maas job request represented by the
        HttpRequest in :attr:http_request, either from the cookies of the HttpRequest or by authenticating and obtaining
        a new session from the request handler.

        Parameters
        ----------
        force_new
            whether to force acquiring details for a new session, regardless of data available in cookies from the request

        Returns
        -------
        bool
            whether session details were acquired and set successfully
        """
        self._is_new_session = False
        if not force_new and 'maas_session_secret' in self.http_request.COOKIES.keys():
            self._session_id = self.http_request.COOKIES['maas_session_id']
            self._session_secret = self.http_request.COOKIES['maas_session_secret']
            self._session_created = self.http_request.COOKIES['maas_session_created']
            return True
        else:
            try:
                auth_details = asyncio.get_event_loop().run_until_complete(self.authenticate_over_websocket())
                self._session_id, self._session_secret, self._session_created = auth_details
                self._is_new_session = True
                return True
            except:
                return False

    def _get_validation_error(self):
        is_valid, error = JsonJobRequestValidator().validate_request(self.maas_job_request.to_dict())
        return error

    @abstractmethod
    def _init_maas_job_request(self):
        pass

    def _is_maas_job_request_valid(self):
        is_valid, error = JsonJobRequestValidator().validate_request(self.maas_job_request.to_dict())
        return is_valid

    def _job_request_failed_due_to_expired_session(self):
        """
        Test if the response to a websocket sent request in :attr:resp_as_json failed specifically because the utilized
        session was valid, but no longer suitably authorized, indicating that it may make sense to try to authenticate a
        new session for the request and try again (i.e., it may, assuming this problem didn't occur when already using a
        freshly acquired session.)

        Returns
        -------
        bool
            whether a failure occur and it specifically was due to a lack of authorization over the used session
        """
        return self.resp_as_json is not None \
               and not self.resp_as_json['success'] \
               and self.resp_as_json['reason'] == 'Unauthorized' \
               and not self._is_new_session

    @property
    @abstractmethod
    def errors(self):
        pass

    @property
    @abstractmethod
    def info(self):
        pass

    @property
    def is_new_session(self):
        return self._is_new_session

    @property
    def maas_job_request(self):
        if self._maas_job_request is None:
            self._maas_job_request = self._init_maas_job_request()
        return self._maas_job_request

    def make_job_request(self, force_new_session: bool = False):
        self._acquire_session_info(force_new=force_new_session)
        # If able to get session details, proceed with making a job request
        if self._session_secret is not None:
            print("******************* Request: " + self.maas_job_request.to_json())
            if self._is_maas_job_request_valid():
                try:
                    req_response = asyncio.get_event_loop().run_until_complete(self.async_send_job_request(self.maas_job_request))
                    self.resp_as_json = json.loads(req_response)
                    print('***************** Response: ' + req_response)
                    if not self.validate_job_request_response():
                        raise RuntimeError('Invalid response received for requested job: ' + str(req_response))
                    # Try to get a new session if unauthorized (and we hadn't already gotten a new session)
                    elif self._job_request_failed_due_to_expired_session():
                        # Clear to we can try again with updated secret
                        self._maas_job_request = None
                        return self.make_job_request(force_new_session=True)
                    elif not self.resp_as_json['success']:
                        template = 'Request failed (reason: {}): {}'
                        raise RuntimeError(template.format(self.resp_as_json['reason'], self.resp_as_json['message']))
                    else:
                        self.job_id = self.resp_as_json['data']['job_id']
                except Exception as e:
                    # TODO: log error instead of print
                    msg = 'Encountered error submitting maas job request over session ' + str(self._session_id)
                    msg += " : \n" + str(type(e)) + ': ' + str(e)
                    print(msg)
                    traceback.print_exc()
                    self.errors.append(msg)
            else:
                msg = 'Could not submit invalid maas job request over session ' + str(self._session_id)
                msg += ' (' + str(self._get_validation_error()) + ')'
                print(msg)
                self.errors.append(msg)
        else:
            self.errors.append("Unable to acquire session details or authenticate new session for request")

    @property
    def session_created(self):
        return self._session_created

    @property
    def session_id(self):
        return self._session_id

    @property
    def session_secret(self):
        return self._session_secret

    def validate_job_request_response(self):
        # TODO: implement
        return True

    @property
    @abstractmethod
    def warnings(self):
        pass


class PostFormJobRequestClient(JobRequestClient):
    """
    A client for websocket interaction with the MaaS request handler, specifically for performing a job request based on
    details provided in a particular HTTP POST request (i.e., with form info on the parameters of the job execution).
    """

    def __init__(self, endpoint_uri: str, http_request: HttpRequest):
        super().__init__(endpoint_uri=endpoint_uri)
        self.http_request = http_request
        self.form_proc = None

    def _init_maas_job_request(self):
        """
        Set or reset the :attr:`form_proc` field and return its :attr:`RequestFormProcessor`.`maas_request` property.

        Returns
        -------
        The processed maas request from the newly initialized form processor in :attr:`form_proc`
        """
        self.form_proc = RequestFormProcessor(post_request=self.http_request, maas_secret=self.session_secret)
        return self.form_proc.maas_request

    @property
    def errors(self):
        if self._errors is None:
            self._errors = [self.form_proc.errors] if self.form_proc is not None else []
        return self._errors

    @property
    def info(self):
        if self._info is None:
            self._info = [self.form_proc.info] if self.form_proc is not None else []
        return self._info


    # def old_make_job_request(self, force_new_session: bool = False):
    #     """
    #
    #     Parameters
    #     ----------
    #     force_new_session
    #
    #     Returns
    #     -------
    #     tuple
    #         A tuple with the generated :obj:RequestFormProcessor used to handle processing POST request params and the
    #         response from the websocket request as a deserialized JSON object (or None if this failed or wasn't tried)
    #     """
    #     resp_as_json = None
    #     self._acquire_session_info(force_new=force_new_session)
    #     form_proc = RequestFormProcessor(post_request=self.http_request, maas_secret=self._session_secret)
    #     # If able to get session details, proceed with making a job request
    #     if self._session_secret is not None:
    #         print("******************* Request: " + form_proc.maas_request.to_json())
    #         if form_proc.is_valid:
    #             try:
    #                 req_response = asyncio.get_event_loop().run_until_complete(
    #                     self.async_send_job_request(form_proc.maas_request))
    #                 resp_as_json = json.loads(req_response)
    #                 print('***************** Response: ' + req_response)
    #                 # TODO: validate responses also
    #                 # Try to get a new session if unauthorized (and we hadn't already gotten a new session)
    #                 if self._job_request_failed_due_to_expired_session(resp_as_json):
    #                     return self.make_job_request(force_new_session=True)
    #                 elif not resp_as_json['success']:
    #                     raise RuntimeError('Request failed (reason: ' + resp_as_json['reason'] + '): ' + resp_as_json['message'])
    #                 else:
    #                     self.job_id = resp_as_json['data']['job_id']
    #             except Exception as e:
    #                 # TODO: log error instead of print
    #                 msg = 'Encountered error submitting maas job request over session ' + str(self._session_id)
    #                 msg += " : \n" + str(type(e)) + ': ' + str(e)
    #                 print(msg)
    #                 traceback.print_exc()
    #                 form_proc.errors.append(msg)
    #         else:
    #             msg = 'Could not submit invalid maas job request over session ' + str(self._session_id)
    #             msg += ' (' + str(form_proc.validation_error) + ')'
    #             print(msg)
    #             form_proc.errors.append(msg)
    #     else:
    #         form_proc.errors.append("Unable to acquire session details or authenticate new session for request")
    #
    #     return form_proc, resp_as_json

    @property
    def warnings(self):
        if self._warnings is None:
            self._warnings = [self.form_proc.warnings] if self.form_proc is not None else []
        return self._warnings


class EditView(View):

    @property
    def maas_endpoint_uri(self):
        if not hasattr(self, '_maas_endpoint_uri') or self._maas_endpoint_uri is None:
            self._maas_endpoint_uri = 'wss://' + os.environ.get('MAAS_ENDPOINT_HOST') + ':'
            self._maas_endpoint_uri += os.environ.get('MAAS_ENDPOINT_PORT')
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
            
    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The handler for 'post' requests. This will attempt to submit the request and rerender the page
        like a 'get' request

        :param HttpRequest request: The request asking to render this page
        :param args: An ordered list of arguments
        :param kwargs: A dictionary of named arguments
        :return: A rendered page
        """
        request_client = PostFormJobRequestClient(endpoint_uri=self.maas_endpoint_uri, http_request=request)

        request_client.make_job_request(force_new_session=False)

        http_response = self.get(request=request, errors=request_client.errors, warnings=request_client.warnings,
                                 info=request_client.info, *args, **kwargs)

        # TODO: may need to handle here how to get data back from job, or may need that to be somewhere else
        # TODO: (we'll have the job_id as a cookie if a job started, so this should be doable)

        # Set cookies if a new session was acquired
        if request_client.is_new_session:
            http_response.set_cookie('maas_session_id', request_client.session_id)
            http_response.set_cookie('maas_session_secret', request_client.session_secret)
            http_response.set_cookie('maas_session_created', request_client.session_created)
        # Also set a cookie if a job was started and we have the id
        if request_client.job_id is not None:
            http_response.set_cookie('maas_job_id', request_client.job_id)
        return http_response