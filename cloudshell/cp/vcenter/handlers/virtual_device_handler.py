from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from attrs import define
from pyVmomi import vim

if TYPE_CHECKING:
    from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler


def is_vnic(device) -> bool:
    return isinstance(device, vim.vm.device.VirtualEthernetCard)


def is_virtual_disk(device) -> bool:
    return isinstance(device, vim.vm.device.VirtualDisk)


@define(repr=False)
class VirtualDevice:
    vm: ClassVar[VmHandler]
    _vc_obj: vim.vm.device.VirtualDevice

    def __repr__(self) -> str:
        try:
            name = self.name
        except AttributeError:
            # new object without name
            name = f"New {type(self).__name__}"

        return f"{name} of the {self.vm}"

    @property
    def name(self) -> str:
        return self._vc_obj.deviceInfo.label

    def get_vc_obj(self) -> vim.vm.device.VirtualDevice:
        return self._vc_obj
