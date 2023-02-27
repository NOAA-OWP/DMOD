import typing

from django.db import models

import geopandas

from . import choices

# Create your models here.

_BOX_TYPE = typing.Union[typing.Tuple[int, int, int, int], geopandas.GeoDataFrame, geopandas.GeoSeries]


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

