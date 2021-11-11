from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler


class NetworkNotFound(BaseVCenterException):
    def __init__(self, net_name: str, entity: ManagedEntityHandler):
        self.net_name = net_name
        self.entity = entity
        super().__init__(f"Network {net_name} not found in {entity}")


class NetworkHandler(ManagedEntityHandler):
    def __str__(self):
        return f"Network '{self.name}'"
