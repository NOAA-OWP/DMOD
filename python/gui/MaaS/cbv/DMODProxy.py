"""
Defines a view that may be used to configure a MaaS request
"""

import os
from abc import ABC, abstractmethod
from django.http import HttpRequest, HttpResponse
from django.views.generic.base import View
from django.shortcuts import render

import logging
logger = logging.getLogger("gui_log")

from dmod.communication import (Distribution, get_available_models, get_available_outputs, get_request, get_parameters,
                                NWMRequestJsonValidator, NWMRequest, ExternalRequest, ExternalRequestClient,
                                ExternalRequestResponse, Scalar, MessageEventType)
from pathlib import Path
from typing import List, Optional, Tuple, Type


class RequestFormProcessor(ABC):

    def __init__(self, post_request: HttpRequest, maas_secret):
        """The HttpRequest received, used to submit the form for the job to request from the MaaS."""
        self.post_request = post_request
        self._errors = None
        self.warnings = list()
        self.info = list()
        self.maas_secret = maas_secret

        self._parameter_keys = None

        self._maas_request = None
        self._is_valid = None
        self._validation_error = None
        self._parameters = None

    @abstractmethod
    def _init_parameters(self):
        """
        Initialize the :attr:`_parameters` mapping object from the parameters of this instance's :attr:`request`, which
        also results in the :attr:`_errors` list being initialized.
        """
        pass

    @property
    def errors(self) -> list:
        if self._errors is None:
            self._init_parameters()
        return self._errors

    @property
    def is_valid(self) -> bool:
        """
        Return whether the MaaS request represented by :attr:post_request is valid, lazily perform validation if it
        has not already been done.

        In this implementation, the only supported type of :class:`MaasRequest` is the :class:`NWMRequest` type.  Before
        using a validator, this method will confirm the type, and return False if it is something different.

        Returns
        -------
        bool
            whether the MaaS job request represented by :attr:post_request is valid
        """
        if self._is_valid is None:
            if not isinstance(self.maas_request, NWMRequest):
                self._is_valid = False
                self._validation_error = TypeError('Unsupport MaaS message type created by ' + str(self.__class__))
            else:
                self._is_valid, self._validation_error = NWMRequestJsonValidator().validate(self.maas_request.to_dict())
        return self._is_valid

    @property
    @abstractmethod
    def maas_request(self) -> ExternalRequest:
        """
        Get the :obj:ExternalRequest instance (which could be a subclass of this type) represented by :attr:post_request,
        lazily instantiating the former if necessary.

        Returns
        -------
        :obj:ExternalRequest
            the :obj:ExternalRequest instance represented by :attr:post_request
        """
        pass

    @property
    def parameter_keys(self) -> List[str]:
        return self._parameter_keys

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


class ModelExecRequestFormProcessor(RequestFormProcessor):
    """
    Class that receives an HTTP POST request of the form submission for a desired job, and converts this to a
    MaasRequest to be submitted.
    """
    def __init__(self, post_request: HttpRequest, maas_secret):
        """The HttpRequest received, used to submit the form for the job to request from the MaaS."""
        super(ModelExecRequestFormProcessor, self).__init__(post_request, maas_secret)
        self.model = post_request.POST['model']
        # TODO: fix this later to be required
        self.config_data_id = post_request.POST['config_data_id'] if 'config_data_id' in post_request.POST else '1'

        # This will give us the parameters that were configured for the model we want to use
        # If we configured that we want to tweak 'example_parameter' for the model named 'YetAnother',
        # then change our minds and decide to tweak 'land_cover' for the 'NWM' model, this will filter
        # out the configuration from 'YetAnother'
        self._parameter_keys = [
            parameter
            for parameter in post_request.POST
            if post_request.POST[parameter] == 'on' and parameter.startswith(self.model)
        ]

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
                distribution = Distribution(
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
                scalar = Scalar(int(scalar_value))
                self._parameters[parameter.replace(self.model + "_", "")] = scalar

    @property
    def maas_request(self) -> ExternalRequest:
        """
        Get the :obj:ExternalRequest instance (which could be a subclass of this type) represented by :attr:post_request,
        lazily instantiating the former if necessary.

        Returns
        -------
        :obj:ExternalRequest
            the :obj:ExternalRequest instance represented by :attr:post_request
        """
        if self._maas_request is None:
            if len(self.errors) == 0:
                self._maas_request = get_request(self.model, self.config_data_id, self.maas_secret)
        return self._maas_request


class PostFormRequestClient(ExternalRequestClient):
    """
    A client for websocket interaction with the MaaS request handler as initiated by a POST form HTTP request.
    """

    @classmethod
    def _bootstrap_ssl_dir(cls, ssl_dir: Optional[Path] = None):
        if ssl_dir is None:
            ssl_dir = Path(__file__).resolve().parent.parent.parent.joinpath('ssl')
            ssl_dir = Path('/usr/maas_portal/ssl') #Fixme
        return ssl_dir

    def __init__(self, endpoint_uri: str, http_request: HttpRequest, ssl_dir: Optional[Path] = None):
        super().__init__(endpoint_uri=endpoint_uri, ssl_directory=self._bootstrap_ssl_dir(ssl_dir))
        logger.debug("endpoing_uri: {}".format(endpoint_uri))
        self.http_request = http_request
        self.form_proc = None

    def _acquire_session_info(self, use_current_values: bool = True, force_new: bool = False):
        """
        Attempt to set the session information properties needed to submit a MaaS request.

        Attempt to set the session information properties needed to submit a MaaS request represented by the
        HttpRequest in :attr:http_request, either from the cookies of the HttpRequest or by authenticating and obtaining
        a new session from the request handler.

        Parameters
        ----------
        use_current_values
            Whether to use currently held attribute values for session details, if already not None (disregarded if
            ``force_new`` is ``True``).
        force_new
            Whether to force acquiring a new session, regardless of data available is available on an existing session.

        Returns
        -------
        bool
            whether session details were acquired and set successfully
        """
        logger.info("{}._acquire_session_info:  getting session info".format(self.__class__.__name__))
        if not force_new and use_current_values and self._session_id and self._session_secret and self._session_created:
            logger.info('Using previously acquired session details (new session not forced)')
            return True
        elif not force_new and 'maas_session_secret' in self.http_request.COOKIES.keys():
            self._session_id = self.http_request.COOKIES['maas_session_id']
            self._session_secret = self.http_request.COOKIES['maas_session_secret']
            self._session_created = self.http_request.COOKIES['maas_session_created']
            logger.info("Session From {}".format(self.__class__.__name__))
            return self._session_id and self._session_secret and self._session_created
        else:
            logger.info("Session from {}: force_new={}".format(self.__class__.__name__, force_new))
            tmp = self._auth_client._acquire_session()
            logger.info("Session Info Return: {}".format(tmp))
            return tmp

    def _init_maas_job_request(self):
        pass

    def generate_request(self, form_proc_class: Type[RequestFormProcessor]) -> ExternalRequest:
        self.form_proc = form_proc_class(post_request=self.http_request, maas_secret=self._auth_client._session_secret)
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

    @property
    def warnings(self):
        if self._warnings is None:
            self._warnings = [self.form_proc.warnings] if self.form_proc is not None else []
        return self._warnings


class DMODMixin:
    """
        A mixin to proxy DMOD requests to the aysnc endpoint
    """

    @property
    def maas_endpoint_uri(self):
        if not hasattr(self, '_maas_endpoint_uri') or self._maas_endpoint_uri is None:
            self._maas_endpoint_uri = 'wss://' + os.environ.get('MAAS_ENDPOINT_HOST') + ':'
            self._maas_endpoint_uri += os.environ.get('MAAS_ENDPOINT_PORT')
        return self._maas_endpoint_uri

    def forward_request(self, request: HttpRequest, event_type: MessageEventType) -> Tuple[
        PostFormRequestClient, dict, Optional[ExternalRequestResponse]]:
        """
        Reformat and forward the MaaS request.

        Parameters
        ----------
        request : HttpRequest
            The encapsulated MaaS request.

        event_type : MessageEventType
            The type of request event.

        Returns
        -------
        Tuple[PostFormRequestClient, dict, Optional[ExternalRequestResponse]]
            PostFormRequestClient configured from posted form in request, the session data as a dictionary, and the
            response the client received for the request, if any.
        """
        client = PostFormRequestClient(endpoint_uri=self.maas_endpoint_uri, http_request=request)
        if event_type == MessageEventType.MODEL_EXEC_REQUEST:
            form_processor_type = ModelExecRequestFormProcessor
        else:
            raise RuntimeError("{} got unsupported event type: {}".format(self.__class__.__name__, str(event_type)))

        maas_request = client.generate_request(form_processor_type)
        logger.info("{}.forward_request: making {}".format(self.__class__.__name__, maas_request.__class__.__name__))
        response = client.make_maas_request(maas_request=maas_request, force_new_session=False)

        session_data = { }
        # Set data if a new session was acquired
        if client.is_new_session:
            session_data['maas_session_id'] = client.session_id
            session_data['maas_session_secret'] = client.session_secret
            session_data['maas_session_created'] = client.session_created

        #  TODO: make sure this logic get to the respective appropriate user View types
        #         # if event_type == MessageEventType.MODEL_EXEC_REQUEST:
        #         #     # Set data if a job was started and we have the id (rely on client to manage multiple job ids)
        #         #     # TODO might be worth using DJango session to save this to (can serialize a json list of ids?)
        #         #     # Might also be worth saving to a "user" database table with "active jobs"?
        #         #     if response is not None and 'job_id' in response.data:
        #         #         session_data['new_job_id'] = response.data['job_id']
        #         # elif event_type == MessageEventType.PARTITION_REQUEST:
        #         #     session_data['partitioner_response'] = response

        return client, session_data, response
