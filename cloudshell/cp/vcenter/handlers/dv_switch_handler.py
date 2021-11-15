from __future__ import annotations

from logging import Logger

import attr
from pyVmomi import vim

from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ConnectionModeEnum,
)

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler
from cloudshell.cp.vcenter.handlers.network_handler import (
    DVPortGroupHandler,
    DVPortGroupNotFound,
)
from cloudshell.cp.vcenter.utils.task_waiter import VcenterTaskWaiter


class DvSwitchNotFound(BaseVCenterException):
    def __init__(self, entity: ManagedEntityHandler, name: str):
        self.entity = entity
        self.name = name
        msg = f"DistributedVirtualSwitch with name {name} not found int {entity}"
        super().__init__(msg)


def get_vlan_spec(port_mode: ConnectionModeEnum, vlan_range: str):
    if port_mode is port_mode.ACCESS:
        spec = vim.dvs.VmwareDistributedVirtualSwitch.VlanIdSpec
        vlan_id = int(vlan_range)
    else:
        spec = vim.dvs.VmwareDistributedVirtualSwitch.TrunkVlanSpec
        parts = list(map(int, vlan_range.split("-")))
        if len(parts) == 1:
            start = end = next(parts)
        else:
            start, end = parts
        vlan_id = [vim.NumericRange(start=start, end=end)]
    return spec(vlanId=vlan_id, inherited=False)


@attr.s(auto_attribs=True)
class DvSwitchHandler(ManagedEntityHandler):
    def __str__(self) -> str:
        return f"DistributedVirtualSwitch '{self.name}'"

    def create_dv_port_group(
        self,
        dv_port_name: str,
        vlan_range: str,
        port_mode: ConnectionModeEnum,
        promiscuous_mode: bool,
        logger: Logger,
        num_ports: int = 32,
        task_waiter: VcenterTaskWaiter | None = None,
    ) -> None:
        port_conf_policy = (
            vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy(
                securityPolicy=vim.dvs.VmwareDistributedVirtualSwitch.SecurityPolicy(
                    allowPromiscuous=vim.BoolPolicy(value=promiscuous_mode),
                    forgedTransmits=vim.BoolPolicy(value=True),
                    macChanges=vim.BoolPolicy(value=False),
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

        task = self._entity.AddDVPortgroup_Task([dv_pg_spec])
        logger.info(f"DV Port Group '{dv_port_name}' CREATE Task")
        task_waiter = task_waiter or VcenterTaskWaiter(logger)
        task_waiter.wait_for_task(task)

    def get_dv_port_group(self, name: str) -> DVPortGroupHandler:
        for port_group in self._entity.portgroup:
            if port_group.name == name:
                return DVPortGroupHandler(port_group, self._si)
        raise DVPortGroupNotFound(name, self)
