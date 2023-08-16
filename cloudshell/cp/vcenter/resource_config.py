from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from attr import Attribute
from attrs import define

from cloudshell.api.cloudshell_api import CloudShellAPISession, ResourceInfo
from cloudshell.shell.standards.core.namespace_type import NameSpaceType
from cloudshell.shell.standards.core.resource_conf import BaseConfig, attr
from cloudshell.shell.standards.core.resource_conf.attrs_getter import (
    MODEL,
    AbsAttrsGetter,
)
from cloudshell.shell.standards.core.resource_conf.base_conf import password_decryptor
from cloudshell.shell.standards.core.resource_conf.resource_attr import AttrMeta

from cloudshell.cp.vcenter.constants import STATIC_SHELL_NAME


class ShutdownMethod(Enum):
    SOFT = "soft"
    HARD = "hard"


class VCenterAttributeNames:
    user = "User"
    password = "Password"
    default_datacenter = "Default Datacenter"
    default_dv_switch = "Default dvSwitch"
    holding_network = "Holding Network"
    vm_cluster = "VM Cluster"
    vm_resource_pool = "VM Resource Pool"
    vm_storage = "VM Storage"
    saved_sandbox_storage = "Saved Sandbox Storage"
    behavior_during_save = "Behavior during save"
    vm_location = "VM Location"
    shutdown_method = "Shutdown Method"
    ovf_tool_path = "OVF Tool Path"
    reserved_networks = "Reserved Networks"
    execution_server_selector = "Execution Server Selector"
    promiscuous_mode = "Promiscuous Mode"
    forged_transmits = "Forged Transmits"
    mac_changes = "MAC Address Changes"
    enable_tags = "Enable Tags"


@define(slots=False, str=False)
class VCenterResourceConfig(BaseConfig):
    ATTR_NAMES = VCenterAttributeNames

    user: str = attr(ATTR_NAMES.user)
    password: str = attr(ATTR_NAMES.password, is_password=True)
    default_datacenter: str = attr(ATTR_NAMES.default_datacenter)
    default_dv_switch: str = attr(ATTR_NAMES.default_dv_switch)
    holding_network: str = attr(ATTR_NAMES.holding_network)
    vm_cluster: str = attr(ATTR_NAMES.vm_cluster)
    vm_resource_pool: str = attr(ATTR_NAMES.vm_resource_pool)
    vm_storage: str = attr(ATTR_NAMES.vm_storage)
    saved_sandbox_storage: str = attr(ATTR_NAMES.saved_sandbox_storage)
    # todo enum?
    behavior_during_save: str = attr(ATTR_NAMES.behavior_during_save)
    vm_location: str = attr(ATTR_NAMES.vm_location)
    shutdown_method: ShutdownMethod = attr(ATTR_NAMES.shutdown_method)
    ovf_tool_path: str = attr(ATTR_NAMES.ovf_tool_path)
    reserved_networks: list[str] = attr(ATTR_NAMES.reserved_networks)
    promiscuous_mode: bool = attr(ATTR_NAMES.promiscuous_mode)
    forged_transmits: bool = attr(ATTR_NAMES.forged_transmits)
    mac_changes: bool = attr(ATTR_NAMES.mac_changes)
    enable_tags: bool = attr(ATTR_NAMES.enable_tags)

    @classmethod
    def from_cs_resource_details(
        cls,
        details: ResourceInfo,
        api: CloudShellAPISession,
    ) -> VCenterResourceConfig:
        attrs = ResourceInfoAttrGetter(
            cls, password_decryptor(api), details
        ).get_attrs()
        converter = cls._CONVERTER(cls, attrs)
        return cls(
            name=details.Name,
            shell_name=details.ResourceModelName,
            family_name=details.ResourceFamilyName,
            address=details.Address,
            api=api,
            **converter.convert(),
        )

    @property
    def is_static(self) -> bool:
        return STATIC_SHELL_NAME == self.shell_name


class ResourceInfoAttrGetter(AbsAttrsGetter):
    def __init__(
        self,
        model_cls: type[MODEL],
        decrypt_password: Callable[[str], str],
        details: ResourceInfo,
    ):
        super().__init__(model_cls, decrypt_password)
        self.details = details
        self._attrs = {a.Name: a.Value for a in details.ResourceAttributes}
        self.shell_name = details.ResourceModelName
        self.family_name = details.ResourceFamilyName

    def _extract_attr_val(self, f: Attribute, meta: AttrMeta) -> str:
        key = self._get_key(meta)
        return self._attrs[key]

    def _get_key(self, meta: AttrMeta) -> str:
        namespace = self._get_namespace(meta.namespace_type)
        return f"{namespace}.{meta.name}"

    def _get_namespace(self, namespace_type: NameSpaceType) -> str:
        if namespace_type is NameSpaceType.SHELL_NAME:
            namespace = self.shell_name
        elif namespace_type is NameSpaceType.FAMILY_NAME:
            namespace = self.family_name
        else:
            raise ValueError(f"Unknown namespace: {namespace_type}")
        return namespace
