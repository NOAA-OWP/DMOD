import asyncio
from django.http import JsonResponse
from wsgiref.util import FileWrapper
from django.http.response import StreamingHttpResponse
from .AbstractDatasetView import AbstractDatasetView
from .DatasetFileWebsocketFilelike import DatasetFileWebsocketFilelike
import logging
logger = logging.getLogger("gui_log")


class DatasetApiView(AbstractDatasetView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_dataset_content_details(self, dataset_name: str):
        result = asyncio.get_event_loop().run_until_complete(self.dataset_client.get_dataset_content_details(name=dataset_name))
        logger.info(result)
        return JsonResponse({"contents": result}, status=200)

    def _delete_dataset(self, dataset_name: str) -> JsonResponse:
        result = asyncio.get_event_loop().run_until_complete(self.dataset_client.delete_dataset(name=dataset_name))
        return JsonResponse({"successful": result}, status=200)

    def _get_datasets_json(self) -> JsonResponse:
        serial_dataset_map = asyncio.get_event_loop().run_until_complete(self.get_datasets())
        return JsonResponse({"datasets": serial_dataset_map}, status=200)

    def _get_dataset_json(self, dataset_name: str) -> JsonResponse:
        serial_dataset = asyncio.get_event_loop().run_until_complete(self.get_dataset(dataset_name=dataset_name))
        return JsonResponse({"dataset": serial_dataset[dataset_name]}, status=200)

    def _get_download(self, request, *args, **kwargs):
        dataset_name = request.GET.get("dataset_name", None)
        item_name = request.GET.get("item_name", None)
        chunk_size = 8192

        custom_filelike = DatasetFileWebsocketFilelike(self.dataset_client, dataset_name, item_name)

        response = StreamingHttpResponse(
            FileWrapper(custom_filelike, chunk_size),
            content_type="application/octet-stream"
        )
        response['Content-Length'] = asyncio.get_event_loop().run_until_complete(self.dataset_client.get_item_size(dataset_name, item_name))
        response['Content-Disposition'] = "attachment; filename=%s" % item_name
        return response

    def get(self, request, *args, **kwargs):
        request_type = request.GET.get("request_type", None)
        if request_type == 'download_file':
            return self._get_download(request)
        elif request_type == 'datasets':
            return self._get_datasets_json()
        elif request_type == 'dataset':
            return self._get_dataset_json(dataset_name=request.GET.get("name", None))
        elif request_type == 'contents':
            return self._get_dataset_content_details(dataset_name=request.GET.get("name", None))
        if request_type == 'delete':
            return self._delete_dataset(dataset_name=request.GET.get("name", None))

        # TODO: finish
        return JsonResponse({}, status=400)
