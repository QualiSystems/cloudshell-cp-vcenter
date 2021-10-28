from __future__ import annotations

from typing import TYPE_CHECKING

from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import VMNotFoundException

if TYPE_CHECKING:
    from logging import Logger

    from cloudshell.cp.vcenter.api_client import VCenterAPIClient
    from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


class VMActions:
    def __init__(
        self,
        vcenter_client: VCenterAPIClient,
        resource_conf: VCenterResourceConfig,
        logger: Logger,
    ):
        self._vcenter_client = vcenter_client
        self._resource_conf = resource_conf
        self._logger = logger

    def get_vm_disk_size(self, vm):
        self._logger.info(f"Getting VM Disk size for the VM {vm} ...")
        return sum(
            device.capacityInBytes
            for device in vm.config.hardware.device
            if isinstance(device, vim.vm.device.VirtualDisk)
        )

    def get_vm(self, uuid):
        self._logger.info(f"Getting VM by its UID {uuid} ...")
        dc = self._vcenter_client.get_dc(self._resource_conf.default_datacenter)
        vm = self._vcenter_client.get_vm(uuid=uuid, dc=dc)

        if vm is None:
            raise VMNotFoundException(f"Unable to find VM with uuid: {uuid}")

        return vm
