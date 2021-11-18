from logging import Logger
from threading import Lock

from cloudshell.shell.flows.connectivity.basic_flow import AbstractConnectivityFlow
from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ConnectionModeEnum,
    ConnectivityActionModel,
)
from cloudshell.shell.flows.connectivity.parse_request_service import (
    AbstractParseConnectivityService,
)

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.network_handler import (
    DVPortGroupHandler,
    DVPortGroupNotFound,
)
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
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

    def _set_vlan(self, action: ConnectivityActionModel) -> str:
        vlan_id = action.connection_params.vlan_id
        self._logger.info(f"Start setting vlan {vlan_id}")
        vc_conf = self._resource_conf
        dc = DcHandler.get_dc(vc_conf.default_datacenter, self._si)
        vm = dc.get_vm_by_uuid(action.custom_action_attrs.vm_uuid)
        if not vm.has_vnics():
            raise BaseVCenterException(f"Trying to connect {vm} but it has no vNics")

        dc.get_network(vc_conf.holding_network)  # validate that it exists
        dv_port_name = generate_port_group_name(
            vc_conf.default_dv_switch,
            vlan_id,
            action.connection_params.mode.value,
        )

        port_group = self._get_or_create_port_group(
            dc,
            dv_port_name,
            vlan_id,
            action.connection_params.mode,
        )
        try:
            vnic = get_available_vnic(
                vm,
                vc_conf.holding_network,
                vc_conf.reserved_networks,
                action.custom_action_attrs.vnic,
            )
            vm.connect_vnic_to_port_group(vnic, port_group, self._logger)
        except Exception:
            self._remove_port_group(port_group)
            raise
        return "vlan created"

    def _remove_vlan(self, action: ConnectivityActionModel) -> str:
        vlan_id = action.connection_params.vlan_id
        self._logger.info(f"Start removing vlan {vlan_id}")

        vc_conf = self._resource_conf
        dc = DcHandler.get_dc(vc_conf.default_datacenter, self._si)
        vm = dc.get_vm_by_uuid(action.custom_action_attrs.vm_uuid)
        default_network = dc.get_network(vc_conf.holding_network)
        vnic = vm.get_vnic_by_mac(action.connector_attrs.interface, self._logger)
        net_name = vm.get_network_name_from_vnic(vnic)

        if vlan_id:
            expected_dv_port_name = generate_port_group_name(
                vc_conf.default_dv_switch,
                vlan_id,
                action.connection_params.mode.value,
            )
            remove_network = expected_dv_port_name == net_name
        else:
            remove_network = is_network_generated_name(net_name)

        if remove_network:
            vm.connect_vnic_to_network(vnic, default_network, self._logger)
            port_group = self._get_port_group(net_name, dc)
            self._remove_port_group(port_group)
        return "vlan removed"

    def _get_or_create_port_group(
        self,
        dc: DcHandler,
        dv_port_name: str,
        vlan_range: str,
        port_mode: ConnectionModeEnum,
    ) -> DVPortGroupHandler:
        with self._network_lock:
            dv_switch = dc.get_dv_switch(self._resource_conf.default_dv_switch)
            try:
                port_group = dv_switch.get_dv_port_group(dv_port_name)
            except DVPortGroupNotFound:
                dv_switch.create_dv_port_group(
                    dv_port_name,
                    vlan_range,
                    port_mode,
                    self._resource_conf.promiscuous_mode,
                    self._logger,
                )
                port_group = dv_switch.get_dv_port_group(dv_port_name)
        return port_group

    def _get_port_group(
        self, port_group_name: str, dc: DcHandler
    ) -> DVPortGroupHandler:
        with self._network_lock:
            dv_switch = dc.get_dv_switch(self._resource_conf.default_dv_switch)
            return dv_switch.get_dv_port_group(port_group_name)

    def _remove_port_group(self, port_group: DVPortGroupHandler):
        with self._network_lock:
            if not port_group.is_connected:
                port_group.destroy()
