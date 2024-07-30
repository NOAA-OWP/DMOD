"""
Provides a naive class for formatting a Django object (such as a Model or something like an AnonymousUser) as either
a string or dict for a larger serialization scheme
"""

import typing
import inspect

from datetime import datetime

from django.db.models import Model as DjangoModel
from django.db.models.query_utils import DeferredAttribute as ModelField

from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BasicAuthentication
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from rest_framework.views import APIView

from .message import __MessageSerializer
from .message import SERIALIZABLE_TYPE

DJANGO_OBJECT = typing.Union[DjangoModel, object]
CONVERSION_FUNCTION = typing.Callable[[DJANGO_OBJECT], typing.Union[str, dict]]


_MODULES_TO_IGNORE = [
    'django.contrib.auth'
]


_FIELDNAMES_TO_IGNORE = [
    "password"
]

TYPE_TO_SERIALIZE = typing.Union[DjangoModel, dict, str, bytes, datetime, typing.Iterable]


def conversion_function(*model_types: typing.Type[DJANGO_OBJECT]):
    """
    Indicates that a function is meant to be used for conversions and attaches the class types of all
    pertinent object types to it
    """
    def annotated_conversion_function(function: CONVERSION_FUNCTION) -> CONVERSION_FUNCTION:
        setattr(function, "models", model_types)
        setattr(function, "conversion_function", True)
        return function

    return annotated_conversion_function


def member_is_field(member: object) -> bool:
    """
    Whether the given member represents data stored in the database for an object
    """
    return isinstance(member, ModelField)


class __DjangoMessageSerializer(__MessageSerializer):
    """
    Object that naively converts (preferably) Django models into a format safe to transmit over the wire.

    Non-Django models are supported, though to a much limited extent. Non-Django Model objects that are needed to
    be converted are simply converted to strings. This will cover cases where Django subs in default objects
    (such as AnonymousUser, which isn't a model, for User, which IS a model)
    """
    def __init__(self):
        self.__conversions: typing.Dict[typing.Type[DJANGO_OBJECT], CONVERSION_FUNCTION] = dict()
        """A mapping between all supported object types and their conversion functions"""

        # Scour the members of the serializer for conversion functions
        conversion_functions: typing.List[typing.Tuple[str, typing.Any]] = inspect.getmembers(
            self,
            predicate=lambda member: getattr(member, "conversion_function", False)
        )

        # Assign all found functions to the map. Different models might have the same function, so those conversions
        # will be added to the additional model types specified within the 'models' field that was added to the
        # conversion function
        for conversion_name, conversion in conversion_functions:
            if isinstance(conversion.models, typing.Iterable):
                for model in conversion.models:
                    self.__conversions[model] = conversion

    @conversion_function(DjangoModel)
    def default_conversion(self, instance: DjangoModel) -> typing.Union[str, dict]:
        """
        The default conversion function for all Django models

        Simply takes the values of all fields on the model instance and sticks them into a dictionary, recursively
        (to make sure that nested or related fields are correctly included as well)

        If the class lies within a module we need to ignore (such as 'django.contrib.auth'), only the string is
        returned. This prevents the process from doing things like sending passwords across the wire.

        Args:
            instance: The model instance to convert to a serializer friendly object

        Returns:
            A dictionary if it is safe to convert the object, the string otherwise
        """
        # Check to make sure that the class for the instance isn't in a module marked as dangerous
        requires_more_specific_conversion = len([
            module_name
            for module_name in _MODULES_TO_IGNORE
            if instance.__class__.__module__.startswith(module_name)
        ]) == 0

        # If it's marked as dangerous, return its string representation
        if requires_more_specific_conversion:
            return str(instance)

        # Return a dictionary of each field name mapped to its value
        return {
            field_name: self.convert(getattr(instance, field_name))
            for field_name, field in inspect.getmembers(instance.__class__, predicate=member_is_field)
            if field_name.lower() not in _FIELDNAMES_TO_IGNORE
        }

    @conversion_function(User, AnonymousUser)
    def _user_to_dict(self, user: typing.Union[User, AnonymousUser]) -> dict:
        """
        Converts a user-like object into a representation that is safe to send over the wire
        """
        conversion = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "is_anonymous": user.is_anonymous,
            "name": str(user)
        }

        if isinstance(user, User) and user.get_full_name().strip():
            conversion['name'] = user.get_full_name().strip()

        return conversion

    def convert(self, entity: DJANGO_OBJECT) -> typing.Union[str, dict]:
        """
        Convert the passed in object in a Django application acceptable way
        """
        # first find any existing conversions that match
        matching_conversions = [
            (model_type, conversion)
            for model_type, conversion in self.__conversions.items()
            if isinstance(entity, model_type)
        ]

        # If there aren't any conversions and this isn't a django model, go ahead and return the string
        if len(matching_conversions) == 0 and not isinstance(entity, DjangoModel):
            return str(entity)

        # Sort the conversions based on the length of the MRO. A longer MRO marks a more specific conversion.
        # If an entry is added for AbstractUser and Model, User will match both.
        # AbstractUser inherits from several other things INCLUDING Model, so that is the conversion we seek to use
        matching_conversions = sorted(
            matching_conversions,
            key=lambda model_type_and_conversion: len(inspect.getmro(model_type_and_conversion[0])),
            reverse=True
        )

        # 'matching_conversions' will be a list of (class, conversion function) so get the first value
        # (the one with the longest MRO) and get the conversion function out of it
        most_specific_conversion = matching_conversions[0][1]

        return most_specific_conversion(entity)

    def make_message_serializable(self, message: TYPE_TO_SERIALIZE) -> SERIALIZABLE_TYPE:
        if isinstance(message, DjangoModel):
            return self.convert(message)
        return super().make_message_serializable(message)


DjangoObjectSerializer = __DjangoMessageSerializer()
"""A naive Django object serializer"""

make_message_serializable = DjangoObjectSerializer.make_message_serializable
