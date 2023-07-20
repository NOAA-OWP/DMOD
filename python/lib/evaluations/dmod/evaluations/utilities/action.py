"""
Provides a mechanism for stitching together complex conditional actions in a meaningful and more readable way

A central performer holds information about what to do when certain conditions match premade conditions.

Consider:

    >>> def print_a_is_5(*args, **kwargs):
    >>>     print("A is 5")
    >>>
    >>> def print_a_is_5_and_c_is_12(*args, **kwargs):
    >>>     print("A is 5 and C is 12")
    >>>
    >>> def print_neither(*args, **kwargs):
    >>>     print("A is not 5 and C is not 12")
    >>>
    >>> class ExampleConditions(ActionConditions):
    >>>     @classmethod
    >>>     def from_values(cls, data, *args, **kwargs):
    >>>         return cls(data.get("a",) == 5, data.get("c",) == 12)
    >>>     def __init__(self, a_is_5: bool = False, c_is_12: bool = False):
    >>>         self.a_is_5 = a_is_5
    >>>         self.c_is_12 = c_is_12
    >>>
    >>> class ExampleConditionsBuilder(ActionConditionBuilder):
    >>>     conditions_type = ExampleConditions
    >>>
    >>>     @classmethod
    >>>     def create_performer(cls):
    >>>         return ExamplePerformer()
    >>>
    >>>     @classmethod
    >>>     def create_conditions(cls):
    >>>         return cls.conditions_type()
    >>>
    >>>     def __init__(self, performer: "ExamplePerformer" = None):
    >>>         super().__init__(performer)
    >>>         self.__conditions = self.create_conditions()
    >>>
    >>>     @property
    >>>     def conditions(self):
    >>>         return self.__conditions
    >>>
    >>>     @property
    >>>     def a_is_5(self):
    >>>         self.__conditions.a_is_5 = True
    >>>         return self
    >>>
    >>>     @property
    >>>     def c_is_12(self):
    >>>         self.__conditions.c_is_12 = True
    >>>         return self
    >>>
    >>> class ExamplePerformer(Performer):
    >>>     builder_type = ExampleConditionsBuilder
    >>>
    >>>     @property
    >>>     def when(self):
    >>>         return self.builder_type(self)
    >>>
    >>>     def print(self, data: dict):
    >>>         self.perform(data)
    >>>
    >>> performer = ExamplePerformer()
    >>> performer.when.a_is_5.then(print_a_is_5)
    >>> performer.when.a_is_5.c_is_12.then(print_a_is_5_and_c_is_12)
    >>> performer.when.then(print_neither)
    >>> performer.print({"a": 4})
    A is not 5 and C is not 12
    >>> performer.print({"a": 5, "c": 12})
    A is 5 and C is 12
    >>> performer.print({"a": 5, "c": 13})
    A is 5
"""
from __future__ import annotations

import os
import typing
import abc
import inspect


class ActionConditions(abc.ABC):
    """
    A collection of booleans defining a certain state that will serve as the conditions for an action.
    Consider two types of ActionConditions: State Action Conditions and Prescribed Action Conditions.
    State Action Conditions will have every field set to true or false to indicate its value.
    Prescribed Action Conditions may only have a subset set. `compatibility` is meant to measure how close a
    State condition and a prescribed condition are. If one out of 8 fields are prescribed, it's not particularly
    specific but the state condition may match on the boolean value of that field. There may be another prescribed
    condition that has 7 fields set that the state condition matches on. In this case, the state condition has a
    higher compatibility than the other prescribed conditions due to how specific the second set of prescribed
    conditions are.
    """
    @classmethod
    @abc.abstractmethod
    def from_values(cls, *args, **kwargs) -> ActionConditions:
        """
        Create State conditions based on the interpretation of passed in objects
        """
        pass

    @property
    def specificity(self) -> int:
        """
        A measure of how specific the condition is

        Specificity increases with the number of set rules (i.e. values that are True or False)
        """
        return sum([
            1
            for value in self.__dict__.values()
            if value in (True, False)
        ])

    def compatibility(self, other: ActionConditions) -> float:
        """
        Determine how compatible two different merge conditions are

        A definitive rule is an attribute on the conditions that has a defined True or False value. A value of None
        means that it doesn't factor into the equation meaning that it does not contribute to the overall conditions'
        specificity. The conditions with the least amount of rules defines the maximum possible specificity.
        Conditions determined via values will be the most specific possible.

        Say Conditions A has 8 defined rules, Conditions B has 4 defined rules, Conditions C has 9 defined rules,
        and Conditions D has 17 defined rules based on input values. Conditions D will never define how specific the
        rules can be for comparison. When checking Conditions C against D, the values for all rules are the same
        except for one. Since there is a mismatch, the value of -1.0 is returned, meaning that it is absolutely
        non-compatible. Conditions D matches all the rules of Conditions A, making a compatibility score of 8 due to
        A's 8 rules. Conditions D matches all the rules of conditions B, yielding a compatibility score of 4,
        due to B's 4 rules. In the end, D is deemed more compatible with A since A was more specific, despite D
        matching both A and B.

        Args:
            other: The conditions to compare to

        Returns:
            A measure of how many definitive rules are followed multiplied by the complexity of the rule
        """
        these_conditions = self.get_condition_map()
        other_conditions = other.get_condition_map()

        primary_ruleset = these_conditions if len(self) < len(other) else other_conditions
        secondary_ruleset = other_conditions if len(self) < len(other) else these_conditions

        total_match = len(primary_ruleset)

        if total_match < 1:
            raise ValueError("A set of rule conditions is missing values")

        current_match = 0

        for rule_name, rule_value in primary_ruleset.items():
            if rule_name in secondary_ruleset and secondary_ruleset[rule_name] != rule_value:
                return -1.0
            elif rule_name in secondary_ruleset:
                current_match += 1

        return (current_match / total_match) * self.specificity

    def get_condition_map(self) -> typing.Mapping[str, bool]:
        """
        Create a map of all set conditions

        If 5 out 8 fields have been set to `True` or `False`, this should return a map between the names of those
        5 fields and their boolean values
        """
        return {
            condition: value
            for condition, value in self.__dict__.items()
            if value in (True, False)
        }

    def __len__(self):
        return len([
            value
            for value in self.__dict__.values()
            if value in (True, False)
        ])

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash((value for value in self.__dict__.values() if value in (True, False)))


ActionConditions_co = typing.TypeVar("ActionConditions_co", bound=ActionConditions, covariant=True)


class ActionConditionBuilder(typing.Generic[ActionConditions_co], abc.ABC):
    """
    A builder object used to create conditions in a streamlined fashion

    For each field in the ActionConditions that this builds, create a property which will set the field to True
    and return the builder for chaining. This will provide an interface that may be invoked as:

        >>> ExampleBuilder().condition_a.condition_b.condition_d.then(some_function)
    """
    conditions_type: typing.Type[ActionConditions_co] = None

    @classmethod
    def create_conditions(cls) -> ActionConditions_co:
        return cls.conditions_type()

    @property
    def conditions(self) -> ActionConditions_co:
        return self.__conditions

    @classmethod
    def conditions_from_values(cls, *args, **kwargs):
        return cls.conditions_type.from_values(*args, **kwargs)

    def __init__(self, performer: Performer = None):
        self.performer = performer
        """When to perform this particular merge action"""

        self.__conditions: ActionConditions_co = self.conditions_type()

    def then(self, action: typing.Callable) -> Performer:
        if self.performer is None:
            raise Exception("An action cannot be assigned to this builder's conditions - no performer is available")

        self.performer.add_handling(self.conditions, action)
        return self.performer


ActionConditionsBuilder_co = typing.TypeVar("ActionConditionsBuilder_co", bound=ActionConditionBuilder, covariant=True)


class Performer(typing.Generic[ActionConditionsBuilder_co], abc.ABC):
    builder_type: typing.Type[ActionConditionsBuilder_co] = None

    def __init__(self, builder_type: typing.Type[ActionConditionsBuilder_co] = None):
        if builder_type:
            self.builder_type = builder_type

        self.__plan: typing.List[typing.Tuple[ActionConditions, typing.Callable]] = list()

    @property
    def when(self) -> ActionConditionsBuilder_co:
        return self.builder_type(self)

    def add_handling(self, conditions: ActionConditions, action: typing.Callable):
        self.__plan.append((conditions, action))

    def perform(self, *args, **kwargs) -> typing.Any:
        value_conditions = self.builder_type.conditions_from_values(*args, **kwargs)

        compatible_action = None
        compatibility = 0

        for conditions, action in self.__plan:
            condition_compatibility = conditions.compatibility(value_conditions)

            if condition_compatibility > compatibility:
                compatibility = condition_compatibility
                compatible_action = action

        if compatible_action is not None:
            if inspect.ismethod(compatible_action):
                return compatible_action(value_conditions, *args, **kwargs)
            return compatible_action(self, value_conditions, *args, **kwargs)

        message = ["There are no handlers for the given conditions:"]
        current_line = ""

        condition_description = str(value_conditions)

        for character in condition_description:
            if character == " " and len(current_line) > 100:
                message.append(current_line)
                current_line = ""
            else:
                current_line += character

        if current_line:
            message.append(current_line)

        raise ValueError(os.linesep.join(message))