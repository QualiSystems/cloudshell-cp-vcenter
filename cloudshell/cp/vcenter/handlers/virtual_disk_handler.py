import re
from functools import cached_property

from cloudshell.cp.vcenter.handlers.virtual_device_handler import VirtualDevice


class VirtualDisk(VirtualDevice):
    @cached_property
    def index(self) -> int:
        """Return the index of the disk on the VM."""
        return int(re.search(r"\d+$", self.name).group())

    @property
    def capacity_in_bytes(self) -> int:
        return self._vc_obj.capacityInBytes

    @property
    def has_parent(self) -> bool:
        return bool(self._vc_obj.backing.parent)
