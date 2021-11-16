from __future__ import annotations

from logging import Logger

import attr

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.vcenter_path import VcenterPath
from cloudshell.cp.vcenter.utils.task_waiter import VcenterTaskWaiter


class FolderNotFound(BaseVCenterException):
    def __init__(self, vc_entity, name: str):
        self.vc_entity = vc_entity
        self.name = name
        msg = f"Folder with name {name} not found in the entity {vc_entity.name}"
        super().__init__(msg)


@attr.s(auto_attribs=True)
class FolderHandler(ManagedEntityHandler):
    @classmethod
    def get_folder_from_parent(
        cls, parent, path: str | VcenterPath, si: SiHandler
    ) -> FolderHandler:
        if not isinstance(path, VcenterPath):
            path = VcenterPath(path)
        vc_folder = parent
        try:
            for name in path:
                vc_folder = si.find_child(vc_folder, name)
        except AttributeError:
            raise FolderNotFound(parent, str(path))
        if not vc_folder:
            raise FolderNotFound(parent, str(path))

        return cls(vc_folder, si)

    def __str__(self) -> str:
        return f"Folder '{self.name}'"

    def get_folder(self, path: str | VcenterPath) -> FolderHandler:
        return self.get_folder_from_parent(self._entity, path, self._si)

    def create_folder(self, name: str) -> FolderHandler:
        vc_folder = self._entity.CreateFolder(name)
        return FolderHandler(vc_folder, self._si)

    def get_or_create_folder(self, path: str | VcenterPath) -> FolderHandler:
        if not isinstance(path, VcenterPath):
            path = VcenterPath
        folder = self

        for name in path:
            try:
                folder = folder.get_folder(name)
            except FolderNotFound:
                folder = folder.create_folder(name)

        return folder

    def destroy(self, logger: Logger, task_waiter: VcenterTaskWaiter | None = None):
        task = self._entity.Destroy_Task()
        task_waiter = task_waiter or VcenterTaskWaiter(logger)
        task_waiter.wait_for_task(task)