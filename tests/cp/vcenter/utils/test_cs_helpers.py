from __future__ import annotations

from unittest.mock import Mock

from cloudshell.cp.vcenter.utils.cs_helpers import on_task_progress_check_if_cancelled


def test_on_task_progress_check_if_cancelled():
    cancellation_context_mgr = Mock()
    cancellation_context_mgr.cancellation_context.is_cancelled = False
    task = Mock()

    on_progress = on_task_progress_check_if_cancelled(cancellation_context_mgr)

    on_progress(task, None)
    task.cancel.assert_not_called()

    cancellation_context_mgr.cancellation_context.is_cancelled = True
    on_progress(task, None)
    task.cancel.assert_called_once()
