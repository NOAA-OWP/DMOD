"""
@TODO: Put a module wide description here
"""
import typing
import inspect


from .. import util


def is_a_value(o) -> bool:
    """
    Whether the passed object is a value and not some method or module or something

    Args:
        o:
            The object to be tested
    Returns:
        Whether the passed object is a value and not some method or module or something
    """
    # This will exclude methods, code, stuff like __get__, __set__, __add__, async objects, etc
    return not (
            inspect.iscode(o)
            or inspect.isdatadescriptor(o)
            or inspect.ismethoddescriptor(o)
            or inspect.ismemberdescriptor(o)
            or inspect.ismodule(o)
            or inspect.isgenerator(o)
            or inspect.isgeneratorfunction(o)
            or inspect.ismethod(o)
            or inspect.isawaitable(o)
            or inspect.isabstract(o)
    )


def value_matches_parameter_type(value, parameter: typing.Union[inspect.Parameter, typing.Type]) -> bool:
    """
    Checks to see if the given value matches that of the passed in parameter

    Since a parameter without an annotation is interpreted as `typing.Any`, `True` is returned if not type is indicated

    Args:
        value: The value to check
        parameter: The parameter to check

    Returns:
        Whether the given value conforms to the parameter
    """
    if isinstance(parameter, inspect.Parameter) and parameter.annotation == parameter.empty:
        return True

    if isinstance(parameter, inspect.Parameter):
        parameter = parameter.annotation

    is_typing_class = isinstance(parameter, typing._GenericAlias)
    is_union = is_typing_class and isinstance(parameter, typing._UnionGenericAlias)
    parameter_is_number = util.type_is_number(parameter)

    if parameter_is_number:
        return util.value_is_number(value)
    if is_union:
        return True in [
            value_matches_parameter_type(value, t)
            for t in typing.get_args(parameter)
        ]
    if is_typing_class:
        typing_class_name = getattr(parameter, "_name")
        return isinstance(value, typing.__dict__[typing_class_name])

    try:
        return isinstance(value, parameter)
    except TypeError:
        return False