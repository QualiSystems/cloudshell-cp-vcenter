from typing import Any

from cloudshell.cp.core.cancellation_manager import CancellationContextManager

from cloudshell.cp.vcenter.handlers.task import ON_TASK_PROGRESS_TYPE, Task


def on_task_progress_check_if_cancelled(
    cancellation_manager: CancellationContextManager,
) -> ON_TASK_PROGRESS_TYPE:
    def on_progress(task: Task, progress: Any) -> None:
        if cancellation_manager.cancellation_context.is_cancelled:
            task.cancel()

    return on_progress
