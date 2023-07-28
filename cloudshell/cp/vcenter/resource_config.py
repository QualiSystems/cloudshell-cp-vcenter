from __future__ import annotations

from enum import Enum

from attrs import define

from cloudshell.api.cloudshell_api import ResourceInfo
from cloudshell.shell.standards.core.resource_conf import BaseConfig, attr

from cloudshell.cp.vcenter.constants import SHELL_NAME


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
        shell_name: str = SHELL_NAME,
        api=None,
        supported_os=None,
    ) -> VCenterResourceConfig:
        attrs = {attr.Name: attr.Value for attr in details.ResourceAttributes}
        # todo static vcenter
        return cls(
            shell_name=shell_name,
            name=details.Name,
            fullname=details.Name,
            address=details.Address,
            family_name=details.ResourceFamilyName,
            attributes=attrs,
            supported_os=supported_os,
            api=api,
            cs_resource_id=details.UniqeIdentifier,
        )
