from dmod.core.serializable import Serializable

from typing import Literal


class Distribution(Serializable):
    """
    Represents the definition of a distribution of numbers
    """

    minimum: int = 0
    """The lower bound for the distribution"""

    maximum: int = 0
    """The upper bound for the distribution"""

    distribution_type: Literal["normal"] = "normal"
    """The type of the distribution"""

    class Config(Serializable.Config):
        fields = {
            "distribution_type": {"alias": "type"},
            "minimum": {"alias": "min"},
            "maximum": {"alias": "max"},
        }

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return self.__str__()
