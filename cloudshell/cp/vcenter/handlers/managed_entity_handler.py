from abc import abstractmethod

import attr
from pyVmomi import vim, vmodl

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler


class ManagedEntityNotFound(BaseVCenterException):
    ...


@attr.s(auto_attribs=True)
class ManagedEntityHandler:
    _entity: vim.ManagedEntity
    _si: SiHandler

    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError("Should return - Entity 'name'")

    def __getattribute__(self, item):
        """Raise the error if the resource has been removed."""
        try:
            result = super().__getattribute__(item)
        except vmodl.fault.ManagedObjectNotFound:
            raise ManagedEntityNotFound
        else:
            return result

    @property
    def name(self) -> str:
        return self._entity.name

    def find_child(self, name: str):
        return self._si.find_child(self._entity, name)

    def find_items(self, vim_type, recursive: bool = False):
        return self._si.find_items(vim_type, recursive, container=self._entity)
