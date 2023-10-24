from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import Mock


class VmMock(Mock):
    def __init__(self, *args, **kwargs):
        name = kwargs["name"]
        super().__init__(*args, **kwargs)
        self.name = name


class SiMock(Mock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.t_vms = {}
        self._t_preparing = False

    @contextmanager
    def t_preparing(self):
        try:
            self._t_preparing = True
            yield
            self.t_prepare()
        finally:
            self._t_preparing = False

    def t_prepare(self):
        def t_find_by_uuid(container, uuid, vmSearch=False, instanceUuid=False):
            return self.t_vms[uuid]

        self.content.searchIndex.FindByUuid.side_effect = t_find_by_uuid

    def t_add_vm(self, vm: VmMock):
        assert self._t_preparing
        self.t_vms[vm.uuid] = vm
