from dmod.core.serializable import Serializable


class Scalar(Serializable):
    """
    Represents a parameter value that is bound to a single number
    """
    scalar: int

    def __str__(self):
        return str(self.scalar)

    def __repr__(self):
        return self.__str__()


class Parameter(Serializable):
    """
    Base clase for model parameter descriptions that a given model may expose to DMOD for dynamic parameter selection.
    """
    name: str


class ScalarParameter(Parameter):
    """
    A Scalar parameter is a simple interger parameter who's valid range are integer increments between
    min and max, inclusive.
    """
    min: int
    max: int
