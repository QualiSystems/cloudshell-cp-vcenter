from __future__ import annotations

from cloudshell.cp.core.request_actions.models import SaveApp
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler


class SaveModelResponse:
    def __init__(
            self,
            save_action: SaveApp,
            vm_handler: VmHandler | None = None,
            error: Exception | None = None,
    ):
        """SaveModelResponse.

        :param saved_artifact:
        """
        self.vm_handler = vm_handler
        self.save_action = save_action
        self.error = error
