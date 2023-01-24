from __future__ import annotations

import re
from functools import cached_property
from typing import TYPE_CHECKING

from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler
from cloudshell.cp.vcenter.handlers.network_handler import (
    DVPortGroupHandler,
    NetworkHandler,
)
from cloudshell.cp.vcenter.handlers.virtual_device_handler import VirtualDevice
from cloudshell.cp.vcenter.utils.connectivity_helpers import is_ipv4

if TYPE_CHECKING:
    from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler


class VnicNotFound(BaseVCenterException):
    def __init__(self, name_or_id: str, vm: VmHandler):
        self.name_or_id = name_or_id
        if name_or_id.isdigit():
            msg = f"vNIC with ID '{name_or_id}' not found in the {vm}"
        else:
            msg = f"vNIC with name '{name_or_id}' not found in the {vm}"
        super().__init__(msg)


class VnicWithMacNotFound(BaseVCenterException):
    def __init__(self, mac_address: str, entity: ManagedEntityHandler):
        self.mac_address = mac_address
        self.entity = entity
        msg = f"vNIC with mac address {mac_address} not found in the {entity}"
        super().__init__(msg)


class VnicWithoutNetwork(BaseVCenterException):
    ...


class Vnic(VirtualDevice):
    @classmethod
    def create(cls, network: NetworkHandler | DVPortGroupHandler) -> Vnic:
        try:
            self = cls.vm.vnics[0]._create_new_vnic_same_type()
        except IndexError:
            self = cls(vim.vm.device.VirtualEthernetCard())
        self.connect(network)
        return self

    @cached_property
    def index(self) -> int:
        """Return the index of the vNIC on the VM."""
        return int(re.search(r"\d+$", self.name).group())

    @property
    def key(self) -> int:
        return self._vc_obj.key

    @property
    def mac_address(self) -> str:
        return self._vc_obj.macAddress.upper()

    @property
    def network(self) -> NetworkHandler | DVPortGroupHandler:
        try:
            return NetworkHandler(self._vc_obj.backing.network, self.vm.si)
        except AttributeError:
            try:
                pg_key = self._vc_obj.backing.port.portgroupKey
            except ValueError:
                raise VnicWithoutNetwork

            for pg in self.vm.dv_port_groups:
                if pg.key == pg_key:
                    break
            else:
                raise VnicWithoutNetwork
            return pg

    @property
    def ipv4(self) -> str | None:
        ips = self.vm.get_ip_addresses_by_vnic(self)
        ipv4 = next(filter(is_ipv4, ips), None)
        return ipv4

    def connect(self, network: NetworkHandler | DVPortGroupHandler) -> None:
        if isinstance(network, NetworkHandler):
            nic_spec = self._create_spec_for_connecting_network(network)
        else:
            nic_spec = self._create_spec_for_connecting_dv_port_group(network)
        config_spec = vim.vm.ConfigSpec(deviceChange=[nic_spec])
        self.vm._reconfigure(config_spec)

        if self._is_new:  # we need to update vCenter object
            vnic = self.vm.vnics[-1]
            assert vnic.network == network
            self._vc_obj = vnic.get_vc_obj()

    def _create_new_vnic_same_type(self) -> Vnic:
        return Vnic(type(self._vc_obj)())

    def _create_spec_for_connecting_generic_network(
        self,
    ) -> vim.vm.device.VirtualDeviceSpec:
        vnic = self._vc_obj
        vnic.wakeOnLanEnabled = True
        vnic.deviceInfo = vim.Description()
        vnic.connectable = vim.vm.device.VirtualDevice.ConnectInfo(
            connected=True,
            startConnected=True,
            allowGuestControl=True,
            status="untried",
        )

        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.device = vnic

        if self._is_new:  # vNIC is not connected to the VM yet
            nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        else:
            nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit

        return nic_spec

    @property
    def _is_new(self) -> bool:
        return not bool(self.mac_address)

    def _create_spec_for_connecting_network(
        self, network: NetworkHandler
    ) -> vim.vm.device.VirtualDeviceSpec:
        vnic = self._vc_obj
        vnic.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo(
            network=network.get_vc_obj(), deviceName=network.name
        )
        nic_spec = self._create_spec_for_connecting_generic_network()
        return nic_spec

    def _create_spec_for_connecting_dv_port_group(
        self, port_group: DVPortGroupHandler
    ) -> vim.vm.device.VirtualDeviceSpec:
        vnic = self._vc_obj
        vnic.backing = (
            vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo(
                port=vim.dvs.PortConnection(
                    portgroupKey=port_group.key,
                    switchUuid=port_group.switch_uuid,
                )
            )
        )
        nic_spec = self._create_spec_for_connecting_generic_network()
        return nic_spec
