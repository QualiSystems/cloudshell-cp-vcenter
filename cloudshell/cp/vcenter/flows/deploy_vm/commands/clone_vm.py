from __future__ import annotations

from typing import TYPE_CHECKING

from cloudshell.cp.core.rollback import RollbackCommand

if TYPE_CHECKING:
    from cloudshell.cp.vcenter.api_client import VCenterAPIClient


class CloneVMCommand(RollbackCommand):
    def __init__(
        self,
        rollback_manager,
        cancellation_manager,
        vcenter_client: VCenterAPIClient,
        task_waiter,
        vm_template,
        vm_name,
        vm_resource_pool,
        vm_storage,
        vm_folder,
        vm_snapshot,
        config_spec,
        logger,
    ):
        super().__init__(
            rollback_manager=rollback_manager, cancellation_manager=cancellation_manager
        )
        self._vcenter_client = vcenter_client
        self._task_waiter = task_waiter
        self._vm_template = vm_template
        self._vm_name = vm_name
        self._vm_resource_pool = vm_resource_pool
        self._vm_storage = vm_storage
        self._vm_folder = vm_folder
        self._vm_snapshot = vm_snapshot
        self._config_spec = config_spec
        self._logger = logger
        self._cloned_vm = None

    def _execute(self):
        vm = self._vcenter_client.clone_vm(
            vm_template=self._vm_template,
            vm_name=self._vm_name,
            vm_resource_pool=self._vm_resource_pool,
            vm_storage=self._vm_storage,
            vm_folder=self._vm_folder,
            snapshot=self._vm_snapshot,
            task_waiter=self._task_waiter,
            config_spec=self._config_spec,
        )
        self._cloned_vm = vm
        return vm

    def rollback(self):
        self._vcenter_client.destroy_vm(vm=self._cloned_vm)
