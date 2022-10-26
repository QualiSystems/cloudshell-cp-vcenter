import re

from cloudshell.cp.vcenter.handlers.virtual_device_handler import VirtualDeviceHandler


class VirtualDiskHandler(VirtualDeviceHandler):
    def __repr__(self) -> str:
        return f"Virtual Disk '{self.label}'"

    __str__ = __repr__

    @property
    def capacity_in_bytes(self) -> int:
        return self._device.capacityInBytes

    @property
    def has_parent(self) -> bool:
        return bool(self._device.backing.parent)

    @property
    def number(self) -> int:
        return int(re.search(r"\d+", self.label).group())
