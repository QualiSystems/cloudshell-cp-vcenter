from __future__ import annotations

import logging
from contextlib import suppress
from threading import Lock

from attrs import define, field

from cloudshell.cp.core.reservation_info import ReservationInfo

from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.folder_handler import (
    FolderIsNotEmpty,
    FolderNotFound,
)
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.vm_handler import VmNotFound
from cloudshell.cp.vcenter.handlers.vsphere_sdk_handler import VSphereSDKHandler
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import ShutdownMethod, VCenterResourceConfig
from cloudshell.cp.vcenter.utils.vm_helpers import get_vm_folder_path

logger = logging.getLogger(__name__)

folder_delete_lock = Lock()


def delete_instance(
    deployed_app: BaseVCenterDeployedApp,
    resource_conf: VCenterResourceConfig,
    reservation_info: ReservationInfo,
) -> None:
    DeleteFlow(deployed_app, resource_conf, reservation_info).delete()


@define
class DeleteFlow:
    _deployed_app: BaseVCenterDeployedApp
    _resource_conf: VCenterResourceConfig
    _reservation_info: ReservationInfo
    _si: SiHandler = field(init=False)
    _vsphere_client: VSphereSDKHandler = field(init=False)
    _dc: DcHandler = field(init=False)

    def __attrs_post_init__(self):
        self._si = SiHandler.from_config(self._resource_conf)
        self._vsphere_client = VSphereSDKHandler.from_config(
            resource_config=self._resource_conf,
            reservation_info=self._reservation_info,
            si=self._si,
        )
        self._dc = DcHandler.get_dc(self._resource_conf.default_datacenter, self._si)

    def delete(self) -> None:
        tags = self._delete_vm()
        tags |= self._delete_folder()
        self._delete_tags(tags)

    def _delete_vm(self) -> set[str]:
        vm_uuid = self._deployed_app.vmdetails.uid
        tags = set()
        try:
            vm = self._dc.get_vm_by_uuid(vm_uuid)
        except VmNotFound:
            logger.warning(f"Trying to remove vm {vm_uuid} but it is not exists")
        else:
            self._si.delete_customization_spec(vm.name)
            tags |= self._get_tags(vm)

            soft = self._resource_conf.shutdown_method is ShutdownMethod.SOFT
            vm.power_off(soft=soft)

            vm.delete()
        return tags

    def _delete_folder(self) -> set[str]:
        path = get_vm_folder_path(
            self._deployed_app,
            self._resource_conf,
            self._reservation_info.reservation_id,
        )
        tags = set()
        with folder_delete_lock:
            try:
                folder = self._dc.get_vm_folder(path)
            except FolderNotFound:
                pass
            else:
                tags |= self._get_tags(folder)
                with suppress(FolderIsNotEmpty):
                    folder.destroy()
        return tags

    def _get_tags(self, obj) -> set[str]:
        if self._vsphere_client:
            return set(self._vsphere_client.get_attached_tags(obj))

    def _delete_tags(self, tags: set[str]) -> None:
        if self._vsphere_client:
            self._vsphere_client.delete_unused_tags(tags)
