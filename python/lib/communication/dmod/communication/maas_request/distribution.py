class Distribution(object):
    """
    Represents the definition of a distribution of numbers
    """

    def __init__(
        self, minimum: int = 0, maximum: int = 0, distribution_type: str = "normal"
    ):
        """
        :param int minimum: The lower bound for the distribution
        :param int maximum: The upper bound of the distribution
        :param str distribution_type: The type of the distribution
        """
        self.minimum = minimum
        self.maximum = maximum
        self.distribution_type = distribution_type

    def to_dict(self):
        return {
            "distribution": {
                "min": self.minimum,
                "max": self.maximum,
                "type": self.distribution_type,
            }
        }

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return self.__str__()
