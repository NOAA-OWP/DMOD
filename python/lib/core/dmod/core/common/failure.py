"""
Provides a mechanism for recording and explaining operation failures
"""
import typing


class Failure:
    """
    Metadata about how a task failed
    """
    def __init__(self, task_name: str, reason: str, message: str, exception: BaseException = None):
        """
        Constructor

        Args:
            task_name: The name of the task that failed
            reason: Why the task failed
            message: A detailed explanation for why the task failed
            exception: The exception that caused the task to fail
        """
        self.task_name = task_name
        self.reason = reason
        self.message = message
        self.exception = exception

    @staticmethod
    def explain(failures: typing.List["Failure"]) -> str:
        """
        Generates an explanation as to why tasks may have failed

        Args:
            failures: Metadata from failed tasks

        Returns:
            A description of why a series of tasks failed
        """
        explanation = ""
        number_of_failures = len(failures)
        individual_failure_messages = [str(failure) for failure in failures]

        if number_of_failures == 1:
            explanation = individual_failure_messages[0]
        elif number_of_failures == 2:
            explanation = f"{individual_failure_messages[0]} and {individual_failure_messages[1]}"
        elif number_of_failures >= 3:
            explanation = ", ".join(individual_failure_messages[:-1]) + f", and {individual_failure_messages[-1]}"

        return explanation

    def __str__(self):
        message = f"Task '{self.task_name}' failed: {self.message}."

        if self.exception and self.exception != self.message:
            message += f" Error: {str(self.exception)}"

        return message

    def __repr__(self):
        return self.__str__()
