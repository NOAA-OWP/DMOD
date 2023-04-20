"""
Defines basic views used to expedite UI element development by providing direct access 
to developmental and example templates and functionality

An example would be accessing a template that just shows how to instantiate a table and 
provide the functionality in such a way that further development may be done client side 
in an isolated fashion
"""
import typing
import os
import abc

from django.conf import settings

from django.http import HttpRequest
from django.http import HttpResponse

from django.views.generic import View
from django.views.generic import TemplateView

from django.shortcuts import render


class ClientPrototype(TemplateView):
    """
    Base class for a view used to test client side prototypes
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template_name = kwargs.get("template_name", self.get_prototype_template())

    @classmethod
    def get_prototype_template(cls) -> str:
        """
        Get the template for this particular test
        """
        raise NotImplementedError(
            "Class specific templates should be declared within a subclass, not the base prototype"
        )


class RuntimePrototype(View):
    """
    Defines a prototype whose template is passed in through the query rather than through a class based variable
    """
    def get(self, request: HttpRequest, path: str) -> HttpResponse:
        if not path.endswith(".html"):
            path += ".html"

        context = {key: value for key, value in request.GET.items()}
        context['modules'] = {"tables": "common/js/tables.js"}

        return render(request=request, template_name=path, context=context)
