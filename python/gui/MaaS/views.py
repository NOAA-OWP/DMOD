import os
from django.conf import settings
from django.http import HttpResponse, Http404


def download_dataset(request, path):
    file_path = os.path.join(settings.DATA_DOWNLOADS_DIR, path)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/zip")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response
    raise Http404
