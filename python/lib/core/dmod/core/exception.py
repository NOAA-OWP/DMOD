from abc import ABC


class DmodException(Exception, ABC):
    """
    Abstract base for custom exception types within DMOD.
    """

    def __init__(self, *args, **kwargs):
        super(DmodException, self).__init__(*args, **kwargs)


class DmodRuntimeError(DmodException):
    """
    A customized DMOD exception analogous to ::class:`RuntimeError`.

    A customized exception type extending from ::class:`DmodException`, which is analogous to the standard
    ::class:`RuntimeError` type.  It is intended for use in runtime error situations that are specific to DMOD but that
    don't fall into some other more targeted scenario that would be worthy of a specific exception.
    """

    def __init__(self, *args, **kwargs):
        super(DmodRuntimeError, self).__init__(*args, **kwargs)
