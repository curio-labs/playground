import logging

from concurrent.futures import Future, ThreadPoolExecutor

from typing import Any, Callable, Tuple

Task = Tuple[Callable[..., Any], Tuple[Any, ...]]
TaskList = list[Task]


LOG = logging.getLogger(__name__)


def execute_in_thread_pool(tasks: TaskList, max_workers: int) -> list[Any]:
    """
    This function executes a list of tasks in a thread pool and returns the results
    Args:
        tasks (TaskList): The list of tasks to execute
        max_workers (int): The maximum number of workers to use

    Returns:
        list[Any]: The list of results from the tasks

    """
    results: list[Any] = [None] * len(tasks)
    errors: int = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures: list[Future] = [executor.submit(task[0], *task[1]) for task in tasks]
        for i, future in enumerate(futures):
            try:
                results[
                    i
                ] = future.result()  # Store the result at the corresponding index
            except Exception as exc:
                LOG.warning(f"Error in future task: {exc} {type(exc)}")
                errors += 1
    if errors:
        LOG.warning(f"Total errors in {tasks[0][0].__name__}: {errors}")
    return results
