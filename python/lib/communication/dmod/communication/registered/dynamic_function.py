import typing
import functools
import inspect


class DynamicFunctionMixin:
    """
    A mixin that provides the tools necessary to find functions within a class instance that bear specific
    decorators and attributes.

    This is useful for abstract classes that need to keep track of and call implemented functions from subclasses
    """
    @functools.lru_cache
    def _get_dynamic_functions(
        self,
        decorator_name: str,
        required_attributes: typing.List[str] = None
    ) -> typing.Dict[str, typing.Callable]:
        if required_attributes is None:
            required_attributes = list()
        elif isinstance(required_attributes, str) or not isinstance(required_attributes, typing.Sequence):
            required_attributes = [required_attributes]

        def is_method_and_has_decorator(member) -> bool:
            """
            A filter dictating whether an encountered member is a method with a specific decorator and required
            attributes

            Args:
                member: The instance member to check

            Returns:
                True if the encountered member meets the specified requirements
            """
            has_decorator_and_is_method = (inspect.ismethod(member) or inspect.iscoroutinefunction(member)) \
                                          and hasattr(member, decorator_name)

            for required_attribute in required_attributes:
                if not hasattr(member, required_attribute):
                    return False

            return has_decorator_and_is_method

        # Collect all functions within this class that have the correct decorator and meet the attribute requirements
        functions: typing.Dict[str, typing.Callable] = {
            function_name: function
            for function_name, function in inspect.getmembers(self, predicate=is_method_and_has_decorator)
        }

        return functions
