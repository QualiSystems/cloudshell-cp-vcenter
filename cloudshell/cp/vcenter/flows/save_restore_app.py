from __future__ import annotations

from contextlib import suppress
from logging import Logger
from typing import Iterable

import attr

from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.request_actions import DriverResponse
from cloudshell.cp.core.request_actions.models import (
    Artifact,
    Attribute,
    DeleteSavedApp,
    SaveApp,
    SaveAppResult,
)
from cloudshell.cp.core.rollback import RollbackCommandsManager

from cloudshell.cp.vcenter.flows.deploy_vm.commands.clone_vm import CloneVMCommand
from cloudshell.cp.vcenter.handlers.datastore_handler import DatastoreHandler
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.folder_handler import FolderHandler, FolderNotFound
from cloudshell.cp.vcenter.handlers.resource_pool import ResourcePoolHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.vcenter_path import VcenterPath
from cloudshell.cp.vcenter.handlers.vm_handler import PowerState, VmHandler
from cloudshell.cp.vcenter.models.base_deployment_app import (
    VCenterVMFromCloneDeployAppAttributeNames,
)
from cloudshell.cp.vcenter.models.deploy_app import VMFromVMDeployApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig
from cloudshell.cp.vcenter.utils.task_waiter import VcenterCancellationContextTaskWaiter

SAVED_SANDBOXES_FOLDER = "Saved Sandboxes"
SNAPSHOT_NAME = "artifact"


@attr.s(auto_attribs=True)
class SaveRestoreAppFlow:
    _resource_conf: VCenterResourceConfig
    _cs_api: CloudShellAPISession
    _cancellation_manager: CancellationContextManager
    _logger: Logger

    def __attrs_post_init__(self):
        self._si = SiHandler.from_config(self._resource_conf, self._logger)
        self._rollback_manager = RollbackCommandsManager(logger=self._logger)
        self._task_waiter = VcenterCancellationContextTaskWaiter(
            self._logger, self._cancellation_manager
        )

    def save_apps(self, save_actions: Iterable[SaveApp]) -> str:
        dc = DcHandler.get_dc(self._resource_conf.default_datacenter, self._si)
        results = [self._save_app(action, dc) for action in save_actions]
        return DriverResponse(results).to_driver_response_json()

    def delete_saved_apps(self, delete_saved_app_actions: list[DeleteSavedApp]):
        dc = DcHandler.get_dc(self._resource_conf.default_datacenter, self._si)
        for action in delete_saved_app_actions:
            self._delete_saved_app(action, dc)
        self._delete_folders(delete_saved_app_actions, dc)

    def _create_deploy_app(
        self, save_action: SaveApp, vm: VmHandler
    ) -> VMFromVMDeployApp:
        attrs = save_action.actionParams.deploymentPathAttributes
        attrs = {a.attributeName: a.attributeValue for a in attrs}
        attrs[VMFromVMDeployApp.ATTR_NAMES.vcenter_vm] = vm.path
        deploy_app = VMFromVMDeployApp(attributes=attrs)
        if self._resource_conf.vm_location:  # use vm location from the resource
            deploy_app.vm_location = self._resource_conf.vm_location
        if self._resource_conf.saved_sandbox_storage:
            deploy_app.vm_storage = self._resource_conf.saved_sandbox_storage
        return deploy_app

    @staticmethod
    def _prepare_folders(
        deploy_app: VMFromVMDeployApp, dc: DcHandler, reservation_id: str
    ) -> FolderHandler:
        folder_path = VcenterPath(deploy_app.vm_location)
        folder_path.append(SAVED_SANDBOXES_FOLDER)
        folder_path.append(reservation_id)

        return dc.get_or_create_vm_folder(folder_path)

    def _get_vm_resource_pool(
        self, deploy_app: VMFromVMDeployApp, dc: DcHandler
    ) -> ResourcePoolHandler:
        r_conf = self._resource_conf
        r_pool_name = deploy_app.vm_resource_pool or r_conf.vm_resource_pool
        cluster_name = deploy_app.vm_cluster or r_conf.vm_cluster
        if r_pool_name:
            return dc.get_resource_pool(r_pool_name)
        if cluster_name:
            cluster = dc.get_cluster(cluster_name)
            return cluster.get_resource_pool()

    def _save_app(self, save_action: SaveApp, dc: DcHandler) -> SaveAppResult:
        with self._cancellation_manager:
            vm_uuid = save_action.actionParams.sourceVmUuid
            r_id = save_action.actionParams.savedSandboxId
            vm = dc.get_vm_by_uuid(vm_uuid)
            deploy_app = self._create_deploy_app(save_action, vm)
            vm_resource_pool = self._get_vm_resource_pool(deploy_app, dc)
            vm_storage = dc.get_datastore(deploy_app.vm_storage)

        with self._cancellation_manager:
            vm_folder = self._prepare_folders(deploy_app, dc, r_id)

        vm_power_state = None
        if deploy_app.behavior_during_save == "Power Off":
            vm_power_state = vm.power_state
            vm.power_off(soft=False, logger=self._logger)

        new_vm_name = f"Clone of {vm.name[0:32]}"
        cloned_vm = self._clone_vm(
            vm,
            new_vm_name,
            vm_resource_pool,
            vm_storage,
            vm_folder,
        )
        cloned_vm.create_snapshot(SNAPSHOT_NAME, dump_memory=False, logger=self._logger)

        if vm_power_state is PowerState.ON:
            vm.power_on(self._logger)

        return self._prepare_result(cloned_vm, save_action)

    @staticmethod
    def _prepare_result(cloned_vm: VmHandler, save_action: SaveApp) -> SaveAppResult:
        attr_names = VCenterVMFromCloneDeployAppAttributeNames
        entity_attrs = [
            Attribute(attr_names.vcenter_vm, str(cloned_vm.path)),
            Attribute(attr_names.vcenter_vm_snapshot, SNAPSHOT_NAME),
            # attributes to ignore
            Attribute(attr_names.customization_spec, ""),
            Attribute(attr_names.private_ip, ""),
            Attribute(attr_names.cpu_num, ""),
            Attribute(attr_names.ram_amount, ""),
            Attribute(attr_names.hostname, ""),
            Attribute(attr_names.hdd_specs, ""),
        ]

        return SaveAppResult(
            save_action.actionId,
            artifacts=[Artifact(cloned_vm.uuid, cloned_vm.name)],
            savedEntityAttributes=entity_attrs,
        )

    def _clone_vm(
        self,
        vm_template: VmHandler,
        vm_name: str,
        vm_resource_pool: ResourcePoolHandler,
        vm_storage: DatastoreHandler,
        vm_folder: FolderHandler,
    ) -> VmHandler:
        return CloneVMCommand(
            rollback_manager=self._rollback_manager,
            cancellation_manager=self._cancellation_manager,
            logger=self._logger,
            task_waiter=self._task_waiter,
            vm_template=vm_template,
            vm_name=vm_name,
            vm_resource_pool=vm_resource_pool,
            vm_storage=vm_storage,
            vm_folder=vm_folder,
            vm_snapshot=None,
            config_spec=None,
        ).execute()

    def _delete_saved_app(self, action: DeleteSavedApp, dc: DcHandler):
        for artifact in action.actionParams.artifacts:
            with self._cancellation_manager:
                vm_uuid = artifact.artifactRef
                vm = dc.get_vm_by_uuid(vm_uuid)
            vm.power_off(soft=False, logger=self._logger, task_waiter=self._task_waiter)
            vm.delete(self._logger, self._task_waiter)

    def _delete_folders(
        self, delete_saved_app_actions: list[DeleteSavedApp], dc: DcHandler
    ):
        path = VcenterPath(self._resource_conf.vm_location) + SAVED_SANDBOXES_FOLDER
        try:
            sandbox_folder = dc.get_vm_folder(path)
        except FolderNotFound:
            return

        for action in delete_saved_app_actions:
            rid = action.actionParams.savedSandboxId
            with suppress(FolderNotFound):
                folder = sandbox_folder.get_folder(rid)
                folder.destroy(self._logger, self._task_waiter)
