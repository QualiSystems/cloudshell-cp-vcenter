from __future__ import annotations

import time
from logging import Logger
from threading import Lock

from cloudshell.shell.flows.connectivity.basic_flow import AbstractConnectivityFlow
from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ConnectionModeEnum,
    ConnectivityActionModel,
)
from cloudshell.shell.flows.connectivity.models.driver_response import (
    ConnectivityActionResult,
)
from cloudshell.shell.flows.connectivity.parse_request_service import (
    AbstractParseConnectivityService,
)

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.network_handler import (
    AbstractPortGroupHandler,
    DVPortGroupHandler,
    HostPortGroupHandler,
    NetworkHandler,
    PortGroupNotFound,
)
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.switch_handler import (
    DvSwitchHandler,
    DvSwitchNotFound,
    VSwitchHandler,
)
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig
from cloudshell.cp.vcenter.utils.connectivity_helpers import (
    generate_port_group_name,
    get_available_vnic,
    is_network_generated_name,
)


class DvSwitchNameEmpty(BaseVCenterException):
    def __init__(self):
        msg = "For connectivity actions you have to specify default DvSwitch"
        super().__init__(msg)


class VCenterConnectivityFlow(AbstractConnectivityFlow):
    def __init__(
        self,
        resource_conf: VCenterResourceConfig,
        parse_connectivity_request_service: AbstractParseConnectivityService,
        logger: Logger,
    ):
        super().__init__(parse_connectivity_request_service, logger)
        self._resource_conf = resource_conf
        self._si = SiHandler.from_config(resource_conf, logger)
        self._network_lock = Lock()

    def apply_connectivity(self, request: str) -> str:
        self._validate_dvs_present()
        return super().apply_connectivity(request)

    def _validate_dvs_present(self):
        if not self._resource_conf.default_dv_switch:
            raise DvSwitchNameEmpty

    def _set_vlan(self, action: ConnectivityActionModel) -> ConnectivityActionResult:
        vlan_id = action.connection_params.vlan_id
        self._logger.info(f"Start setting vlan {vlan_id}")
        vc_conf = self._resource_conf
        dc = DcHandler.get_dc(vc_conf.default_datacenter, self._si)
        vm = dc.get_vm_by_uuid(action.custom_action_attrs.vm_uuid)

        dc.get_network(vc_conf.holding_network)  # validate that it exists
        port_group_name = generate_port_group_name(
            vc_conf.default_dv_switch,
            vlan_id,
            action.connection_params.mode.value,
        )

        port_group = self._get_or_create_port_group(
            dc, vm, port_group_name, vlan_id, action.connection_params.mode
        )
        try:
            vnic = get_available_vnic(
                vm,
                vc_conf.holding_network,
                vc_conf.reserved_networks,
                action.custom_action_attrs.vnic,
            )
            if isinstance(port_group, DVPortGroupHandler):
                vm.connect_vnic_to_port_group(vnic, port_group, self._logger)
            elif isinstance(port_group, HostPortGroupHandler):
                network = dc.get_network(port_group.name)
                vm.connect_vnic_to_network(vnic, network, self._logger)
        except Exception:
            self._remove_port_group(port_group)
            raise
        msg = f"Setting VLAN {vlan_id} successfully completed"
        return ConnectivityActionResult.success_result_vm(action, msg, vnic.mac_address)

    def _remove_vlan(self, action: ConnectivityActionModel) -> ConnectivityActionResult:
        vlan_id = action.connection_params.vlan_id
        self._logger.info(f"Start removing vlan {vlan_id}")

        vc_conf = self._resource_conf
        dc = DcHandler.get_dc(vc_conf.default_datacenter, self._si)
        vm = dc.get_vm_by_uuid(action.custom_action_attrs.vm_uuid)
        default_network = dc.get_network(vc_conf.holding_network)
        vnic = vm.get_vnic_by_mac(action.connector_attrs.interface, self._logger)
        network = vm.get_network_from_vnic(vnic)

        if vlan_id:
            expected_dv_port_name = generate_port_group_name(
                vc_conf.default_dv_switch,
                vlan_id,
                action.connection_params.mode.value,
            )
            remove_network = expected_dv_port_name == network.name
        else:
            remove_network = is_network_generated_name(network.name)

        if remove_network:
            vm.connect_vnic_to_network(vnic, default_network, self._logger)
            port_group = self._get_port_group(network, vm)
            self._remove_port_group(port_group)
        msg = f"Removing VLAN {vlan_id} successfully completed"
        return ConnectivityActionResult.success_result_vm(action, msg, vnic.mac_address)

    def _get_or_create_port_group(
        self,
        dc: DcHandler,
        vm: VmHandler,
        port_group_name: str,
        vlan_range: str,
        port_mode: ConnectionModeEnum,
    ) -> AbstractPortGroupHandler:
        try:
            switch = dc.get_dv_switch(self._resource_conf.default_dv_switch)
        except DvSwitchNotFound:
            switch = vm.get_v_switch(self._resource_conf.default_dv_switch)

        with self._network_lock:
            try:
                port_group = switch.get_port_group(port_group_name)
            except PortGroupNotFound:
                switch.create_port_group(
                    port_group_name,
                    vlan_range,
                    port_mode,
                    self._resource_conf.promiscuous_mode,
                    self._logger,
                )
                port_group = self._wait_for_the_port_group_appears(
                    switch, port_group_name
                )
        return port_group

    def _wait_for_the_port_group_appears(
        self, switch: DvSwitchHandler | VSwitchHandler, port_name: str
    ) -> AbstractPortGroupHandler:
        delay = 2
        timeout = 60 * 5
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                pg = switch.get_port_group(port_name)
            except PortGroupNotFound:
                time.sleep(delay)
            else:
                return pg
        raise PortGroupNotFound(switch, port_name)

    def _get_port_group(
        self, network: DVPortGroupHandler | NetworkHandler, vm: VmHandler
    ) -> DVPortGroupHandler | HostPortGroupHandler:
        if isinstance(network, DVPortGroupHandler):
            return network

        with self._network_lock:
            switch = vm.get_v_switch(self._resource_conf.default_dv_switch)
            return switch.get_port_group(network.name)

    def _remove_port_group(self, port_group: DVPortGroupHandler | HostPortGroupHandler):
        with self._network_lock:
            if not port_group.is_connected:
                port_group.destroy()
