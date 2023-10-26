"""
@TODO: Put a module wide description here
"""
from .base import Specification
from .base import TemplatedSpecification
from .base import TemplateDetails
from .base import TemplateManagerProtocol

from .evaluation import EvaluationSpecification
from .threshold import ThresholdDefinition
from .threshold import ThresholdSpecification
from .scoring import SchemeSpecification
from .locations import LocationSpecification
from .data import DataSourceSpecification
from .scoring import MetricSpecification
from .fields import FieldMappingSpecification
from .fields import ValueSelector
from .locations import CrosswalkSpecification
from .backend import BackendSpecification
from .fields import AssociatedField
from .unit import UnitDefinition
from .threshold import ThresholdApplicationRules
from .evaluation import EvaluationResults
from .backend import LoaderSpecification

import typing

_SC = typing.TypeVar("_SC", bound=Specification, covariant=True)


def get_templated_classes(*args, **kwargs) -> typing.Sequence[typing.Type[_SC]]:
    from .base import get_subclasses
    return get_subclasses(TemplatedSpecification)


def get_specification_options(*args, **kwargs) -> typing.Sequence[typing.Tuple[str, str]]:
    return [
        (cls.get_specification_type(), cls.get_specification_description())
        for cls in get_templated_classes()
    ]


