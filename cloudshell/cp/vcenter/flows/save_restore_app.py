from __future__ import annotations

import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress

from attrs import define

from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.request_actions import DriverResponse
from cloudshell.cp.core.request_actions.models import (
    Artifact,
    Attribute,
    DeleteSavedApp,
    DeleteSavedAppResult,
    SaveApp,
    SaveAppResult,
)
from cloudshell.cp.core.rollback import RollbackCommandsManager

from cloudshell.cp.vcenter.actions.vm_network import VMNetworkActions
from cloudshell.cp.vcenter.constants import VM_FROM_LINKED_CLONE_DEPLOYMENT_PATH
from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.flows.deploy_vm.commands import CloneVMCommand
from cloudshell.cp.vcenter.handlers.config_spec_handler import ConfigSpecHandler
from cloudshell.cp.vcenter.handlers.datastore_handler import DatastoreHandler
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.folder_handler import (
    FolderHandler,
    FolderIsNotEmpty,
    FolderNotFound,
)
from cloudshell.cp.vcenter.handlers.resource_pool import ResourcePoolHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.vcenter_path import VcenterPath
from cloudshell.cp.vcenter.handlers.vm_handler import PowerState, VmHandler, VmNotFound
from cloudshell.cp.vcenter.models.base_deployment_app import (
    VCenterVMFromCloneDeployAppAttributeNames,
)
from cloudshell.cp.vcenter.models.deploy_app import VMFromVMDeployApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig
from cloudshell.cp.vcenter.utils.cs_helpers import on_task_progress_check_if_cancelled

logger = logging.getLogger(__name__)

SAVED_SANDBOXES_FOLDER = "Saved Sandboxes"
SNAPSHOT_NAME = "artifact"


class SaveRestoreAttributeMissed(BaseVCenterException):
    def __init__(self, attr_name: str):
        self.attr_name = attr_name
        super().__init__(
            f"Attribute {attr_name} should be in the save app attributes or in the "
            f"vCenter resource"
        )


@define(slots=False)
class SaveRestoreAppFlow:
    _si: SiHandler
    _resource_conf: VCenterResourceConfig
    _cs_api: CloudShellAPISession
    _cancellation_manager: CancellationContextManager

    def __attrs_post_init__(self):
        self._rollback_manager = RollbackCommandsManager(logger)
        self._on_task_progress = on_task_progress_check_if_cancelled(
            self._cancellation_manager
        )
        self._dc = DcHandler.get_dc(self._resource_conf.default_datacenter, self._si)
        self._holding_network = self._dc.get_network(
            self._resource_conf.holding_network
        )

    def save_apps(self, save_actions: Iterable[SaveApp]) -> str:
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(self._save_app, save_actions))
        return DriverResponse(results).to_driver_response_json()

    def delete_saved_apps(self, delete_saved_app_actions: list[DeleteSavedApp]) -> str:
        with ThreadPoolExecutor() as executor:
            list(executor.map(self._delete_saved_app, delete_saved_app_actions))
        self._delete_folders(delete_saved_app_actions)
        results = [
            DeleteSavedAppResult(action.actionId) for action in delete_saved_app_actions
        ]
        return DriverResponse(results).to_driver_response_json()

    def _get_app_attrs(self, save_action: SaveApp, vm_path: str) -> dict[str, str]:
        attrs = {
            a.attributeName.rsplit(".", 1)[-1]: a.attributeValue
            for a in save_action.actionParams.deploymentPathAttributes
        }
        attrs[VMFromVMDeployApp.ATTR_NAMES.vcenter_vm] = vm_path

        conf = self._resource_conf
        attr_names = VMFromVMDeployApp.ATTR_NAMES
        if conf.vm_location:
            attrs[attr_names.vm_location] = conf.vm_location
        if conf.saved_sandbox_storage:
            attrs[attr_names.vm_storage] = conf.saved_sandbox_storage
        r_pool = attrs[attr_names.vm_resource_pool] or conf.vm_resource_pool
        cluster_name = attrs[attr_names.vm_cluster] or conf.vm_cluster
        attrs[attr_names.vm_resource_pool] = r_pool
        attrs[attr_names.vm_cluster] = cluster_name

        if attrs[attr_names.behavior_during_save] == "Inherited":
            attrs[
                attr_names.behavior_during_save
            ] = self._resource_conf.behavior_during_save

        return attrs

    def _validate_app_attrs(self, attrs: dict[str, str]):
        if not attrs.get(VMFromVMDeployApp.ATTR_NAMES.vm_storage):
            raise SaveRestoreAttributeMissed(VMFromVMDeployApp.ATTR_NAMES.vm_storage)
        if not attrs.get(
            VMFromVMDeployApp.ATTR_NAMES.vm_resource_pool
        ) or not attrs.get(VMFromVMDeployApp.ATTR_NAMES.vm_cluster):
            raise SaveRestoreAttributeMissed(VMFromVMDeployApp.ATTR_NAMES.vm_cluster)
        if not attrs.get(VMFromVMDeployApp.ATTR_NAMES.vm_location):
            raise SaveRestoreAttributeMissed(VMFromVMDeployApp.ATTR_NAMES.vm_location)
        if not attrs.get(VMFromVMDeployApp.ATTR_NAMES.behavior_during_save):
            raise SaveRestoreAttributeMissed(
                VMFromVMDeployApp.ATTR_NAMES.behavior_during_save
            )

    def _prepare_folders(self, vm_location: str, sandbox_id: str) -> FolderHandler:
        folder_path = VcenterPath(vm_location)
        folder_path.append(SAVED_SANDBOXES_FOLDER)
        folder_path.append(sandbox_id)
        return self._dc.get_or_create_vm_folder(folder_path)

    def _get_vm_resource_pool(self, app_attrs: dict[str, str]) -> ResourcePoolHandler:
        r_pool_name = app_attrs.get(VMFromVMDeployApp.ATTR_NAMES.vm_resource_pool)
        cluster_name = app_attrs.get(VMFromVMDeployApp.ATTR_NAMES.vm_cluster)
        compute_entity = self._dc.get_compute_entity(cluster_name)
        return compute_entity.get_resource_pool(r_pool_name)

    def _save_app(self, save_action: SaveApp) -> SaveAppResult:
        logger.info(f"Starting save app {save_action.actionParams.sourceAppName}")
        logger.debug(f"Save action model: {save_action}")
        with self._cancellation_manager:
            vm_uuid = save_action.actionParams.sourceVmUuid
            sandbox_id = save_action.actionParams.savedSandboxId
            vm = self._dc.get_vm_by_uuid(vm_uuid)
            app_attrs = self._get_app_attrs(save_action, str(vm.path))
            vm_resource_pool = self._get_vm_resource_pool(app_attrs)
            vm_storage = self._dc.get_datastore(
                app_attrs[VMFromVMDeployApp.ATTR_NAMES.vm_storage]
            )

        with self._cancellation_manager:
            vm_folder = self._prepare_folders(
                app_attrs[VMFromVMDeployApp.ATTR_NAMES.vm_location], sandbox_id
            )

        with self._behavior_during_save(vm, app_attrs):
            new_vm_name = f"Clone of {vm.name[0:32]}"
            config_spec = ConfigSpecHandler(None, None, [], None)
            copy_source_uuid = app_attrs.get(
                VMFromVMDeployApp.ATTR_NAMES.copy_source_uuid, False
            )
            if copy_source_uuid:
                config_spec.bios_uuid = vm.bios_uuid
            cloned_vm = self._clone_vm(
                vm,
                new_vm_name,
                vm_resource_pool,
                vm_storage,
                vm_folder,
                config_spec,
            )

            net_actions = VMNetworkActions(
                self._resource_conf, self._cancellation_manager
            )

            for vnic in cloned_vm.vnics:
                network = vnic.network

                if net_actions.is_quali_network(network.name):
                    vnic.connect(self._holding_network)

            cloned_vm.create_snapshot(
                SNAPSHOT_NAME,
                dump_memory=False,
                on_task_progress=self._on_task_progress,
            )

        return self._prepare_result(cloned_vm, save_action)

    @staticmethod
    def _prepare_result(cloned_vm: VmHandler, save_action: SaveApp) -> SaveAppResult:
        attr_names = VCenterVMFromCloneDeployAppAttributeNames
        copy_vm_uuid = next(
            (
                x.attributeValue
                for x in save_action.actionParams.deploymentPathAttributes
                if x.attributeName == attr_names.copy_source_uuid
            ),
            "False",
        )
        entity_attrs = [
            Attribute(attr_names.vcenter_vm, str(cloned_vm.path)),
            Attribute(attr_names.vcenter_vm_snapshot, SNAPSHOT_NAME),
            Attribute(attr_names.hostname, None),
            Attribute(attr_names.private_ip, None),
            Attribute(attr_names.customization_spec, None),
            Attribute(attr_names.copy_source_uuid, copy_vm_uuid),
        ]

        return SaveAppResult(
            save_action.actionId,
            artifacts=[Artifact(cloned_vm.uuid, cloned_vm.name)],
            savedEntityAttributes=entity_attrs,
            saveDeploymentModel=VM_FROM_LINKED_CLONE_DEPLOYMENT_PATH,
        )

    def _clone_vm(
        self,
        vm_template: VmHandler,
        vm_name: str,
        vm_resource_pool: ResourcePoolHandler,
        vm_storage: DatastoreHandler,
        vm_folder: FolderHandler,
        config_spec: ConfigSpecHandler | None = None,
    ) -> VmHandler:

        return CloneVMCommand(
            rollback_manager=self._rollback_manager,
            cancellation_manager=self._cancellation_manager,
            on_task_progress=self._on_task_progress,
            vm_template=vm_template,
            vm_name=vm_name,
            vm_resource_pool=vm_resource_pool,
            vm_storage=vm_storage,
            vm_folder=vm_folder,
            vm_snapshot=None,
            config_spec=config_spec,
        ).execute()

    def _delete_saved_app(self, action: DeleteSavedApp) -> None:
        for artifact in action.actionParams.artifacts:
            vm_uuid = artifact.artifactRef
            with self._cancellation_manager:
                try:
                    vm = self._dc.get_vm_by_uuid(vm_uuid)
                except VmNotFound:
                    continue
            vm.power_off(soft=False, on_task_progress=self._on_task_progress)
            vm.delete(self._on_task_progress)

    def _delete_folders(self, delete_saved_app_actions: list[DeleteSavedApp]) -> None:
        path = VcenterPath(self._resource_conf.vm_location) + SAVED_SANDBOXES_FOLDER
        try:
            sandbox_folder = self._dc.get_vm_folder(path)
        except FolderNotFound:
            return

        for action in delete_saved_app_actions:
            sandbox_id = action.actionParams.savedSandboxId
            with suppress(FolderNotFound, FolderIsNotEmpty):
                folder = sandbox_folder.get_folder(sandbox_id)
                folder.destroy(self._on_task_progress)

    @contextmanager
    def _behavior_during_save(self, vm: VmHandler, attrs):
        vm_power_state = None
        if attrs[VMFromVMDeployApp.ATTR_NAMES.behavior_during_save] == "Power Off":
            vm_power_state = vm.power_state
            vm.power_off(soft=False)

        yield

        if vm_power_state is PowerState.ON:
            vm.power_on(on_task_progress=self._on_task_progress)
