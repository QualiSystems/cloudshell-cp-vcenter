from __future__ import annotations

import re

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler
from cloudshell.cp.vcenter.handlers.vnic_handler import VnicHandler

MAX_DVSWITCH_LENGTH = 60
QS_NAME_PREFIX = "QS"
PORT_GROUP_NAME_PATTERN = re.compile(rf"{QS_NAME_PREFIX}_.+_VLAN")


def generate_port_group_name(dv_switch_name: str, vlan_id: str, port_mode: str):
    dvs_name = dv_switch_name[:MAX_DVSWITCH_LENGTH]
    return f"{QS_NAME_PREFIX}_{dvs_name}_VLAN_{vlan_id}_{port_mode}"


def is_network_generated_name(net_name: str):
    return bool(PORT_GROUP_NAME_PATTERN.search(net_name))


def get_available_vnic(
    vm: VmHandler, default_net_name: str, reserved_networks: list[str], vnic_name=None
) -> VnicHandler:
    for vnic in vm.vnics:
        if vnic_name and vnic_name != vnic.label:
            continue

        net_name = vm.get_network_name_from_vnic(vnic)
        if (
            not net_name
            or net_name == default_net_name
            or (
                not is_network_generated_name(net_name)
                and net_name not in reserved_networks
            )
        ):
            break
    else:
        raise BaseVCenterException("No vNIC available")
    return vnic
