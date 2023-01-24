from __future__ import annotations

import ipaddress
import re
from typing import TYPE_CHECKING

from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ConnectionModeEnum,
)

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.network_handler import (
    AbstractNetwork,
    DVPortGroupHandler,
    NetworkHandler,
)
from cloudshell.cp.vcenter.handlers.si_handler import CustomSpecNotFound
from cloudshell.cp.vcenter.models.connectivity_action_model import (
    VcenterConnectivityActionModel,
)
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig

if TYPE_CHECKING:
    from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler
    from cloudshell.cp.vcenter.handlers.vnic_handler import Vnic


MAX_DVSWITCH_LENGTH = 60
QS_NAME_PREFIX = "QS"
PORT_GROUP_NAME_PATTERN = re.compile(rf"{QS_NAME_PREFIX}_.+_VLAN")


def generate_port_group_name(
    dv_switch_name: str, vlan_id: str, port_mode: ConnectionModeEnum
) -> str:
    dvs_name = dv_switch_name[:MAX_DVSWITCH_LENGTH]
    return f"{QS_NAME_PREFIX}_{dvs_name}_VLAN_{vlan_id}_{port_mode.value}"


def is_network_generated_name(net_name: str):
    return bool(PORT_GROUP_NAME_PATTERN.search(net_name))


def is_correct_vnic(expected_vnic: str, vnic: Vnic) -> bool:
    """Check that expected vNIC name or number is equal to vNIC.

    :param expected_vnic: vNIC name or number from the connectivity request
    """
    if expected_vnic.isdigit():
        try:
            is_correct = vnic.index == int(expected_vnic)
        except ValueError:
            is_correct = False
    else:
        is_correct = expected_vnic.lower() == vnic.name.lower()
    return is_correct


def get_available_vnic(
    vm: VmHandler,
    default_network: AbstractNetwork,
    reserved_networks: list[str],
) -> Vnic | None:
    for vnic in vm.vnics:
        network = vnic.network
        if is_vnic_network_can_be_replaced(network, default_network, reserved_networks):
            break
    else:
        vnic = None
    return vnic


def create_new_vnic(
    vm: VmHandler, network: NetworkHandler | DVPortGroupHandler
) -> Vnic:
    if len(vm.vnics) >= 10:
        raise BaseVCenterException("Limit of vNICs per VM is 10")

    vnic = vm.vnic_class.create(network)

    try:
        custom_spec = vm.si.get_customization_spec(vm.name)
    except CustomSpecNotFound:
        pass
    else:
        # we need to have the same number of interfaces on the VM and in the
        # customization spec
        vm.si.logger.info(f"Adding a new vNIC to the customization spec for the {vm}")
        if custom_spec.number_of_vnics > 0:
            custom_spec.add_new_vnic()
            vm.si.overwrite_customization_spec(custom_spec)

    return vnic


def is_vnic_network_can_be_replaced(
    network: AbstractNetwork,
    default_network: AbstractNetwork,
    reserved_network_names: list[str],
) -> bool:
    return any(
        (
            not network.name,
            network.name == default_network,
            network.name not in reserved_network_names
            and not (is_network_generated_name(network.name)),
        )
    )


def get_existed_port_group_name(action: VcenterConnectivityActionModel) -> str | None:
    pg_name = (
        action.connection_params.vlan_service_attrs.virtual_network
        or action.connection_params.vlan_service_attrs.port_group_name  # deprecated
    )
    return pg_name


def should_remove_port_group(name: str, action: VcenterConnectivityActionModel) -> bool:
    """Check if we should remove the network.

    We don't remove the network if it was specified in action
    or doesn't create by the Shell
    """
    return not bool(get_existed_port_group_name(action)) and is_network_generated_name(
        name
    )


def is_ipv4(ip: str | None) -> bool:
    try:
        ipaddress.IPv4Address(ip)
    except ipaddress.AddressValueError:
        result = False
    else:
        result = True
    return result


def get_forged_transmits(
    action: VcenterConnectivityActionModel, r_conf: VCenterResourceConfig
) -> bool:
    forged_transmits = action.connection_params.vlan_service_attrs.forged_transmits
    if forged_transmits is None:
        forged_transmits = r_conf.forged_transmits
    return forged_transmits


def get_promiscuous_mode(
    action: VcenterConnectivityActionModel, r_conf: VCenterResourceConfig
) -> bool:
    promiscuous_mode = action.connection_params.vlan_service_attrs.promiscuous_mode
    if promiscuous_mode is None:
        promiscuous_mode = r_conf.promiscuous_mode
    return promiscuous_mode


def get_mac_changes(
    action: VcenterConnectivityActionModel, r_conf: VCenterResourceConfig
) -> bool:
    mac_changes = action.connection_params.vlan_service_attrs.mac_changes
    if mac_changes is None:
        mac_changes = r_conf.mac_changes
    return mac_changes
