"""
Definitions for forms that provide advanced handling for json data
"""
from __future__ import annotations

import typing
import json
import re

from pydantic import BaseModel

from django import forms

from widgets import JSONArea

from dmod.evaluations import specification
from dmod.evaluations.specification.base import get_subclasses

from evaluation_service import models

BINARY_TYPES = re.compile(
    r'((?<!,)\s*\{\s*"type": "string",\s*"format": "binary"\s*},\s*|'
    r',\s*\{\s*"type": "string",\s*"format": "binary"\s*}\s*)'
)
"""
A regular expression that finds all type definitions that are strings formatted as bytes

Catches on:

- `{"type": "string", "format": "binary"}, `
- `, {"type": "string", "format": "binary"}

Both cases must be handled for replacement/removal logic. A simple find and replace for
'{"type": "string", "format": "binary"}' could/would result in errant commas, causing the json to fail deserialization

The first will catch when it is at the beginning of a list. If it's at the beginning of the list, the following
comma and whitespace need to be removed to make the next object the first in the list.

The second will catch when it is not the first of the list. In this case, it will need to remove the previous comma
and any following whitespace. If there are further elements in the list, they will collapse and the comma that
would have proceeded this string definition will follow the previous element.

Examples:
    >>> at_beginning = '{"types": [{"type": "string", "format": "binary}, {"type": "number"}, {"type": "string"}]}'
    >>> not_at_beginning = '{"types": [{"type": "string"}, {"type": "string", "format": "binary}, {"type": "number"}]}'
    >>> BINARY_TYPES.sub("", at_beginning)
    '{"types": [{"type": "number"}, {"type": "string"}]}'
    >>> BINARY_TYPES.sub("", not_at_beginning)
    '{"types": [{"type": "string"}, {"type": "number"}]}'
"""


def get_editor_friendly_model_schema(model: typing.Type[BaseModel]) -> typing.Optional[dict]:
    """
    Get the schema for a model and scrub any editor unfriendly type from it

    An example of an editor unfriendly type is a string in a binary format

    Args:
        model: The model whose schema to retrieve

    Returns:
        A schema for the model if it is available
    """
    if hasattr(model, "schema_json"):
        json_data = model.schema_json()

        json_data = BINARY_TYPES.sub("", json_data)

        return json.loads(json_data)
    return None


def get_specification_schema_map() -> typing.Dict[str, typing.Any]:
    """
    Generate a dictionary mapping specification types to their schemas

    Return:
        A dictionary mapping the value of a specification type that will be on the template type selector to schema data that is compatible with the client side editor
    """
    return {
        specification_type.get_specification_type(): get_editor_friendly_model_schema(specification_type)
        for specification_type in get_subclasses(specification.TemplatedSpecification)
    }


class EvaluationDefinitionForm(forms.ModelForm):
    """
    A specialized form for EvaluationDefinition that allows its JSON data to be manipulated within a JSONArea
    """
    class Meta:
        model = models.EvaluationDefinition
        fields = [
            field.name
            for field in models.EvaluationDefinition._meta.get_fields()
            if field.name.lower() not in ("owner", "author")
        ]

    definition = forms.JSONField(
        widget=JSONArea(
            schema=get_editor_friendly_model_schema(specification.EvaluationSpecification)
        )
    )


class SpecificationTemplateForm(forms.ModelForm):
    """
    A specialized form for SpecificationTemplate that allows its JSON data to be manipulated within a JSONArea
    """
    #class Meta:
    #    model = models.SpecificationTemplate
    #    fields = [
    #        field.name
    #        for field in models.SpecificationTemplate._meta.get_fields()
    #        if field.name.lower() not in ("owner", "author")
    #    ]

    class Media:
        # Include a script to add functionality that will update the json area's
        # schema when the template type is changed
        js = [
            "evaluation_service/js/template_specification.js"
        ]

    template_configuration = forms.JSONField(
        widget=JSONArea(
            extra_data={
                "schemas": get_specification_schema_map()
            }
        )
    )