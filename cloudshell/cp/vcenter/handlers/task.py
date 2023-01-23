from __future__ import annotations

from enum import Enum
from typing import Any

from attrs import define, field
from attrs.setters import frozen
from pyVim.task import WaitForTask
from pyVmomi import vim


class TaskState(Enum):
    success = "success"
    running = "running"
    queued = "queued"
    error = "error"


@define(repr=False)
class Task:
    vc_obj: vim.Task = field(on_setattr=frozen)

    def __repr__(self):
        return f"Task {self.key}"

    @property
    def key(self) -> str:
        return self.vc_obj.info.key

    @property
    def result(self) -> Any:
        return self.vc_obj.info.result

    @property
    def cancelable(self) -> bool:
        return self.vc_obj.info.cancelable

    @property
    def cancelled(self) -> bool:
        return self.vc_obj.info.cancelled

    @property
    def state(self) -> TaskState:
        return TaskState(self.vc_obj.info.state)

    @property
    def error_msg(self) -> str | None:
        if self.state is not TaskState.error:
            return None

        error = self.vc_obj.info.error
        if error and error.faultMessage:
            emsg = "; ".join([err.message for err in error.faultMessage])
        elif error and error.msg:
            emsg = error.msg
        else:
            emsg = "Task failed with some error"
        return emsg

    def wait(
        self,
        raise_on_error: bool = True,
    ) -> None:
        WaitForTask(self.vc_obj, raiseOnError=raise_on_error)

    def cancel(self) -> None:
        if self.cancelable and not self.cancelled:
            self.vc_obj.CancelTask()
