from __future__ import annotations

import logging
from contextlib import suppress

from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.rollback import RollbackCommand, RollbackCommandsManager

from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.folder_handler import (
    FolderHandler,
    FolderIsNotEmpty,
    FolderNotFound,
)
from cloudshell.cp.vcenter.handlers.vcenter_path import VcenterPath
from cloudshell.cp.vcenter.handlers.vsphere_sdk_handler import VSphereSDKHandler

logger = logging.getLogger(__name__)


class CreateVmFolder(RollbackCommand):
    def __init__(
        self,
        rollback_manager: RollbackCommandsManager,
        cancellation_manager: CancellationContextManager,
        dc: DcHandler,
        vm_folder_path: VcenterPath,
        vsphere_client: VSphereSDKHandler | None,
    ):
        super().__init__(rollback_manager, cancellation_manager)
        self._dc = dc
        self._vm_folder_path = vm_folder_path
        self._vsphere_client = vsphere_client

    def _execute(self, *args, **kwargs) -> FolderHandler:
        logger.info(f"Creating VM folders for path: {self._vm_folder_path}")
        vm_folder = self._dc.get_or_create_vm_folder(self._vm_folder_path)
        if self._vsphere_client is not None:
            try:
                self._vsphere_client.assign_tags(obj=vm_folder)
            except Exception:
                with suppress(FolderIsNotEmpty):
                    vm_folder.destroy()
                raise
        return vm_folder

    def rollback(self):
        with suppress(FolderIsNotEmpty, FolderNotFound):
            folder = self._dc.get_vm_folder(self._vm_folder_path)
            folder.destroy()
