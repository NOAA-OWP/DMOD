from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop, Task
from typing import Optional


class AsyncServiceInterface(ABC):

    @abstractmethod
    def add_async_task(self, coro) -> int:
        """
        Add a coroutine that will be run as a task in the main service event loop.

        Implementations may have a "built-in" task, which could potentially be executed via a call to
        ``run_until_complete()``.  This method gives the opportunity to schedule additional tasks, ensuring any are
        scheduled prior to any blocking caused by ``run_until_complete()``.  Tasks can also be added later if there is
        not blocking or it has finished.

        However, this method does not

        Parameters
        ----------
        coro
            A coroutine

        Returns
        ----------
        int
            The index of the ::class:`Task` object for the provided coro.
        """
        pass

    @abstractmethod
    def get_task_object(self, index: int) -> Optional[Task]:
        """
        Get the ::class:`Task` object for the task run by the service, based on the associated index returned when
        ::method:`add_async_task` was called, returning ``None`` if the service has not starting running yet.

        Parameters
        ----------
        index
            The associated task index

        Returns
        -------
        Optional[Task]
            The desired async ::class:`Task` object, or ``None`` if the service is not yet running tasks.
        """
        pass

    @property
    @abstractmethod
    def loop(self) -> AbstractEventLoop:
        """
        Get the event loop for the service.

        Returns
        -------
        AbstractEventLoop
            The event loop for the service.
        """
        pass

    @abstractmethod
    def run(self):
        """
        Run the service indefinitely by starting execution of its event loop, ensuring all tasks previously added with
        ::method:`add_async_task` and any built-in task are scheduled.
        """
        pass

    @abstractmethod
    async def shutdown(self, shutdown_signal=None):
        """
        Wait for current tasks to finish, cancel all others, and shutdown the service.
        """
        pass
