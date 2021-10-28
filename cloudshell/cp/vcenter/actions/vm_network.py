from __future__ import annotations

import ipaddress
import re
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import (
    VMIPNotFoundException,
    VMNetworkNotFoundException,
)

if TYPE_CHECKING:
    from logging import Logger

    from cloudshell.cp.core.cancellation_manager import CancellationContextManager

    from cloudshell.cp.vcenter.api_client import VCenterAPIClient
    from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


class VMNetworkActions:
    QUALI_NETWORK_PREFIX = "QS_"
    DEFAULT_IP_REGEX = ".*"
    DEFAULT_IP_WAIT_TIME = 5

    def __init__(
        self,
        vcenter_client: VCenterAPIClient,
        resource_conf: VCenterResourceConfig,
        logger: Logger,
        cancellation_manager: CancellationContextManager,
    ):
        self._vcenter_client = vcenter_client
        self._resource_conf = resource_conf
        self._logger = logger
        self._cancellation_manager = cancellation_manager

    def get_vm_vnics(self, vm):
        self._logger.info(f"Getting vNICs for the VM {vm} ...")
        return [
            device
            for device in vm.config.hardware.device
            if isinstance(device, vim.vm.device.VirtualEthernetCard)
        ]

    def get_network_from_vnic(self, vm, vnic):
        self._logger.info(f"Getting VM Network for the VM {vm} vNIC {vnic} ...")

        backing = vnic.backing

        if hasattr(backing, "network"):
            return backing.network

        for network in vm.network:
            if hasattr(network, "key") and network.key == backing.port.portgroupKey:
                return network

        raise VMNetworkNotFoundException(
            f"Unable to find network for the vNIC {vnic.name}"
        )

    def get_network_vlan_id(self, network):
        self._logger.info(f"Getting VM Network VLAN ID from the network {network} ...")
        try:
            return network.config.defaultPortConfig.vlan.vlanId
        except AttributeError:
            pass

    def is_reserved_network(self, network):
        return network.name in self._resource_conf.reserved_networks

    def is_quali_network(self, network):
        return network.name.startswith(self.QUALI_NETWORK_PREFIX)

    def convert_vlan_id_to_str(self, vlan_id):
        self._logger.info(f"Converting VLAN ID {vlan_id} to string format ...")

        if isinstance(vlan_id, list):
            vlan_id = ",".join([self.convert_vlan_id_to_str(v) for v in vlan_id if v])

        elif isinstance(vlan_id, vim.NumericRange):
            if vlan_id.start == vlan_id.end:
                vlan_id = vlan_id.start
            else:
                vlan_id = f"{vlan_id.start}-{vlan_id.end}"

        vlan_id = str(vlan_id)
        self._logger.info(f"Converted VLAN ID: {vlan_id}")

        return vlan_id

    def _is_ipv4_address(self, ip):
        self._logger.info(f"Checking if IP address {ip} is IPv4 ...")
        is_ipv4 = True
        try:
            ipaddress.IPv4Address(ip)
        except ipaddress.AddressValueError:
            is_ipv4 = False

        self._logger.info(f"IP address is IPv4: {is_ipv4} ...")
        return is_ipv4

    def get_vm_ip_from_vnic(self, vm, vnic):
        """Get VM IP address from the vNIC."""
        self._logger.info(f"Getting IPv4 address from the vNIC {vnic} ...")
        for net in vm.guest.net:
            if str(net.deviceConfigId) == str(vnic.key):
                for ip_address in net.ipAddress:
                    if self._is_ipv4_address(ip_address):
                        return ip_address

    def _get_ip_regex_match_function(self, ip_regex=None):
        """Get Regex Match function for the VM IP address."""
        self._logger.info(
            f"Getting IP RegEx match function for the RegEx {ip_regex} ..."
        )

        if ip_regex is None:
            ip_regex = self.DEFAULT_IP_REGEX
        try:
            return re.compile(ip_regex).match
        except Exception:
            raise AttributeError(f"Invalid IP regex : {ip_regex}")

    def _get_vm_ip_addresses(self, vm, default_network):
        """Get all VM IP address except the default network address."""
        self._logger.info(f"Getting all VM IP addresses for the vm {vm} ...")
        ips = []

        if vm.guest.ipAddress:
            ips.append(vm.guest.ipAddress)

        for nic in vm.guest.net:
            if nic.network != default_network:
                for addr in nic.ipAddress:
                    if addr:
                        ips.append(addr)

        self._logger.info(f"Found VM IP addresses: {ips} ...")
        return ips

    def _find_vm_ip(self, vm, default_network, ip_match_function):
        """Find VM IP address."""
        self._logger.info(f"Finding VM IP address for the vm {vm} ...")
        for ip in self._get_vm_ip_addresses(vm, default_network):
            if self._is_ipv4_address(ip):
                ip = ip_match_function(ip)
                if ip:
                    return ip

    def get_vm_ip(self, vm, default_network=None, ip_regex=None, timeout=None):
        """Get VM IP address."""
        self._logger.info(f"Getting IP address for the VM {vm} from the vCenter ...")

        timeout = timeout or 0
        timeout_time = datetime.now() + timedelta(seconds=timeout)
        ip_regex_match = self._get_ip_regex_match_function(ip_regex)
        ip = None

        while not ip:
            with self._cancellation_manager:
                self._logger.info(f"Getting IP for VM {vm.name} ...")
                ip = self._find_vm_ip(
                    vm=vm,
                    default_network=default_network,
                    ip_match_function=ip_regex_match,
                )

            if ip:
                return ip

            with self._cancellation_manager:
                time.sleep(self.DEFAULT_IP_WAIT_TIME)

            if datetime.now() > timeout_time:
                raise VMIPNotFoundException("Unable to get VM IP")
