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

from cloudshell.cp.vcenter.api.client import VCenterAPIClient
from cloudshell.cp.vcenter.exceptions import NetworkNotFoundException
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig
from cloudshell.cp.vcenter.utils.connectivity_helpers import (
    generate_port_group_name,
    get_available_vnic,
    get_net_name_from_vnic,
    get_port_group_from_dv_switch,
    get_vnic_by_mac,
    is_network_generated_name,
    validate_vm_has_vnics,
)


class ConnectivityFlow(AbstractConnectivityFlow):
    def __init__(
        self,
        resource_conf: VCenterResourceConfig,
        vcenter_client: VCenterAPIClient,
        parse_connectivity_request_service: AbstractParseConnectivityService,
        logger: Logger,
    ):
        super().__init__(parse_connectivity_request_service, logger)
        self._resource_conf = resource_conf
        self._vcenter_client = vcenter_client
        self._network_lock = Lock()

    def _set_vlan(self, action: ConnectivityActionModel) -> str:
        vc_conf = self._resource_conf
        vc_client = self._vcenter_client
        dc = vc_client.get_dc(vc_conf.default_datacenter)
        vm = vc_client.get_vm(action.custom_action_attrs.vm_uuid, dc)
        validate_vm_has_vnics(vm)
        vc_client.get_network(vc_conf.holding_network, dc)  # validate that it exists
        dv_port_name = generate_port_group_name(
            vc_conf.default_dv_switch,
            action.connection_params.vlan_id,
            action.connection_params.mode.value,
        )

        port_group = self._get_or_create_port_group(
            dc,
            dv_port_name,
            action.connection_params.vlan_id,
            action.connection_params.mode,
        )
        try:
            vnic = get_available_vnic(
                vm,
                vc_conf.holding_network,
                vc_conf.reserved_networks,
                action.custom_action_attrs.vnic,
            )
            vc_client.connect_vnic_to_port_group(vnic, port_group, vm)
        except Exception:
            self._remove_port_group(port_group)
            raise
        return "vlan created"

    def _remove_vlan(self, action: ConnectivityActionModel) -> str:
        vc_conf = self._resource_conf
        vc_client = self._vcenter_client
        dc = vc_client.get_dc(vc_conf.default_datacenter)
        vm = vc_client.get_vm(action.custom_action_attrs.vm_uuid, dc)
        default_network = vc_client.get_network(vc_conf.holding_network, dc)
        vnic = get_vnic_by_mac(vm, action.connector_attrs.interface)
        net_name = get_net_name_from_vnic(vnic, vm)

        if action.connection_params.vlan_id:
            expected_dv_port_name = generate_port_group_name(
                vc_conf.default_dv_switch,
                action.connection_params.vlan_id,
                action.connection_params.mode.value,
            )
            remove_network = expected_dv_port_name == net_name
        else:
            remove_network = is_network_generated_name(net_name)

        if remove_network:
            vc_client.connect_vnic_to_network(vnic, default_network, vm)
            port_group = self._get_port_group(net_name, dc)
            self._remove_port_group(port_group)
        return "vlan removed"

    def _get_or_create_port_group(
        self, dc, dv_port_name: str, vlan_range: str, port_mode: ConnectionModeEnum
    ):
        with self._network_lock:
            dv_switch = self._vcenter_client.get_dv_switch(
                self._resource_conf.default_dv_switch, dc
            )
            try:
                port_group = get_port_group_from_dv_switch(dv_switch, dv_port_name)
            except NetworkNotFoundException:
                self._vcenter_client.create_dv_port_group(
                    dv_switch,
                    dv_port_name,
                    vlan_range,
                    port_mode,
                    self._resource_conf.promiscuous_mode,
                )
                port_group = get_port_group_from_dv_switch(dv_switch, dv_port_name)
        return port_group

    def _get_port_group(self, port_group_name: str, dc):
        with self._network_lock:
            dv_switch = self._vcenter_client.get_dv_switch(
                self._resource_conf.default_dv_switch, dc
            )
            return get_port_group_from_dv_switch(dv_switch, port_group_name)

    def _remove_port_group(self, port_group):
        with self._network_lock:
            if not port_group.vm:
                port_group.Destroy()
