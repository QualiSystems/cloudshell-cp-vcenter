from __future__ import annotations

from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler


class NetworkNotFound(BaseVCenterException):
    def __init__(self, net_name: str, entity: ManagedEntityHandler):
        self.net_name = net_name
        self.entity = entity
        super().__init__(f"Network {net_name} not found in {entity}")


class DVPortGroupNotFound(BaseVCenterException):
    def __init__(self, port_group_name: str, entity: ManagedEntityHandler):
        self.port_group_name = port_group_name
        self.entity = entity
        msg = f"Distributed Virtual Port Group {port_group_name} not found in {entity}"
        super().__init__(msg)


class NetworkHandler(ManagedEntityHandler):
    _entity: vim.Network

    def __str__(self) -> str:
        return f"Network '{self.name}'"

    @property
    def key(self) -> str:
        return self._entity.key

    @property
    def vlan_id(self) -> str | None:
        try:
            return self._entity.config.defaultPortConfig.vlan.vlanId
        except AttributeError:
            return None


# base class is Network?
class DVPortGroupHandler(ManagedEntityHandler):
    _entity: vim.dvs.vim.dvs.DistributedVirtualPortgroup

    def __str__(self) -> str:
        return f"Distributed Virtual Port group '{self.name}'"

    @property
    def key(self) -> str:
        return self._entity.key

    @property
    def switch_uuid(self) -> str:
        return self._entity.config.distributedVirtualSwitch.uuid

    @property
    def is_connected(self) -> bool:
        return bool(self._entity.vm)

    def destroy(self):
        self._entity.Destroy()
