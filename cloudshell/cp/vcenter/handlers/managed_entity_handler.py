from __future__ import annotations

from abc import abstractmethod
from logging import Logger
from typing import TYPE_CHECKING, Generic, TypeVar

from attrs import define
from pyVmomi import vim, vmodl

from cloudshell.cp.vcenter.handlers.si_handler import SiHandler

if TYPE_CHECKING:
    from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler

ManagedEntityNotFound = vmodl.fault.ManagedObjectNotFound


VC_TYPE = TypeVar("VC_TYPE", bound=vim.ManagedEntity)


@define(repr=False)
class ManagedEntityHandler(Generic[VC_TYPE]):
    _vc_obj: VC_TYPE
    si: SiHandler

    def __repr__(self) -> str:
        return f"{self._class_name} '{self.name}'"

    @property
    def logger(self) -> Logger:
        return self.si.logger

    @property
    def name(self) -> str:
        return self._vc_obj.name

    @property
    def dc(self) -> DcHandler:
        from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler

        parent = self._vc_obj.parent
        while not isinstance(parent, vim.Datacenter):
            parent = parent.parent
        return DcHandler(parent, self.si)

    @property
    @abstractmethod
    def _class_name(self) -> str:
        return "Managed Entity"

    def get_vc_obj(self) -> VC_TYPE:
        return self._vc_obj

    def find_child(self, name: str):
        return self.si.find_child(self._vc_obj, name)

    def find_items(self, vim_type, recursive: bool = False):
        return self.si.find_items(vim_type, recursive, container=self._vc_obj)
