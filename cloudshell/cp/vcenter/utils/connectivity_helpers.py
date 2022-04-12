from __future__ import annotations

import re
import time
from logging import Logger

from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ConnectivityActionModel,
)

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler
from cloudshell.cp.vcenter.handlers.vnic_handler import VnicHandler
from cloudshell.cp.vcenter.models.connectivity_action_model import (
    VcenterConnectivityActionModel,
)

MAX_DVSWITCH_LENGTH = 60
QS_NAME_PREFIX = "QS"
PORT_GROUP_NAME_PATTERN = re.compile(rf"{QS_NAME_PREFIX}_.+_VLAN")


def generate_port_group_name(dv_switch_name: str, vlan_id: str, port_mode: str):
    dvs_name = dv_switch_name[:MAX_DVSWITCH_LENGTH]
    return f"{QS_NAME_PREFIX}_{dvs_name}_VLAN_{vlan_id}_{port_mode}"


def is_network_generated_name(net_name: str):
    return bool(PORT_GROUP_NAME_PATTERN.search(net_name))


def get_available_vnic(
    vm: VmHandler,
    default_net_name: str,
    reserved_networks: list[str],
    logger: Logger,
    vnic_name=None,
) -> VnicHandler:
    for vnic in vm.vnics:
        if vnic_name and vnic_name != vnic.label:
            continue

        network = vm.get_network_from_vnic(vnic)
        if (
            not network.name
            or network.name == default_net_name
            or (
                not is_network_generated_name(network.name)
                and network.name not in reserved_networks
            )
        ):
            break
    else:
        if len(vm.vnics) >= 10:
            raise BaseVCenterException("Limit of vNICs per VM is 10")
        vnic = vm.create_vnic(logger)
    return vnic


def get_existed_port_group_name(
    action: ConnectivityActionModel | VcenterConnectivityActionModel,
) -> str | None:
    # From vCenter Shell 4.2.1 and 5.0.1 we support "vCenter VLAN Port Group"
    # service that allows to connect to the existed Port Group. Before that we would
    # receive ConnectivityActionModel that know nothing about port_group_name
    pg_name = getattr(
        action.connection_params.vlan_service_attrs, "port_group_name", None
    )
    return pg_name


def should_remove_port_group(
    name: str, action: ConnectivityActionModel | VcenterConnectivityActionModel
) -> bool:
    return not bool(get_existed_port_group_name(action)) or is_network_generated_name(
        name
    )


def wait_network_become_free(
    dc: DcHandler, name: str, delay: int = 5, timeout: int = 60
) -> bool:
    start = time.time()
    while time.time() < start + timeout:
        if not dc.get_network(name).in_use:
            return True
        time.sleep(delay)
    else:
        return False
