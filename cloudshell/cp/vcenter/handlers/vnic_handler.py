from __future__ import annotations

from typing import TYPE_CHECKING

import attr
from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler
from cloudshell.cp.vcenter.handlers.network_handler import (
    DVPortGroupHandler,
    NetworkHandler,
)
from cloudshell.cp.vcenter.handlers.virtual_device_handler import VirtualDeviceHandler

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


@attr.s(auto_attribs=True)
class VnicHandler(VirtualDeviceHandler):
    _is_new_vnic: bool = False

    @classmethod
    def create_new(cls, vnic_type=vim.vm.device.VirtualEthernetCard) -> VnicHandler:
        """The vNIC is not connected to the VM yet!."""
        return cls(vnic_type(), is_new_vnic=True)

    def __str__(self) -> str:
        return f"vNIC '{self.label}'"

    @property
    def label(self) -> str:
        if self._is_new_vnic:
            label = "<new>"
        else:
            label = super().label
        return label

    @property
    def vnic_type(self) -> type[vim.vm.device.VirtualDevice]:
        return type(self._device)

    @property
    def mac_address(self) -> str:
        return self._device.macAddress

    @property
    def vc_network(self) -> vim.Network:
        """Return the Network created from Host Port Group.

        Note: it would raise the ValueError for the dvPortGroup
        """
        try:
            return self._device.backing.network
        except AttributeError:
            raise ValueError

    @property
    def port_group_key(self) -> str:
        try:
            return self._device.backing.port.portgroupKey
        except AttributeError:
            raise ValueError

    def create_spec_for_connection_port_group(
        self, port_group: DVPortGroupHandler
    ) -> vim.vm.device.VirtualDeviceSpec:
        vnic = self._device
        vnic.backing = (
            vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo(
                port=vim.dvs.PortConnection(
                    portgroupKey=port_group.key,
                    switchUuid=port_group.switch_uuid,
                )
            )
        )
        vnic.connectable = vim.vm.device.VirtualDevice.ConnectInfo(
            connected=True,
            startConnected=True,
            allowGuestControl=True,
            status="untried",
        )

        nic_spec = vim.vm.device.VirtualDeviceSpec()

        if self._is_new_vnic:
            nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            self._is_new_vnic = False
        else:
            nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit

        nic_spec.device = vnic
        return nic_spec

    def create_spec_for_connection_network(
        self, network: NetworkHandler
    ) -> vim.vm.device.VirtualDeviceSpec:
        vnic = self._device
        vnic.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo(
            network=network._entity, deviceName=network.name
        )
        vnic.wakeOnLanEnabled = True
        vnic.deviceInfo = vim.Description()
        vnic.connectable = vim.vm.device.VirtualDevice.ConnectInfo(
            connected=True,
            startConnected=True,
            allowGuestControl=True,
            status="untried",
        )
        nic_spec = vim.vm.device.VirtualDeviceSpec()

        if self._is_new_vnic:
            nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            self._is_new_vnic = False
        else:
            nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit

        nic_spec.device = vnic
        return nic_spec
