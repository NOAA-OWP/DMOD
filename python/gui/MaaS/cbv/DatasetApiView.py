import asyncio
from django.http import JsonResponse
from .AbstractDatasetView import AbstractDatasetView
import logging
logger = logging.getLogger("gui_log")


class DatasetApiView(AbstractDatasetView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_datasets_json(self) -> JsonResponse:
        serial_dataset_map = asyncio.get_event_loop().run_until_complete(self.get_datasets())
        return JsonResponse({"datasets": serial_dataset_map}, status=200)

    def _get_dataset_json(self, dataset_name: str) -> JsonResponse:
        serial_dataset = asyncio.get_event_loop().run_until_complete(self.get_dataset(dataset_name=dataset_name))
        return JsonResponse({"dataset": serial_dataset[dataset_name]}, status=200)

    def get(self, request, *args, **kwargs):
        request_type = request.GET.get("request_type", None)
        if request_type == 'datasets':
            return self._get_datasets_json()
        elif request_type == 'dataset':
            return self._get_dataset_json(dataset_name=request.GET.get("name", None))

        # TODO: finish
        return JsonResponse({}, status=400)
