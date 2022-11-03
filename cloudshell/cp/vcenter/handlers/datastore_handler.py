import attr

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler
from cloudshell.cp.vcenter.utils.units_converter import UsageInfo, format_bytes


class DatastoreNotFound(BaseVCenterException):
    def __init__(self, entity: ManagedEntityHandler, name: str):
        self.entity = entity
        self.name = name
        super().__init__(f"Datastore with name {name} not found in {entity}")


@attr.s(auto_attribs=True)
class DatastoreHandler(ManagedEntityHandler):
    def __str__(self) -> str:
        return f"Datastore '{self.name}'"

    @property
    def free_space(self):
        return self._entity.summary.freeSpace

    @property
    def usage_info(self) -> UsageInfo:
        capacity = self._entity.summary.capacity
        used = capacity - self.free_space
        return UsageInfo(
            capacity=format_bytes(capacity),
            used=format_bytes(capacity - self.free_space),
            free=format_bytes(used),
            used_percentage=str(round(used / capacity * 100)),
        )
