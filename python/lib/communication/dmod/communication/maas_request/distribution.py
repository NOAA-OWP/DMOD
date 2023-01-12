from dmod.core.serializable import Serializable

from typing import Literal


class DistributionBounds(Serializable):
    minimum: int = 0
    maximum: int = 0
    distribution_type: Literal["normal"] = "normal"

    class Config:
        feilds = {
            "distribution_type": {"alias": "type"},
            "minimum": {"alias": "min"},
            "maximum": {"alias": "max"},
        }


class Distribution(Serializable):
    """
    Represents the definition of a distribution of numbers
    """

    distribution: DistributionBounds

    def __init__(
        self, minimum: int = 0, maximum: int = 0, distribution_type: str = "normal"
    ):
        """
        :param int minimum: The lower bound for the distribution
        :param int maximum: The upper bound of the distribution
        :param str distribution_type: The type of the distribution
        """
        super().__init__(
            distribution=DistributionBounds(
                minimum=minimum, maximum=maximum, distribution_type=distribution_type
            )
        )

    @property
    def minimum(self) -> int:
        """The lower bound for the distribution"""
        return self.distribution.minimum

    @minimum.setter
    def minimum(self, value: int):
        self.distribution.minimum = value

    @property
    def maximum(self) -> int:
        """The upper bound for the distribution"""
        return self.distribution.maximum

    @maximum.setter
    def maximum(self, value: int):
        self.distribution.maximum = value

    @property
    def distribution_type(self) -> str:
        """The type of the distribution"""
        return self.distribution.distribution_type

    @distribution_type.setter
    def distribution_type(self, value: str) -> str:
        self.distribution.distribution_type = value

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return self.__str__()
