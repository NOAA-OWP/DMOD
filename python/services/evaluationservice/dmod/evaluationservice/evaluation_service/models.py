import typing
import json

from django.contrib.auth.models import User
from django.db import models

import geopandas
from django.db.models import UniqueConstraint

from . import choices
from .wrapper import ModelWrapper

from dmod.evaluations.specification import get_specification_options

# Create your models here.

_BOX_TYPE = typing.Union[typing.Tuple[int, int, int, int], geopandas.GeoDataFrame, geopandas.GeoSeries]


class SpecificationTemplate(models.Model):
    class Meta:
        constraints = [
            UniqueConstraint(name="unique_template_idx", fields=["template_name", "template_specification_type"])
        ]

    template_name = models.CharField(verbose_name="name", max_length=100, help_text="The name of the template")
    template_specification_type = models.CharField(
        max_length=50,
        choices=get_specification_options(),
        help_text="The type of specification that this template pertains to"
    )
    template_configuration = models.CharField(
        max_length=30000,
        help_text="The configuration that should be applied to a given specification type"
    )
    template_description = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="A description of what the template does"
    )

    author = models.ForeignKey(to=User, on_delete=models.CASCADE, help_text="The user who created this template")

    @property
    def name(self) -> str:
        return self.template_name

    @property
    def specification_type(self) -> str:
        return self.template_specification_type

    def get_configuration(self, decoder_type: typing.Type[json.JSONDecoder] = None):
        return json.loads(self.template_configuration, cls=decoder_type)

    @property
    def description(self) -> typing.Optional[str]:
        return self.template_description

    def __str__(self):
        return f"[{self.specification_type}] {self.name}{':' + self.description if self.description else ''}"


class SpecificationTemplate(models.Model, TemplateDetails):
    class Meta:
        constraints = [
            UniqueConstraint(name="unique_template_idx", fields=["template_name", "template_specification_type"])
        ]
    template_name = models.CharField(verbose_name="name", max_length=100, help_text="The name of the template")
    template_specification_type = models.CharField(
        max_length=50,
        help_text="The type of specification that this template pertains to"
    )
    template_configuration = models.CharField(
        max_length=30000,
        help_text="The configuration that should be applied to a given specification type"
    )
    template_description = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="A description of what the template does"
    )

    author = models.ForeignKey(to=User, on_delete=models.CASCADE, help_text="The user who created this template")

    @property
    def name(self) -> str:
        return self.template_name

    @property
    def specification_type(self) -> str:
        return self.template_specification_type

    @property
    def configuration(self) -> dict:
        return json.loads(self.template_configuration)

    @property
    def description(self) -> typing.Optional[str]:
        return self.template_description


class EvaluationDefinition(models.Model):
    """
    Represents a definition for an evaluation that may be stored for reuse
    """
    class Meta:
        unique_together = ('name', 'author', 'description')

    name = models.CharField(max_length=255, help_text="The name of the evaluation")
    """(:class:`str`) The name of the evaluation"""

    author = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The name of the author of the evaluation"
    )
    """(:class:`str`) The name of the author of the evaluation"""

    description = models.TextField(
        blank=True,
        null=True,
        help_text="A helpful description of what the evaluation is intended to do"
    )
    """(:class:`str`) A helpful description of what the evaluation is intended to do"""

    definition = models.JSONField(
        help_text="The raw json that will be sent as the instructions to the evaluation service"
    )
    """(:class:`str`) The raw json that will be sent as the instructions to the evaluation service"""

    last_edited = models.DateTimeField(auto_now=True)
    """(:class:`datetime.datetime`) The last time this definition was edited"""

    def __str__(self):
        return f"{self.name} by {self.author}"

    def __repr__(self):
        return f"({self.author}) {self.name}: {self.description}"


class StoredDataset(models.Model):
    """
    Represents an accessible geometry dataset
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['dataset_type', 'name'],
                name="unique_stored_dataset"
            )
        ]

    name = models.CharField(max_length=255, help_text="An easy to reference name for the dataset")
    """(:class:`str`) The name of the dataset"""

    path = models.CharField(max_length=500, help_text="The path to the dataset")
    """(:class:`str`) The path to the dataset"""

    dataset_type = models.CharField(
        max_length=100,
        choices=choices.StoredDatasetType.field_choices(),
        help_text="The type of data the dataset provides"
    )
    """(:class:`str`) The type of data the dataset provides"""

    dataset_format = models.CharField(
        max_length=100,
        choices=choices.StoredDatasetFormat.field_choices(),
        help_text="The format of the dataset"
    )

    def read(self, bbox: _BOX_TYPE = None, engine: str = None) -> geopandas.GeoDataFrame:
        return geopandas.read_file(self.path, bbox=bbox, engine=engine)

    def __eq__(self, other) -> bool:
        return isinstance(other, StoredDataset) \
               and self.path == other.path \
               and self.name == other.name \
               and self.dataset_format == other.dataset_format \
               and self.dataset_type == other.dataset_type

    def __gt__(self, other) -> bool:
        return self.name > other.name

    def __lt__(self, other) -> bool:
        return self.name < other.name

    def __str__(self) -> str:
        return str(self.name)

    def __repr__(self) -> str:
        return f"{self.name} => {self.path}"


SpecificationTemplateCommunicator = ModelWrapper.for_model(SpecificationTemplate)
"""
A specialized handler for SpecificationTemplate database operations that should work the same in sync and async contexts
"""

EvaluationDefinitionCommunicator = ModelWrapper.for_model(EvaluationDefinition)
"""
A specialized handler for EvaluationDefinition database operations that should work the same in sync and async contexts
"""

StoredDatasetCommunicator = ModelWrapper.for_model(StoredDataset)
"""
A specialized handler for StoredDataset database operations that should work the same in sync and async contexts
"""