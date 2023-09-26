from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from attrs import define, field, setters
from pyVmomi import vim

from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ConnectionModeEnum,
)

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler
from cloudshell.cp.vcenter.handlers.network_handler import PortGroupNotFound
from cloudshell.cp.vcenter.handlers.task import ON_TASK_PROGRESS_TYPE, Task

if TYPE_CHECKING:
    from cloudshell.cp.vcenter.handlers.cluster_handler import HostHandler


logger = logging.getLogger(__name__)


class DvSwitchNotFound(BaseVCenterException):
    def __init__(self, entity: ManagedEntityHandler, name: str):
        self.entity = entity
        self.name = name
        msg = f"DistributedVirtualSwitch with name {name} not found in the {entity}"
        super().__init__(msg)


class VSwitchNotFound(BaseVCenterException):
    def __init__(self, entity: ManagedEntityHandler, name: str):
        self.entity = entity
        self.name = name
        super().__init__(f"VirtualSwitch with name {name} not found in the {entity}")


class PortGroupExists(BaseVCenterException):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"PortGroup with name {name} already exists")


def get_vlan_spec(port_mode: ConnectionModeEnum, vlan_range: str):
    if port_mode is port_mode.ACCESS:
        spec = vim.dvs.VmwareDistributedVirtualSwitch.VlanIdSpec
        vlan_id = int(vlan_range)
    else:
        spec = vim.dvs.VmwareDistributedVirtualSwitch.TrunkVlanSpec
        parts = sorted(map(int, vlan_range.split("-")))
        if len(parts) == 1:
            start = end = parts[0]
        else:
            start, end = parts
        vlan_id = [vim.NumericRange(start=start, end=end)]
    return spec(vlanId=vlan_id, inherited=False)


class AbstractSwitchHandler(Protocol):
    @property
    def name(self) -> str:
        raise NotImplementedError

    def create_port_group(
        self,
        port_name: str,
        vlan_range: str,
        port_mode: ConnectionModeEnum,
        promiscuous_mode: bool,
        forged_transmits: bool,
        mac_changes: bool,
        num_ports: int = 32,
        on_task_progress: ON_TASK_PROGRESS_TYPE | None = None,
    ) -> None:
        raise NotImplementedError


class DvSwitchHandler(ManagedEntityHandler, AbstractSwitchHandler):
    @property
    def _class_name(self) -> str:
        return "Distributed Virtual Switch"

    def create_port_group(
        self,
        dv_port_name: str,
        vlan_range: str,
        port_mode: ConnectionModeEnum,
        promiscuous_mode: bool,
        forged_transmits: bool,
        mac_changes: bool,
        num_ports: int = 32,
        on_task_progress: ON_TASK_PROGRESS_TYPE | None = None,
    ) -> None:
        logger.debug(f"Creating dv port group {dv_port_name} on {self}")
        port_conf_policy = (
            vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy(
                securityPolicy=vim.dvs.VmwareDistributedVirtualSwitch.SecurityPolicy(
                    allowPromiscuous=vim.BoolPolicy(value=promiscuous_mode),
                    forgedTransmits=vim.BoolPolicy(value=forged_transmits),
                    macChanges=vim.BoolPolicy(value=mac_changes),
                    inherited=False,
                ),
                vlan=get_vlan_spec(port_mode, vlan_range),
            )
        )
        dv_pg_spec = vim.dvs.DistributedVirtualPortgroup.ConfigSpec(
            name=dv_port_name,
            numPorts=num_ports,
            type=vim.dvs.DistributedVirtualPortgroup.PortgroupType.earlyBinding,
            defaultPortConfig=port_conf_policy,
        )

        vc_task = self._vc_obj.AddDVPortgroup_Task([dv_pg_spec])
        logger.info(f"DV Port Group '{dv_port_name}' CREATE Task")
        task = Task(vc_task)
        task.wait(on_progress=on_task_progress)


@define(repr=False)
class VSwitchHandler(AbstractSwitchHandler):
    _vc_obj: vim.host.VirtualSwitch = field(on_setattr=setters.frozen)
    host: HostHandler

    def __repr__(self) -> str:
        return f"VirtualSwitch '{self.name}'"

    @property
    def key(self) -> str:
        return self._vc_obj.key

    @property
    def name(self) -> str:
        return self._vc_obj.name

    def create_port_group(
        self,
        port_name: str,
        vlan_range: str,
        port_mode: ConnectionModeEnum,
        promiscuous_mode: bool,
        forged_transmits: bool,
        mac_changes: bool,
        num_ports: int = 32,
        on_task_progress: ON_TASK_PROGRESS_TYPE | None = None,
    ) -> None:
        logger.debug(f"Creating port group {port_name} on {self}")
        pg_spec = vim.host.PortGroup.Specification()
        pg_spec.vswitchName = self.name
        pg_spec.name = port_name
        pg_spec.vlanId = int(vlan_range)
        network_policy = vim.host.NetworkPolicy()
        network_policy.security = vim.host.NetworkPolicy.SecurityPolicy()
        network_policy.security.allowPromiscuous = promiscuous_mode
        network_policy.security.macChanges = mac_changes
        network_policy.security.forgedTransmits = forged_transmits
        pg_spec.policy = network_policy

        self.host.add_port_group(pg_spec)

    def port_group_exists(self, name: str) -> bool:
        try:
            self.host.get_port_group(name)
        except PortGroupNotFound:
            result = False
        else:
            result = True
        return result
