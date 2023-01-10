from __future__ import annotations

from contextlib import suppress
from logging import Logger
from threading import Lock
from typing import ClassVar

import attr
from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException, TaskFaultException
from cloudshell.cp.vcenter.handlers.managed_entity_handler import (
    ManagedEntityHandler,
    ManagedEntityNotFound,
)
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.vcenter_path import VcenterPath
from cloudshell.cp.vcenter.utils.task_waiter import VcenterTaskWaiter


class FolderNotFound(BaseVCenterException):
    def __init__(self, vc_entity, name: str):
        self.vc_entity = vc_entity
        self.name = name
        msg = f"Folder with name {name} not found in the entity {vc_entity.name}"
        super().__init__(msg)


class FolderIsNotEmpty(BaseVCenterException):
    def __init__(self, folder: FolderHandler):
        self.folder = folder
        super().__init__(f"{folder} is not empty, cannot delete it")


@attr.s(auto_attribs=True)
class FolderHandler(ManagedEntityHandler):
    FOLDER_LOCK: ClassVar[Lock] = Lock()

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
                if not vc_folder:
                    raise FolderNotFound(parent, str(path))
        except AttributeError:
            raise FolderNotFound(parent, str(path))

        return cls(vc_folder, si)

    def __str__(self) -> str:
        return f"Folder '{self.name}'"

    @property
    def _moId(self) -> str:
        # avoid using this property
        return self._entity._moId

    @property
    def _wsdl_name(self) -> str:
        return self._entity._wsdlName

    def is_empty(self) -> bool:
        return not bool(self._entity.childEntity)

    def get_folder(self, path: str | VcenterPath) -> FolderHandler:
        return self.get_folder_from_parent(self._entity, path, self._si)

    def create_folder(self, name: str) -> FolderHandler:
        vc_folder = self._entity.CreateFolder(name)
        return FolderHandler(vc_folder, self._si)

    def get_or_create_folder(self, path: str | VcenterPath) -> FolderHandler:
        if not isinstance(path, VcenterPath):
            path = VcenterPath(path)
        folder = self

        for name in path:
            folder = folder.get_or_create_child(name)
        return folder

    def destroy(self, logger: Logger, task_waiter: VcenterTaskWaiter | None = None):
        logger.info(f"Deleting the {self}")
        with suppress(ManagedEntityNotFound):
            if not self.is_empty():
                raise FolderIsNotEmpty(self)

            task = self._entity.Destroy_Task()
            task_waiter = task_waiter or VcenterTaskWaiter(logger)
            try:
                task_waiter.wait_for_task(task)
            except TaskFaultException as e:
                if "has already been deleted" not in str(e):
                    raise

    def get_or_create_child(self, name: str) -> FolderHandler:
        """Creates a new folder with a lock.

        If we try to create a folder that already exists vCenter will show
        an unpleasant message in 'Recent Tasks' on the Web Portal 🤷
        """
        with self.FOLDER_LOCK:
            try:
                folder = self.get_folder(name)
            except FolderNotFound:
                # Try Except wrapper for cases
                # when we have several simultaneous request,
                # and one of them fails with duplicate error
                try:
                    folder = self.create_folder(name)
                except vim.fault.DuplicateName:
                    folder = self.get_folder(name)
        return folder
