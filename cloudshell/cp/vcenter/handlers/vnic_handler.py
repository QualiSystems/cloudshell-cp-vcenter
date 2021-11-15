from __future__ import annotations

from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler
from cloudshell.cp.vcenter.handlers.network_handler import (
    DVPortGroupHandler,
    NetworkHandler,
)
from cloudshell.cp.vcenter.handlers.virtual_device_handler import VirtualDeviceHandler


class VnicWithMacNotFound(BaseVCenterException):
    def __init__(self, mac_address: str, entity: ManagedEntityHandler):
        self.mac_address = mac_address
        self.entity = entity
        msg = f"vNIC with mac address {mac_address} not found in the {entity}"
        super().__init__(msg)


class VnicWithoutNetwork(BaseVCenterException):
    ...


class VnicHandler(VirtualDeviceHandler):
    @property
    def mac_address(self) -> str | None:
        try:
            mac = self._device.macAddress
        except AttributeError:
            mac = None
        return mac

    @property
    def network_name(self) -> str:
        try:
            return self._device.backing.network.name
        except AttributeError:
            raise ValueError

    @property
    def network(self) -> vim.Network:
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
        )

        nic_spec = vim.vm.device.VirtualDeviceSpec()
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
            connected=False,
            startConnected=False,
        )
        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        nic_spec.device = vnic
        return nic_spec
