from __future__ import annotations

import logging
from contextlib import suppress
from threading import Lock

from attrs import define, field

from cloudshell.cp.core.reservation_info import ReservationInfo

from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.folder_handler import (
    FolderHandler,
    FolderIsNotEmpty,
)
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.vm_handler import VmNotFound
from cloudshell.cp.vcenter.handlers.vsphere_sdk_handler import VSphereSDKHandler
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig

logger = logging.getLogger(__name__)

folder_delete_lock = Lock()


@define
class DeleteFlow:
    _si: SiHandler
    _deployed_app: BaseVCenterDeployedApp
    _resource_conf: VCenterResourceConfig
    _reservation_info: ReservationInfo | None
    _vsphere_client: VSphereSDKHandler = field(init=False)
    _dc: DcHandler = field(init=False)

    def __attrs_post_init__(self):
        self._vsphere_client = VSphereSDKHandler.from_config(
            resource_config=self._resource_conf,
            reservation_info=self._reservation_info,
            si=self._si,
        )
        self._dc = DcHandler.get_dc(self._resource_conf.default_datacenter, self._si)

    def delete(self) -> None:
        tags = set()
        folder = None
        try:
            vm_tags, folder = self._delete_vm()
            tags |= vm_tags
        finally:
            try:
                tags |= self._delete_folder(folder)
            finally:
                self._delete_tags(tags)

    def _delete_vm(self) -> tuple[set[str], FolderHandler | None]:
        vm_uuid = self._deployed_app.vmdetails.uid
        tags = set()
        folder = None
        try:
            vm = self._dc.get_vm_by_uuid(vm_uuid)
        except VmNotFound:
            logger.warning(f"Trying to remove vm {vm_uuid} but it is not exists")
        else:
            try:
                folder = vm.parent
            finally:
                try:
                    self._si.delete_customization_spec(vm.name)
                finally:
                    try:
                        tags |= self._get_tags(vm)
                    finally:
                        vm.power_off(soft=False)
                        vm.delete()
        return tags, folder

    def _delete_folder(self, folder: FolderHandler | None) -> set[str]:
        tags = set()
        if folder is not None:
            with folder_delete_lock:
                if folder.is_exists():
                    try:
                        tags |= self._get_tags(folder)
                    finally:
                        with suppress(FolderIsNotEmpty):
                            folder.destroy()
        return tags

    def _get_tags(self, obj) -> set[str]:
        tags = set()
        if self._vsphere_client:
            tags |= set(self._vsphere_client.get_attached_tags(obj))
        return tags

    def _delete_tags(self, tags: set[str]) -> None:
        if self._vsphere_client:
            self._vsphere_client.delete_unused_tags(tags)
