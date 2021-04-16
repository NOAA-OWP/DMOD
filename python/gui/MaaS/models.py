from django.db import models
import string

PARAMETER_TYPE_OPTIONS = [
    ("number", "Number"),
    ("text", "Text"),
    ("date", "Date"),
    ("datetime-local", "Date and Time"),
]


ACCEPTABLE_ID_CHARACERS = "_-" + string.ascii_letters + string.digits


# Create your models here.
class Formulation(models.Model):
    name = models.CharField(
        max_length=100,
        help_text="The name of the formulation"
    )

    description = models.TextField(
        help_text="What the formulation seeks to achieve"
    )

    def clean_name(self) -> str:
        """
        Returns the name of the formulation with non-alphanumeric characters stripped out

        :return: A version of the name that may be used as an id
        """
        return "".join([
            letter
            for letter in str(self.name).title()
            if letter in ACCEPTABLE_ID_CHARACERS
        ])

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return self.__str__()


class FormulationParameter(models.Model):
    formulation = models.ForeignKey(
        Formulation,
        on_delete=models.CASCADE
    )

    name = models.CharField(
        max_length=50,
        help_text="The name of the parameter for the formulation"
    )

    description = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="How this parameter affects the formulation"
    )

    value_type = models.CharField(
        max_length=50,
        choices=PARAMETER_TYPE_OPTIONS,
        help_text="The type of the "
    )

    group = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="A sub-group to which this parameter belongs"
    )

    is_list = models.BooleanField(
        default=False,
        help_text="Whether or not this variable should be a list"
    )

    minimum = models.FloatField(
        blank=True,
        null=True,
        help_text="The minimum possible numerical value for this parameter"
    )

    maximum = models.FloatField(
        blank=True,
        null=True,
        help_text="The maximum possible numerical value for this parameter"
    )

    default_value = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="An optional default value for the parameter"
    )

    def __str__(self):
        return "{}: {}".format(self.name, self.description)

    def __repr__(self):
        return self.__str__()
