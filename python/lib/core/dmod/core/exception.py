from abc import ABC
from typing import Any, Dict


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


class DmodElementTypeError(DmodException):
    """
    Raised when operation or function is applied to a collection of a valid type with an element of an invalid type.

    The intent of this could be thought of as indicating a ::class:`ValueError` for a collection argument, while
    simultaneously indicating a ::class:`TypeError` for one of the nested elements of the collection argument.  I.e.,
    the collection object itself is usable, but one or more of its elements cannot be used as needed due to the
    element(s) being of an inappropriate type.
    """

    def __init__(self, *args, **kwargs):
        super(DmodElementTypeError, self).__init__(*args, **kwargs)


class DmodElementValueError(DmodException):
    """
    Raised to indicate something analogous to ::class:`ValueError`, but for an element of a collection argument.

    A specialized type for a specific scenario with collections similar to that covered by ::class:`ValueError`.  The
    intent is to have a specialized error to indicate when a collection object, of a valid type, has some element
    with a valid type but problematic value, as opposed to the collection itself having a    problematic value.  The
    distinction arises from the collection's "value" being thought of as an emergent property of the grouping of
    elements.

    A simple illustration of this is the collection with a value of "empty."  It may be useful to distinguish an error
    due to one of the elements having a bad value in isolation, from an error due to an empty collection arg.
    """

    def __init__(self, *args, **kwargs):
        super(DmodElementValueError, self).__init__(*args, **kwargs)


class DmodValueCombinationError(DmodException):
    """
    Raised to indicate that a function is called with individually valid arguments values that together are invalid.

    A specialized exception similar to ::class:`ValueError` to show that a function was called with arguments of the
    proper types but invalid values.  However, it applies only when all individual argument values are still within the
    domain of acceptable values for the associated parameter.

    For example, say there is a function ``arithmatic(param1: int, op: str, param2: int)`` that works intuitively for
    performing arithmatic operations.  This exception would apply if that function were passed **both** ``/`` for ``op``
    and ``0`` for ``param2``, even though individually those are perfectly reasonable arguments.
    """

    def __init__(self, func_name: str, bad_params: Dict[str, Any], *args, **kwargs):
        """
        Initialize this instance.

        Instances build their message in a type-specific format from provided parameters, which is passed upstream to
        the call to ``super().__init__()``.  However, if the standard ``message`` param is within ``kwargs``, or if
        there is a 0-th variable argument in ``args`` that is a string, then this value is prepended to the customized
        message value (along with `` | ``).

        Parameters
        ----------
        func_name : str
            The name of the function that requires raising this exception.
        bad_params : Dict[str, Any]
            The parameter values that when combined are invalid for use in the function, as a dictionary of parameter
            names mapped to argument values.
        args
        kwargs
        """
        list_str = ','.join(['{}={}'.format(str(key), bad_params[key]) for key in bad_params])
        msg = 'Cannot call function {} with the provided combination of values ({})'.format(func_name, list_str)

        if 'message' in kwargs and isinstance(kwargs['message'], str):
            msg = '{} | {}'.format(kwargs['message'], msg)
        elif len(args) > 0 and isinstance(args[0], str):
            msg = '{} | {}'.format(args[0], msg)

        super(DmodValueCombinationError, self).__init__(message=msg, *args, **kwargs)
