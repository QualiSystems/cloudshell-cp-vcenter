from __future__ import annotations

from collections.abc import Generator
from typing import ClassVar

import attr
from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException


class SnapshotNotFoundInSnapshotTree(BaseVCenterException):
    def __init__(self):
        super().__init__("Snapshot not found in snapshot tree")


class SnapshotPathEmpty(BaseVCenterException):
    ...


def _yield_snapshot_handlers(
    snapshot_list, path: SnapshotPath | None = None
) -> Generator[SnapshotHandler, None, None]:
    if not path:
        path = SnapshotPath()

    for snapshot_tree in snapshot_list:
        new_path = path + snapshot_tree.name
        yield SnapshotHandler(snapshot_tree.snapshot, new_path)
        yield from _yield_snapshot_handlers(snapshot_tree.childSnapshotList, new_path)


def _get_snapshot_path(
    snapshot_list, snapshot, path: SnapshotPath | None = None
) -> SnapshotPath | None:
    if not path:
        path = SnapshotPath()

    for snapshot_tree in snapshot_list:
        new_path = path + snapshot_tree.name
        if snapshot_tree.snapshot == snapshot:
            return new_path

        new_path = _get_snapshot_path(
            snapshot_tree.childSnapshotList, snapshot, new_path
        )
        if new_path:
            return new_path
        else:
            continue

    return None


def _get_snapshot_by_path(snapshot_list, path: SnapshotPath):
    if not path:
        return None

    new_path = path.copy()
    root_name = new_path.pop_head()
    for snapshot_tree in snapshot_list:
        if snapshot_tree.name == root_name:
            if new_path:
                return _get_snapshot_path(snapshot_tree.childSnapshotList, new_path)
            else:
                return snapshot_tree.snapshot
    return None


@attr.s(auto_attribs=True)
class SnapshotPath:
    SEPARATOR: ClassVar[str] = "/"
    _path: str = ""

    def __str__(self) -> str:
        return self._path

    def __bool__(self) -> bool:
        return bool(self._path)

    def __add__(self, other: SnapshotPath | str) -> SnapshotPath:
        if not isinstance(other, (SnapshotPath, str)):
            raise NotImplementedError
        path = SnapshotPath(self._path)
        path.append(other)
        return path

    @property
    def name(self) -> str:
        return self._path.rsplit(self.SEPARATOR, 1)[-1]

    def copy(self) -> SnapshotPath:
        return SnapshotPath(self._path)

    def append(self, path: str | SnapshotPath):
        path = f"{self._path}{self.SEPARATOR}{str(path)}"
        self._path = path.strip(self.SEPARATOR)

    def pop_head(self) -> str:
        if not self._path:
            raise SnapshotPathEmpty

        parts = self._path.split(self.SEPARATOR, 1)
        head = parts[0]
        try:
            path = parts[1]
        except IndexError:
            path = ""
        self._path = path
        return head


@attr.s(auto_attribs=True)
class SnapshotHandler:
    _snapshot: vim.vm.Snapshot
    _path: SnapshotPath | None = None

    @classmethod
    def get_vm_snapshot_by_path(cls, vm, path: SnapshotPath) -> SnapshotHandler:
        for snapshot_handler in cls.yield_vm_snapshots(vm):
            if snapshot_handler.path == path:
                return snapshot_handler
        raise SnapshotNotFoundInSnapshotTree

    @classmethod
    def yield_vm_snapshots(cls, vm) -> Generator[SnapshotHandler, None, None]:
        yield from _yield_snapshot_handlers(vm.snapshot.rootSnapshotList)

    @property
    def _root_snapshot_list(self):
        return self._snapshot.vm.snapshot.rootSnapshotList

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def path(self) -> SnapshotPath:
        if self._path is None:
            path = _get_snapshot_path(self._root_snapshot_list, self._snapshot)
            if not path:
                raise SnapshotNotFoundInSnapshotTree  # it shouldn't happen
            self._path = path
        return self._path

    def revert_to_snapshot_task(self):
        return self._snapshot.RevertToSnapshot_Task()
