"""
Defines a view that may be used to configure a MaaS request
"""
import asyncio
import os.path

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile, TemporaryUploadedFile
from django.conf import settings
from datetime import datetime

import dmod.communication as communication
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, Serializable

import logging
logger = logging.getLogger("gui_log")

from .utils import extract_log_data
from .AbstractDatasetView import AbstractDatasetView
from .DatasetManagementForms import DatasetForm, DatasetFormatForm
from typing import List

DT_FORMAT = settings.DATE_TIME_FORMAT


class DatasetManagementView(AbstractDatasetView):

    """
    A view used to configure a dataset management request or requests for transmitting dataset data.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    def _create_dataset(self, name: str, category: str, data_format: str, *args, **kwargs) -> bool:
        d_format = DataFormat.get_for_name(data_format)
        if format is None:
            return False
        else:
            try:
                domain = DataDomain.factory_init_from_restriction_collections(d_format, **kwargs)
            except Exception as e:
                msg = 'Failed to create dataset {}: {} creating domain ({})'.format(name, e.__class__.__name__, str(e))
                logger.error(msg)
                raise RuntimeError(msg)
        return asyncio.get_event_loop().run_until_complete(
            self.dataset_client.create_dataset(name=name, category=DataCategory.get_for_name(category), domain=domain))

    def _upload_files_to_dataset(self, dataset_name: str, files: List[UploadedFile]) -> bool:
        # TODO: (later) consider modifying files to account for DMOD-specific characteristics (e.g., file paths for
        #  inside worker containers)
        minio_client = self.factory_minio_client()
        result = True
        for f in files:
            if isinstance(f, TemporaryUploadedFile):
                length = os.path.getsize(f.file.name)
            else:
                length = f.file.getbuffer().nbytes
            result_obj = minio_client.put_object(bucket_name=dataset_name, object_name=f.name, data=f.file,
                                                 length=length)
            # TODO: (later) try to do something based on result_obj.last_modified
            result = result and result_obj.bucket_name == dataset_name and result_obj.object_name == f.name
        return result

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
        serial_dataset_map = asyncio.get_event_loop().run_until_complete(self.get_datasets())
        serial_dataset_list = [serial_dataset_map[d] for d in serial_dataset_map]

        dataset_categories = [c.name.title() for c in DataCategory]
        dataset_formats = [f.name for f in DataFormat]

        form = DatasetForm()

        payload = {
            'form': form,
            'dynamic_forms': [f.value() for f in DatasetFormatForm],
            'datasets': serial_dataset_list,
            'dataset_categories': dataset_categories,
            'dataset_formats': dataset_formats,
            'errors': errors,
            'info': info,
            'warnings': warnings
        }

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
        # Should get a list of file-type objects, with a ``name`` property and a ``file`` BytesIO property
        files = http_request.FILES.getlist('files')

        csrf_token_key = 'csrfmiddlewaretoken'

        # name (dataset name), category, data_format, and any other applicable dynamic form items
        # e.g., catchment_id, hydrofabric_id, data_id, etc.
        dataset_details = dict([(k, v) for k, v in http_request.POST.items() if k != csrf_token_key])
        dataset_name = dataset_details['name']

        # TODO: consider reading files to validate/replace domain details from form

        # If present, parse catchment ids string to list of individual ids
        if 'catchment_id' in dataset_details:
            dataset_details['catchment_id'] = [s.strip() for s in dataset_details.pop('catchment_id').split(',')]

        # Fix keys for start and end times
        if 'start_time' in dataset_details and 'end_time' in dataset_details:
            start = datetime.strptime(dataset_details.pop('start_time'), settings.DATE_TIME_FORMAT)
            end = datetime.strptime(dataset_details.pop('end_time'), settings.DATE_TIME_FORMAT)
            dataset_details['time'] = {'start': start.strftime(Serializable.get_datetime_str_format()),
                                       'end': end.strftime(Serializable.get_datetime_str_format())}
        elif 'start_time' in dataset_details or 'end_time' in dataset_details:
            # TODO: figure out best way to handle this; for now ...
            raise RuntimeError('Cannot create a dataset of this format unless both a start and end time are given')

        was_created = self._create_dataset(**dataset_details)

        if not was_created:
            err_msg = 'Could not created dataset {}'.format(dataset_name)
            logger.error(err_msg)
            http_response = self.get(http_request=http_request, errors=[err_msg], *args, **kwargs)
        elif files is None or len(files) == 0:
            info_msg = 'Created empty dataset {}'.format(dataset_name)
            logger.info(info_msg)
            http_response = self.get(http_request=http_request, info_msg=[info_msg], *args, **kwargs)
        # With this condition test (if we get here), put files in dataset
        elif not self._upload_files_to_dataset(dataset_name=dataset_name, files=files):
            err_msg = 'Could not upload requested files to dataset {}'.format(dataset_name)
            logger.error(err_msg)
            http_response = self.get(http_request=http_request, errors=[err_msg], *args, **kwargs)
        else:
            info_msg = 'Created dataset {} with {} files uploaded'.format(dataset_name, len(files))
            logger.info(info_msg)
            http_response = self.get(http_request=http_request, info_msg=[info_msg], *args, **kwargs)

        #for k, v in session_data.items():
        #    http_response.set_cookie(k, v)

        return http_response
