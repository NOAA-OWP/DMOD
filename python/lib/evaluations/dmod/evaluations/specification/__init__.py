from .template import TemplateManager
from .template import TemplateDetails
from .template import FileTemplateManager
from .base import Specification
from .base import TemplatedSpecification
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

SPECIFICATION_TYPES = typing.Sequence[typing.Type[Specification]]

def get_specification_types(all_specifications: bool = False, *args, **kwargs) -> SPECIFICATION_TYPES:
    from .base import get_subclasses

    if all_specifications:
        base_class = Specification
    else:
        base_class = TemplatedSpecification

    return get_subclasses(base_class)


def get_specification_options(all_specifications: bool = False, *args, **kwargs) -> typing.Sequence[typing.Tuple[str, str]]:
    from .base import get_subclasses

    if all_specifications:
        base_class = Specification
    else:
        base_class = TemplatedSpecification

    return [
        (
            cls.get_specification_type(),
            cls.get_specification_description()
        )
        for cls in get_subclasses(base_class)
    ]


setattr(TemplateManager, "get_specification_types", get_specification_options)