import time

from pyVmomi import vim  # noqa

from cloudshell.cp.vcenter.exceptions import TaskFaultException


class VcenterTaskWaiter:
    DEFAULT_WAIT_TIME = 2

    def __init__(self, logger):
        self._logger = logger

    def _check_task(self, task):
        pass

    def wait_for_task(self, task):
        """Wait for the vCenter task to be processed."""
        while task.info.state in (
            vim.TaskInfo.State.running,
            vim.TaskInfo.State.queued,
        ):
            self._check_task(task)
            time.sleep(self.DEFAULT_WAIT_TIME)

        if task.info.state == vim.TaskInfo.State.success:
            return task.info.result

        if task.info.error.faultMessage:
            emsg = "; ".join([err.message for err in task.info.error.faultMessage])
        elif task.info.error.msg:
            emsg = task.info.error.msg
        else:
            emsg = "Task failed with some error"

        raise TaskFaultException(emsg)


class VcenterCancellationContextTaskWaiter(VcenterTaskWaiter):
    DEFAULT_WAIT_TIME = 2

    def __init__(self, logger, cancellation_manager):
        super().__init__(logger=logger)
        self._cancellation_manager = cancellation_manager

    def _check_task(self, task):
        if all(
            [
                task.info.cancelable,
                self._cancellation_manager.is_cancelled,
                not task.info.cancelled,
            ]
        ):
            # todo: check cancellation from the CloudShell portal
            task.CancelTask()
