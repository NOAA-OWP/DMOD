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
    r'((?<!,)\s*\{\s*"type": "string",\s*"format": "binary"\s*},\s*|,\s*\{\s*"type": "string",\s*"format": "binary"\s*}\s*)'
)
"""
A regular expression that finds all type definitions that are strings formatted as bytes
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
        fields = "__all__"

    definition = forms.JSONField(
        widget=JSONArea(
            schema=get_editor_friendly_model_schema(specification.EvaluationSpecification)
        )
    )

class SpecificationTemplateForm(forms.ModelForm):
    """
    A specialized form for SpecificationTemplate that allows its JSON data to be manipulated within a JSONArea
    """
    class Meta:
        model = models.SpecificationTemplate
        fields = "__all__"

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