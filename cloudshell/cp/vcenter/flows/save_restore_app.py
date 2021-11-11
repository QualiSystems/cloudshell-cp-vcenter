from __future__ import annotations

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

from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.flows.deploy_vm.commands.clone_vm import CloneVMCommand
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
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
    _vcenter_client: VCenterAPIClient
    _resource_conf: VCenterResourceConfig
    _cs_api: CloudShellAPISession
    _cancellation_manager: CancellationContextManager
    _logger: Logger

    def __attrs_post_init__(self):
        self._rollback_manager = RollbackCommandsManager(logger=self._logger)
        self._task_waiter = VcenterCancellationContextTaskWaiter(
            self._logger, self._cancellation_manager
        )

    def save_apps(self, save_actions: Iterable[SaveApp]) -> str:
        dc = self._vcenter_client.get_dc(self._resource_conf.default_datacenter)
        dc = DcHandler(dc)
        results = [self._save_app(action, dc) for action in save_actions]
        return DriverResponse(results).to_driver_response_json()

    def delete_saved_apps(self, delete_saved_app_actions: list[DeleteSavedApp]):
        dc = self._vcenter_client.get_dc(self._resource_conf.default_datacenter)
        dc = DcHandler(dc)
        for action in delete_saved_app_actions:
            self._delete_saved_app(action, dc)
        self._delete_folders(delete_saved_app_actions, dc)

    def _create_deploy_app(
        self, save_action: SaveApp, vm: VmHandler
    ) -> VMFromVMDeployApp:
        attrs = save_action.actionParams.deploymentPathAttributes
        attrs[VMFromVMDeployApp.ATTR_NAMES.vcenter_vm] = vm.path
        # todo check attributes is dict or list
        deploy_app = VMFromVMDeployApp(attributes=attrs)
        if self._resource_conf.vm_location:  # use vm location from the resource
            deploy_app.vm_location = self._resource_conf.vm_location
        if self._resource_conf.saved_sandbox_storage:
            deploy_app.vm_storage = self._resource_conf.saved_sandbox_storage
        return deploy_app

    def _prepare_folders(
        self, deploy_app: VMFromVMDeployApp, dc: DcHandler, reservation_id: str
    ):
        # todo do we need deploy app?
        vm_location_folder = self._vcenter_client.get_folder(
            deploy_app.vm_location, dc._entity  # fixme
        )
        saved_sandboxes_folder = self._vcenter_client.get_or_create_folder(
            SAVED_SANDBOXES_FOLDER, vm_location_folder
        )
        return self._vcenter_client.get_or_create_folder(
            reservation_id, saved_sandboxes_folder
        )

    def _get_vm_resource_pool(self, deploy_app: VMFromVMDeployApp, dc: DcHandler):
        r_conf = self._resource_conf
        r_pool_name = deploy_app.vm_resource_pool or r_conf.vm_resource_pool
        cluster_name = deploy_app.vm_cluster or r_conf.vm_cluster
        if r_pool_name:
            return self._vcenter_client.get_resource_pool(r_pool_name, dc._entity)
        if cluster_name:
            cluster = self._vcenter_client.get_cluster(cluster_name, dc._entity)
            return cluster.resourcePool

    def _save_app(self, save_action: SaveApp, dc: DcHandler) -> SaveAppResult:
        with self._cancellation_manager:
            vm_uuid = save_action.actionParams.sourceVmUuid
            r_id = save_action.actionParams.savedSandboxId
            vm = dc.get_vm_by_uuid(vm_uuid, self._vcenter_client)
            deploy_app = self._create_deploy_app(save_action, vm)
            vm_resource_pool = self._get_vm_resource_pool(deploy_app, dc)
            vm_storage = self._vcenter_client.get_storage(
                deploy_app.vm_storage, dc._entity
            )

        with self._cancellation_manager:
            vm_folder = self._prepare_folders(deploy_app, dc, r_id)

        vm_power_state = None
        if deploy_app.behavior_during_save == "Power Off":
            vm_power_state = vm.power_state
            vm.power_off(soft=False, logger=self._logger)

        new_vm_name = f"Clone of {vm.name[0:32]}"
        cloned_vm = self._clone_vm(
            vm._entity,
            new_vm_name,
            vm_resource_pool,
            vm_storage,
            vm_folder,
        )
        cloned_vm = VmHandler(cloned_vm)
        cloned_vm.create_snapshot(SNAPSHOT_NAME, dump_memory=False, logger=self._logger)

        if vm_power_state is PowerState.ON:
            vm.power_on(self._logger)

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

    def _clone_vm(self, vm_template, vm_name, vm_resource_pool, vm_storage, vm_folder):
        return CloneVMCommand(
            rollback_manager=self._rollback_manager,
            cancellation_manager=self._cancellation_manager,
            vcenter_client=self._vcenter_client,
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
                vm = dc.get_vm_by_uuid(vm_uuid, self._vcenter_client)
            vm.power_off(soft=False, logger=self._logger, task_waiter=self._task_waiter)
            vm.delete(self._logger, self._task_waiter)

    def _delete_folders(
        self, delete_saved_app_actions: list[DeleteSavedApp], dc: DcHandler
    ):
        folders_to_delete = {
            (
                f"{self._resource_conf.vm_location}"
                f"/{SAVED_SANDBOXES_FOLDER}"
                f"/{action.actionParams.savedSandboxId}"
            )
            for action in delete_saved_app_actions
        }
        for folder_path in folders_to_delete:
            folder = self._vcenter_client.get_folder(folder_path, dc._entity)
            task = folder.Destroy_Task()
            self._task_waiter.wait_for_task(task=task)
