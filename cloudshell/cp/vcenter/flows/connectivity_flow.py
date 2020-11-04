from logging import Logger
from threading import Lock

from cloudshell.shell.flows.connectivity.basic_flow import AbstractConnectivityFlow

from cloudshell.cp.vcenter.api.client import VCenterAPIClient
from cloudshell.cp.vcenter.exceptions import NetworkNotFoundException
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig
from cloudshell.cp.vcenter.utils.connectivity_helpers import (
    generate_port_group_name,
    get_available_vnic,
    get_network_from_vm,
    get_port_group_from_dv_switch,
    validate_vm_has_vnics,
)


class ConnectivityFlow(AbstractConnectivityFlow):
    IS_VLAN_RANGE_SUPPORTED = True
    IS_MULTI_VLAN_SUPPORTED = False

    def __init__(
        self,
        resource_conf: VCenterResourceConfig,
        vcenter_client: VCenterAPIClient,
        logger: Logger,
    ):
        super().__init__(logger)
        self._resource_conf = resource_conf
        self._vcenter_client = vcenter_client
        self._create_network_lock = Lock()

    def _add_vlan_flow(
        self,
        vlan_range: str,
        port_mode: str,
        full_name: str,
        qnq: bool,
        c_tag: str,
        vm_uid: str,
    ):
        vnic_name = None
        vc_conf = self._resource_conf
        vc_client = self._vcenter_client
        dc = vc_client.get_dc(vc_conf.default_datacenter)
        vm = vc_client.get_vm(vm_uid, dc)
        validate_vm_has_vnics(vm)
        default_network = vc_client.get_network(vc_conf.holding_network, dc)
        dv_port_name = generate_port_group_name(
            vc_conf.default_dv_switch, vlan_range, port_mode
        )

        network = self._get_or_create_network(
            dc, vm, dv_port_name, vlan_range, port_mode
        )
        vnic = get_available_vnic(
            vm, vc_conf.holding_network, vc_conf.reserved_networks, vnic_name
        )

    def _remove_vlan_flow(
        self, vlan_range: str, full_name: str, port_mode: str, vm_uid: str
    ):
        pass

    def _remove_all_vlan_flow(self, full_name: str, vm_uid: str):
        pass

    def _get_or_create_network(self, dc, vm, dv_port_name, vlan_range, port_mode):
        with self._create_network_lock:
            try:
                network = get_network_from_vm(vm, dv_port_name)
            except NetworkNotFoundException:
                dv_switch = self._vcenter_client.get_dv_switch(
                    self._resource_conf.default_dv_switch, dc
                )
                try:
                    network = get_port_group_from_dv_switch(dv_switch, dv_port_name)
                except NetworkNotFoundException:
                    self._vcenter_client.create_dv_port_group(
                        dv_switch,
                        dv_port_name,
                        vlan_range,
                        port_mode,
                        self._resource_conf.promiscuous_mode,
                    )
                    network = get_port_group_from_dv_switch(dv_switch, dv_port_name)
        return network
