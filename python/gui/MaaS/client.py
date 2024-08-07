#!/usr/bin/env python

import traceback
import asyncio

from typing import Union

import logging

from pathlib import Path

from django.http import HttpRequest

from dmod.communication import ExternalRequest
from dmod.communication import ExternalRequestResponse
from dmod.communication import ExternalRequestClient

from . import utilities
from .processors.processor import BaseProcessor

logger = logging.getLogger("gui_log")


class JobRequestClient(ExternalRequestClient):
    """
    A client for websocket interaction with the MaaS request handler, specifically for performing a job request based on
    details provided in a particular HTTP POST request (i.e., with form info on the parameters of the job execution).
    """

    def __init__(
            self,
            endpoint_uri: str,
            processor: BaseProcessor,
            ssl_dir: Path = None
    ):
        if ssl_dir is None:
            ssl_dir = Path(__file__).resolve().parent.parent.parent.joinpath('ssl')
            ssl_dir = Path('/usr/maas_portal/ssl') #Fixme
        logger.debug("endpoint_uri: {}".format(endpoint_uri))
        super().__init__(endpoint_uri=endpoint_uri, ssl_directory=ssl_dir)
        self._processor = processor
        self._cookies = None

    def _acquire_session_info(self, use_current_values: bool = True, force_new: bool = False):
        """
        Attempt to set the session information properties needed to submit a maas job request.

        Attempt to set the session information properties needed to submit a maas job request represented by the
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
        logger.info("JobRequestClient._acquire_session_info:  getting session info")
        if not force_new and use_current_values and self._session_id and self._session_secret and self._session_created:
            logger.info('Using previously acquired session details (new session not forced)')
            return True
        elif not force_new and 'maas_session_secret' in self._cookies.keys():
            self._session_id = self._cookies['maas_session_id']
            self._session_secret = self._cookies['maas_session_secret']
            self._session_created = self._cookies['maas_session_created']
            logger.info("Session From PostFormJobRequestClient")
            return self._session_id and self._session_secret and self._session_created
        else:
            logger.info("Session from JobRequestClient: force_new={}".format(force_new))
            tmp = self._auth_client._acquire_session()
            logger.info("Session Info Return: {}".format(tmp))
            return tmp

    def _init_maas_job_request(self) -> ExternalRequest:
        """
        Set or reset the :attr:`form_proc` field and return its :attr:`RequestFormProcessor`.`maas_request` property.

        Returns
        -------
        The processed maas request from the newly initialized form processor in :attr:`form_proc`
        """
        pass

    # TODO: refactor to combine logic of this and MaasRequestClient from communication
    def make_maas_request(self, request: Union[HttpRequest, utilities.RequestWrapper], force_new_session: bool = False):
        logger.debug("client Making Job Request")
        self._cookies = request.COOKIES
        self._acquire_session_info(force_new=force_new_session)

        maas_job_request = self._processor.process_request(request)

        # Make sure to set if empty or reset if a new session was forced and just acquired
        if force_new_session or maas_job_request.session_secret is None:
            maas_job_request.session_secret = self._session_secret
        # If able to get session details, proceed with making a job request
        if self._session_secret is not None:
            print("******************* Request: " + maas_job_request.to_json())
            try:
                is_request_valid, request_validation_error = self._run_validation(message=maas_job_request)
                if is_request_valid:
                    try:
                        response_obj: ExternalRequestResponse = asyncio.get_event_loop().run_until_complete(
                            self.async_make_request(maas_job_request))
                        print('***************** Response: ' + str(response_obj))
                        # Try to get a new session if session is expired (and we hadn't already gotten a new session)
                        if self._request_failed_due_to_expired_session(response_obj) and not force_new_session:
                            return self.make_maas_request(request=request, force_new_session=True)
                        elif not self.validate_maas_request_response(response_obj):
                            raise RuntimeError('Invalid response received for requested job: ' + str(response_obj))
                        elif not response_obj.success:
                            template = 'Request failed (reason: {}): {}'
                            raise RuntimeError(template.format(response_obj.reason, response_obj.message))
                        else:
                            self.info.append(
                                "Scheduler started job, id {}".format(response_obj.data['job_id'])
                            )
                            return response_obj
                    except Exception as e:
                        # TODO: log error instead of print
                        msg = 'Encountered error submitting maas job request over session ' + str(self._session_id)
                        msg += " : \n" + str(type(e)) + ': ' + str(e)
                        print(msg)
                        traceback.print_exc()
                        self.errors.append(msg)
                else:
                    msg = 'Could not submit invalid maas job request over session ' + str(self._session_id)
                    msg += ' (' + str(request_validation_error) + ')'
                    print(msg)
                    self.errors.append(msg)
            except RuntimeError as e:
                print(str(e))
                self.errors.append(str(e))
        else:
            logger.info("client Unable to aquire session details")
            self.errors.append("Unable to acquire session details or authenticate new session for request")
        return None

    @property
    def errors(self):
        if self._errors is None:
            self._errors = [self._processor.errors] if self._processor is not None else []
        return self._errors

    @property
    def info(self):
        if self._info is None:
            self._info = [self._processor.info] if self._processor is not None else []
        return self._info

    @property
    def warnings(self):
        if self._warnings is None:
            self._warnings = [self._processor.warnings] if self._processor is not None else []
        return self._warnings
