"""
Defines a view that may be used to configure a MaaS request
"""
import asyncio
import os
from django.http import HttpRequest, HttpResponse
from django.views.generic.base import View
from django.shortcuts import render

import dmod.communication as communication
from dmod.client.request_clients import DatasetExternalClient
from dmod.core.meta_data import DataCategory, DataFormat

import logging
logger = logging.getLogger("gui_log")

from pathlib import Path

from .DMODProxy import DMODMixin, GUI_STATIC_SSL_DIR
from .utils import extract_log_data
from typing import Dict


class DatasetManagementView(View, DMODMixin):

    """
    A view used to configure a dataset management request or requests for transmitting dataset data.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dataset_client = None

    def _process_event_type(self, http_request: HttpRequest) -> communication.MessageEventType:
        """
        Determine and return whether this request is for a ``DATASET_MANAGEMENT`` or ``DATA_TRANSMISSION`` event.

        Parameters
        ----------
        http_request : HttpRequest
            The raw HTTP request in question.

        Returns
        -------
        communication.MessageEventType
            Either ``communication.MessageEventType.DATASET_MANAGEMENT`` or
            ``communication.MessageEventType.DATA_TRANSMISSION``.
        """
        # TODO:
        raise NotImplementedError("{}._process_event_type not implemented".format(self.__class__.__name__))

    @property
    def dataset_client(self) -> DatasetExternalClient:
        if self._dataset_client is None:
            self._dataset_client = DatasetExternalClient(endpoint_uri=self.maas_endpoint_uri,
                                                         ssl_directory=GUI_STATIC_SSL_DIR)
        return self._dataset_client

    async def _get_datasets(self) -> Dict[str, dict]:
        serial_datasets = await self.dataset_client.get_serialized_datasets()
        return serial_datasets

    def get(self, http_request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The handler for 'get' requests.

        This will render the 'maas/dataset_management.html' template after retrieving necessary information to initially
        populate the forms it displays.

        Parameters
        ----------
        http_request : HttpRequest
            The request asking to render this page.
        args
        kwargs

        Returns
        -------
        A rendered page.
        """
        errors, warnings, info = extract_log_data(kwargs)

        # Gather map of serialized datasets, keyed by dataset name
        serial_dataset_map = asyncio.get_event_loop().run_until_complete(self._get_datasets())

        dataset_categories = [c.name.title() for c in DataCategory]
        dataset_formats = [f.name for f in DataFormat]

        payload = {
            'datasets': serial_dataset_map,
            'dataset_categories': dataset_categories,
            'dataset_formats': dataset_formats,
            'errors': errors,
            'info': info,
            'warnings': warnings
        }

        # TODO: create this file
        return render(http_request, 'maas/dataset_management.html', payload)

    def post(self, http_request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The handler for 'post' requests.

        This will attempt to submit the request and rerender the page like a 'get' request.

        Parameters
        ----------
        http_request : HttpRequest
            The request asking to render this page.
        args
        kwargs

        Returns
        -------
        A rendered page.
        """
        # TODO: implement this to figure out whether DATASET_MANAGEMENT or DATA_TRANSMISSION
        event_type = self._process_event_type(http_request)
        client, session_data, dmod_response = self.forward_request(http_request, event_type)

        # TODO: this probably isn't exactly correct, so review once closer to completion
        if dmod_response is not None and 'dataset_id' in dmod_response.data:
            session_data['new_dataset_id'] = dmod_response.data['dataset_id']

        http_response = self.get(http_request=http_request, errors=client.errors, warnings=client.warnings,
                                 info=client.info, *args, **kwargs)

        for k, v in session_data.items():
            http_response.set_cookie(k, v)

        return http_response
