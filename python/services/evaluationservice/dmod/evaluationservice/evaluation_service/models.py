from django.db import models

# Create your models here.


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

