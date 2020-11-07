from __future__ import annotations

import re

from pyVmomi import vim  # noqa

from cloudshell.cp.vcenter.exceptions import (
    BaseVCenterException,
    NetworkNotFoundException,
)

MAX_DVSWITCH_LENGTH = 60
QS_NAME_PREFIX = "QS"
PORT_GROUP_NAME_PATTERN = re.compile(rf"{QS_NAME_PREFIX}_.+_VLAN")


def generate_port_group_name(dv_switch_name: str, vlan_id: str, port_mode: str):
    dvs_name = dv_switch_name[:MAX_DVSWITCH_LENGTH]
    return f"{QS_NAME_PREFIX}_{dvs_name}_VLAN_{vlan_id}_{port_mode}"


def is_network_generated_name(net_name: str):
    return bool(PORT_GROUP_NAME_PATTERN.search(net_name))


def get_port_group_from_dv_switch(dv_switch, port_group_name: str):
    for port_group in dv_switch.portgroup:
        if port_group.name == port_group_name:
            return port_group
    raise NetworkNotFoundException(f"Port Group {port_group_name} not found")


def is_vm_has_vnics(vm):
    # Is there any network device on vm
    for device in vm.config.hardware.device:
        if isinstance(device, vim.vm.device.VirtualEthernetCard) and hasattr(
            device, "macAddress"
        ):
            return True
    return False


def validate_vm_has_vnics(vm):
    if not is_vm_has_vnics(vm):
        emsg = f"Trying to connect VM '{vm.name}' but it has no vNics"
        raise BaseVCenterException(emsg)


def get_network_from_vm(vm, net_name: str):
    for network in vm.network:
        if network.name == net_name:
            return network
    raise NetworkNotFoundException(f"Network {net_name} not found in VM {vm.name}")


def get_vlan_spec(port_mode: str, vlan_range: str):
    if port_mode.lower() == "access":
        spec = vim.dvs.VmwareDistributedVirtualSwitch.VlanIdSpec
        try:
            vlan_id = int(vlan_range)
        except ValueError:
            raise BaseVCenterException("Access VLAN supports only int vlan id")
    elif port_mode.lower() == "trunk":
        emsg = "Trunk VLAN should be a number or range in format 1-100"
        spec = vim.dvs.VmwareDistributedVirtualSwitch.TrunkVlanSpec
        try:
            parts = list(map(int, vlan_range.split("-")))
        except ValueError:
            raise BaseVCenterException(emsg)
        if len(parts) == 1:
            start = end = next(parts)
        elif len(parts) == 2:
            start, end = parts
        else:
            raise BaseVCenterException(emsg)
        vlan_id = [vim.NumericRange(start=start, end=end)]
    else:
        raise BaseVCenterException("Port mode should be access or trunk")
    return spec(vlanId=vlan_id, inherited=False)


def _get_vnics(vm):
    return (
        device
        for device in vm.config.hardware.device
        if isinstance(device, vim.vm.device.VirtualEthernetCard)
    )


def get_available_vnic(
    vm, default_net_name: str, reserved_networks: list[str], vnic_name=None
):
    vnics = (
        vnic
        for vnic in _get_vnics(vm)
        if not vnic_name or vnic_name == vnic.deviceInfo.label
    )
    for vnic in vnics:
        net_name = get_net_name_from_vnic(vnic, vm)
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


def get_vnic_by_mac(vm, mac_address: str):
    try:
        vnic = next(filter(lambda v: v.macAddress == mac_address, _get_vnics(vm)))
    except StopIteration:
        emsg = f"vNIC with mac address {mac_address} not found on VM {vm.name}"
        raise BaseVCenterException(emsg)
    return vnic


def get_net_name_from_vnic(vnic, vm) -> str:
    try:
        net_name = vnic.backing.network.name
    except AttributeError:
        for net in vm.network:
            try:
                if net.key == vnic.backing.port.portgroupKey:
                    net_name = net.name
                    break
            except AttributeError:
                continue
        else:
            net_name = ""
    return net_name
