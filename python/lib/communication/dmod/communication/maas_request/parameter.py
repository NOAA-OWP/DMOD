class Scalar:
    """
    Represents a parameter value that is bound to a single number
    """

    def __init__(self, scalar: int):
        """
        :param int scalar: The value for the parameter
        """
        self.scalar = scalar

    def to_dict(self):
        return {"scalar": self.scalar}

    def __str__(self):
        return str(self.scalar)

    def __repr__(self):
        return self.__str__()


class Parameter:
    """
    Base clase for model parameter descriptions that a given model may expose to DMOD for dynamic parameter selection.
    """

    def __init__(self, name):
        """
        Set the base meta data of the parameter
        """
        self.name = name


class ScalarParameter(Parameter):
    """
    A Scalar parameter is a simple interger parameter who's valid range are integer increments between
    min and max, inclusive.
    """

    def __init__(self, min, max):
        self.min = min
        self.max = max
