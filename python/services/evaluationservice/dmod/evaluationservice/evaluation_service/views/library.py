"""
Provides views used to retrieve generated libraries
"""
import os

from django.http import HttpRequest
from django.http import JsonResponse
from django.http import HttpResponse
from django.http import HttpResponseBadRequest

from django.views.generic import View
from django.views.generic import TemplateView

from evaluation_service.consumers import get_clients
from evaluation_service.consumers import get_consumer_by_client_name
from evaluation_service.consumers import SUPPORTED_LANGUAGES


class GetLibraryOptions(View):
    @classmethod
    def route(cls) -> str:
        return "library/options/?$"

    def get(self, request: HttpRequest) -> JsonResponse:
        payload = {
            "clients": [
                {
                    "value": client_name,
                    "text": client_name.title()
                }
                for client_name in get_clients()
            ],
            "languages": [
                 {
                     "value": language,
                     "text": language.title()
                 }
                 for language in SUPPORTED_LANGUAGES.all()
            ]
        }

        return JsonResponse(data=payload)


class GetLibrary(View):
    @classmethod
    def route(cls) -> str:
        return "library/build/?$"

    def get(self, request: HttpRequest) -> HttpResponse:
        language = request.GET.get('language')
        client = request.GET.get("client")

        if not language and not client:
            return HttpResponseBadRequest("Neither a library language nor a client class were provided")
        elif not language:
            return HttpResponseBadRequest("A library language was not provided")
        elif not client:
            return HttpResponseBadRequest("A client class was not provided")
        elif not SUPPORTED_LANGUAGES.is_supported(language=language):
            return HttpResponseBadRequest(f"'{language}' is not a supported library language")

        consumer_class = get_consumer_by_client_name(client)

        if not consumer_class:
            return HttpResponseBadRequest(f"No library named '{client}' could be found")

        code = consumer_class.build_code(language=language)

        return HttpResponse(code)


class LibrarySelector(TemplateView):
    template_name = "evaluation_service/library_selector.html"

    def get_context_data(self, **kwargs):
        payload = {
            "options_url": "/" + os.path.join("evaluation_service", GetLibraryOptions.route()[:-2]),
            "get_url": "/" + os.path.join("evaluation_service", GetLibrary.route()[:-2])
        }

        return payload
