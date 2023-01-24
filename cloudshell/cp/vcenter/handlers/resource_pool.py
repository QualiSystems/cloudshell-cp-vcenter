from __future__ import annotations

from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler


class ResourcePoolNotFound(BaseVCenterException):
    def __init__(self, entity: ManagedEntityHandler, name: str):
        self.name = name
        self.entity = entity
        super().__init__(f"Resource Pool with name {name} not found in the {entity}")


class ResourcePoolHandler(ManagedEntityHandler):
    _vc_obj: vim.ResourcePool

    @property
    def resource_pools(self) -> list[ResourcePoolHandler]:
        return [ResourcePoolHandler(rp, self.si) for rp in self._vc_obj.resourcePool]

    @property
    def _class_name(self) -> str:
        return "Resource Pool"

    def get_resource_pool(self, name: str) -> ResourcePoolHandler:
        for rp in self.resource_pools:
            if rp.name == name:
                break
        else:
            raise ResourcePoolNotFound(self, name)
        return rp
