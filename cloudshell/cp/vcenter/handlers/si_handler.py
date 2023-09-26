from __future__ import annotations

import logging
from contextlib import suppress
from functools import partial
from threading import Lock
from typing import TYPE_CHECKING, Any

from attrs import define
from pyVim.connect import Disconnect
from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.custom_spec_handler import (
    CustomSpecHandler,
    get_custom_spec_from_vim_spec,
)
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig
from cloudshell.cp.vcenter.utils.client_helpers import get_si

if TYPE_CHECKING:
    from typing_extensions import Self

logger = logging.getLogger(__name__)
si_lock = Lock()
si_connections = {}


class CustomSpecNotFound(BaseVCenterException):
    def __init__(self, name: str):
        super().__init__(f"Customization spec with name {name} not found.")


class ResourceInUse(BaseVCenterException):
    def __init__(self, name):
        self.name = name
        super().__init__(f"{name} is in use")


@define
class SiHandler:
    _vc_obj: vim.ServiceInstance

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        Disconnect(self._vc_obj)
        # Disconnect makes session not valid but left opened socket ...
        # we have to destroy it
        self._vc_obj._stub.DropConnections()

    @classmethod
    def from_config(cls, conf: VCenterResourceConfig) -> SiHandler:
        return cls.connect(conf.address, conf.user, conf.password)

    @classmethod
    def connect(cls, host: str, user: str, password: str) -> SiHandler:
        logger.info("Initializing vCenter API client SI")
        si = get_si(host, user, password)
        return cls(si)

    @property
    def root_folder(self):
        return self._vc_obj.content.rootFolder

    @property
    def vc_version(self) -> str:
        return self._vc_obj.content.about.version

    @property
    def instance_uuid(self) -> str:
        return self._vc_obj.content.about.instanceUuid

    @property
    def vcenter_host(self) -> str:
        # noinspection PyUnresolvedReferences
        for item in self._vc_obj.content.setting.setting:
            if item.key == "VirtualCenter.FQDN":
                return item.value
        raise Exception("Unable to find vCenter host")

    def get_vc_obj(self) -> vim.ServiceInstance:
        return self._vc_obj

    def acquire_session_ticket(self) -> str:
        return self._vc_obj.content.sessionManager.AcquireCloneTicket()

    def find_items(self, vim_type, recursive=False, container=None) -> Any:
        container = container or self.root_folder
        if not isinstance(vim_type, list):
            vim_type = [vim_type]
        view = self._vc_obj.content.viewManager.CreateContainerView(
            container, vim_type, recursive
        )
        # noinspection PyUnresolvedReferences
        items = view.view
        # noinspection PyUnresolvedReferences
        view.DestroyView()
        return items

    def find_by_uuid(self, dc, uuid: str, vm_search: bool) -> Any:
        find_by_uuid = partial(self._vc_obj.content.searchIndex.FindByUuid, dc, uuid)
        if vm_search:
            # vmSearch=True, instanceUuid=True
            # if we cannot find by vCenter UUID use fallback - find by BIOS UUID
            entity = find_by_uuid(True, True) or find_by_uuid(True)
        else:
            entity = find_by_uuid()
        return entity

    def find_child(self, parent, name: str) -> Any:
        return self._vc_obj.content.searchIndex.FindChild(parent, name)

    def get_customization_spec(self, name: str) -> CustomSpecHandler | None:
        try:
            spec = self._vc_obj.content.customizationSpecManager.GetCustomizationSpec(
                name
            )
        except vim.fault.NotFound:
            raise CustomSpecNotFound(name)

        custom_spec_handler = get_custom_spec_from_vim_spec(spec)
        return custom_spec_handler

    def duplicate_customization_spec(self, original_name: str, new_name: str):
        try:
            self._vc_obj.content.customizationSpecManager.DuplicateCustomizationSpec(
                name=original_name, newName=new_name
            )
        except vim.fault.NotFound:
            raise CustomSpecNotFound(original_name)

    def overwrite_customization_spec(self, spec: CustomSpecHandler):
        self._vc_obj.content.customizationSpecManager.OverwriteCustomizationSpec(
            spec.spec
        )

    def create_customization_spec(self, spec: CustomSpecHandler):
        self._vc_obj.content.customizationSpecManager.CreateCustomizationSpec(spec.spec)

    def delete_customization_spec(self, name: str):
        with suppress(vim.fault.NotFound):
            self._vc_obj.content.customizationSpecManager.DeleteCustomizationSpec(
                name=name
            )

    def query_event(self, filter_spec: vim.event.EventFilterSpec):
        # noinspection PyUnresolvedReferences
        return self._vc_obj.content.eventManager.QueryEvent(filter_spec)
