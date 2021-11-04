from __future__ import annotations

from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.exceptions import (
    BaseVCenterException,
    ObjectNotFoundException,
)
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler
from cloudshell.cp.vcenter.handlers.network_handler import (
    NetworkHandler,
    NetworkNotFound,
)
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler


class VmNotFound(BaseVCenterException):
    def __init__(self, dc: DcHandler, uuid: str | None = None, name: str | None = None):
        self.uuid = uuid
        self.name = name

        if not uuid and not name:
            raise ValueError("You should specify uuid or name")
        if uuid:
            msg = f"VM with the uuid {uuid} in the DC {dc.name} not found"
        else:
            msg = f"VM with the name {name} in the DC {dc.name} not found"
        super().__init__(msg)


class DcHandler(ManagedEntityHandler):
    def __str__(self):
        return f"DC '{self.name}'"

    @property
    def networks(self) -> list[NetworkHandler]:
        return list(map(NetworkHandler, self._entity.network))

    def get_network(self, name: str) -> NetworkHandler:
        for network in self.networks:
            if network.name == name:
                return network
        raise NetworkNotFound(name, self)

    def get_vm_by_uuid(self, uuid: str, vcenter_client: VCenterAPIClient) -> VmHandler:
        vm = vcenter_client.get_vm(uuid, self._entity)
        if not vm:
            raise VmNotFound(self, uuid=uuid)
        return VmHandler(vm)

    def get_vm_by_name(self, name: str, vcenter_client: VCenterAPIClient) -> VmHandler:
        try:
            vm = vcenter_client.get_vm_by_name(name, self._entity)
        except ObjectNotFoundException:
            raise VmNotFound(self, name=name)
        return VmHandler(vm)
