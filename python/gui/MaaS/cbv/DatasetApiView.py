import asyncio
import zipfile

from django.http import JsonResponse
from wsgiref.util import FileWrapper
from django.http.response import StreamingHttpResponse
from .AbstractDatasetView import AbstractDatasetView
from pathlib import Path
from .DatasetFileWebsocketFilelike import DatasetFileWebsocketFilelike
from django.conf import settings
from typing import Optional, Set
import logging
import minio

MINIO_HOST_STRING = settings.MINIO_HOST_STRING
MINIO_ACCESS = Path(settings.MINIO_ACCESS_FILE).read_text().strip()
MINIO_SECRET = Path(settings.MINIO_SECRET_FILE).read_text().strip()
MINIO_SECURE_CONNECT = settings.MINIO_SECURE_CONNECT

logger = logging.getLogger("gui_log")

CACHE_DIR: Path = Path(settings.DATA_CACHE_DIR)
DOWNLOADS_DIR: Path = Path(settings.DATA_DOWNLOADS_DIR)
UPLOADS_DIR: Path = Path(settings.DATA_UPLOADS_DIR)


class DatasetApiView(AbstractDatasetView):

    @classmethod
    def factory_minio_client(cls, endpoint: Optional[str] = None, access: Optional[str] = None,
                             secret: Optional[str] = None, is_secure: Optional[bool] = False) -> minio.Minio:
        client = minio.Minio(endpoint=MINIO_HOST_STRING if endpoint is None else endpoint,
                             access_key=MINIO_ACCESS if access is None else access,
                             secret_key=MINIO_SECRET if secret is None else secret,
                             secure=MINIO_SECURE_CONNECT if is_secure is None else is_secure)

        return client

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def _cleanup_dir(cls, dir_path: Path) -> bool:
        """
        Cleanup contents and remove a given directory, returning whether this was done or nothing exists at the path.

        Parameters
        ----------
        dir_path : Path
            Path to an expected directory.

        Returns
        -------
        bool
            ``True`` if nothing exists at this path, either because a directory was deleted or because nothing was
            there; or ``False`` if there is an existing non-directory file at this path.
        """
        # TODO: implement and then use in caching method and after zip file is created
        if not dir_path.exists():
            return True
        elif not dir_path.is_dir():
            return False
        else:
            results = True
            for p in dir_path.glob('*'):
                if p.is_dir():
                    results = results and cls._cleanup_dir(p)
                else:
                    p.unlink()
            dir_path.rmdir()
            return results

    def _cache_dataset_downloads(self, dataset_name: str, files: Optional[Set[str]] = None) -> Path:
        """
        Cache contents (files) of the dataset to files in the local downloads cache.

        Parameters
        ----------
        dataset_name : str
            The name of the dataset of interest.
        files : Optional[Set[str]]
            An optional subset of the files in the dataset to be cached locally, with the default of ``None`` implying
            all files within the dataset.

        Returns
        ----------
        Path
            The cache directory path containing the downloaded dataset data.
        """
        #returned_json = asyncio.get_event_loop().run_until_complete(self.get_dataset(dataset_name=dataset_name))
        #dataset_json = returned_json[dataset_name]
        # TODO: maybe check to make sure dataset exists?
        local_copy_dir = CACHE_DIR.joinpath(dataset_name)
        if files is None and local_copy_dir.is_dir():
            self._cleanup_dir(local_copy_dir)
        elif local_copy_dir.is_dir():
            for p in [local_copy_dir.joinpath(f) for f in files]:
                if p.is_dir():
                    self._cleanup_dir(p)
                else:
                    p.unlink(missing_ok=True)
        elif local_copy_dir.exists():
            local_copy_dir.unlink()
        local_copy_dir.mkdir(parents=True)
        # TODO: later devise something better for dealing with prefixes for emulated directory structure
        #for minio_object in self.minio_client.list_objects(dataset_name):
        logger.info("Retrieving a list of dataset files for {}".format(dataset_name))
        minio_client = self.factory_minio_client()
        file_list = [obj.object_name for obj in minio_client.list_objects(dataset_name)]
        logger.info("Downloading {} dataset files to GUI app server".format(len(file_list)))
        for filename in file_list:
            minio_client.fget_object(bucket_name=dataset_name, object_name=filename,
                                     file_path=str(local_copy_dir.joinpath(filename)))
        logger.info("Dataset {} locally cached".format(dataset_name))
        return local_copy_dir

    def _get_dataset_content_details(self, dataset_name: str):
        result = asyncio.get_event_loop().run_until_complete(self.dataset_client.get_dataset_content_details(name=dataset_name))
        logger.info(result)
        return JsonResponse({"contents": result}, status=200)

    def _delete_dataset(self, dataset_name: str) -> JsonResponse:
        result = asyncio.get_event_loop().run_until_complete(self.dataset_client.delete_dataset(name=dataset_name))
        return JsonResponse({"successful": result}, status=200)

    def _get_dataset_download(self, request, *args, **kwargs):
        dataset_name = request.GET.get("dataset_name", None)
        local_dir = self._cache_dataset_downloads(dataset_name).resolve(strict=True)
        logger.info("Caching data to {}".format(local_dir))
        zip_path = DOWNLOADS_DIR.joinpath('{}.zip'.format(dataset_name))
        if not DOWNLOADS_DIR.is_dir():
            DOWNLOADS_DIR.mkdir(parents=True)
        logger.info("Creating zip file for dataset contents at {}".format(zip_path))
        with zipfile.ZipFile(zip_path, mode='w', compression=zipfile.ZIP_STORED) as zip_file:
            for file in local_dir.glob('*'):
                logger.info("Writing {} to zip file {}".format(file, zip_path))
                zip_file.write(file, file.relative_to(local_dir.parent))

        logger.info("Dataset zip file {} fully created".format(zip_path))
        self._cleanup_dir(local_dir)

        # TODO: make sure downloading actually works

        #response = HttpResponse(zip_path.open(), mimetype='application/zip')
        #return response
        # TODO: later, figure out something to clean up these zip files
        return JsonResponse({"zip_file": str(zip_path.relative_to(DOWNLOADS_DIR))}, status=200)

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
        if request_type == 'download_dataset':
            return self._get_dataset_download(request)
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
