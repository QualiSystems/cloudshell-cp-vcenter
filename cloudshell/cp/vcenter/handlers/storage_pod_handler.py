from __future__ import annotations

import attr
from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.datastore_handler import (
    DatastoreHandler,
    DatastoreNotFound,
)
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler


class StoragePodNotFound(BaseVCenterException):
    def __init__(self, entity: ManagedEntityHandler, name: str):
        self.entity = entity
        self.name = name
        super().__init__(f"Storage Pod with name '{name}' not found in {entity}")


@attr.s(auto_attribs=True)
class StoragePodHandler(ManagedEntityHandler):
    @property
    def datastores(self) -> list[DatastoreHandler]:
        return [
            DatastoreHandler(store, self.si) for store in self.find_items(vim.Datastore)
        ]

    @property
    def _class_name(self) -> str:
        return "Storage Pod"

    def get_datastore_by_name(self, name: str) -> DatastoreHandler:
        for datastore in self.datastores:
            if datastore.name == name:
                return datastore
        raise DatastoreNotFound(self, name)

    def get_datastore_with_max_free_space(self) -> DatastoreHandler:
        return max(self.datastores, key=lambda d: d.free_space)
