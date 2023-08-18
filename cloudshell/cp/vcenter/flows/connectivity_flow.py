from __future__ import annotations

import logging
from collections.abc import Collection
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from itertools import chain
from threading import Lock
from typing import TYPE_CHECKING, Any

from attrs import define, field

from cloudshell.shell.flows.connectivity.cloud_providers_flow import (
    AbcCloudProviderConnectivityFlow,
    VnicInfo,
)
from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ConnectionModeEnum,
    is_set_action,
)

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.network_handler import (
    AbstractNetwork,
    DVPortGroupHandler,
    HostPortGroupNotFound,
    NetworkHandler,
    NetworkNotFound,
)
from cloudshell.cp.vcenter.handlers.si_handler import ResourceInUse, SiHandler
from cloudshell.cp.vcenter.handlers.switch_handler import (
    AbstractSwitchHandler,
    DvSwitchNotFound,
    PortGroupExists,
)
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler
from cloudshell.cp.vcenter.handlers.vnic_handler import Vnic, VnicNotFound
from cloudshell.cp.vcenter.handlers.vsphere_sdk_handler import VSphereSDKHandler
from cloudshell.cp.vcenter.models.connectivity_action_model import (
    VcenterConnectivityActionModel,
)
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig
from cloudshell.cp.vcenter.utils.connectivity_helpers import (
    PgCanNotBeRemoved,
    check_pg_can_be_removed,
    create_new_vnic,
    generate_port_group_name,
    get_existed_port_group_name,
    is_network_generated_name,
)

if TYPE_CHECKING:
    from cloudshell.cp.core.reservation_info import ReservationInfo


logger = logging.getLogger(__name__)


class DvSwitchNameEmpty(BaseVCenterException):
    def __init__(self):
        msg = (
            "For connectivity actions you have to specify default DvSwitch name in the "
            "resource or in every VLAN service"
        )
        super().__init__(msg)


@define
class VCenterConnectivityFlow(AbcCloudProviderConnectivityFlow):
    _resource_conf: VCenterResourceConfig
    _reservation_info: ReservationInfo
    _network_lock: Lock = field(init=False, factory=Lock)
    _switches: dict[str, AbstractSwitchHandler] = field(init=False, factory=dict)

    def __attrs_post_init__(self):
        self._si = SiHandler.from_config(self._resource_conf)
        self._vsphere_client = VSphereSDKHandler.from_config(
            resource_config=self._resource_conf,
            reservation_info=self._reservation_info,
            si=self._si,
        )
        self._dc = DcHandler.get_dc(self._resource_conf.default_datacenter, self._si)
        self._default_network = self._dc.get_network(
            self._resource_conf.holding_network
        )

    def validate_actions(
        self, actions: Collection[VcenterConnectivityActionModel]
    ) -> None:
        all_actions_with_switch = all(
            a.connection_params.vlan_service_attrs.switch_name for a in actions
        )
        if not self._resource_conf.default_dv_switch and not all_actions_with_switch:
            raise DvSwitchNameEmpty

    def pre_connectivity(
        self,
        actions: Collection[VcenterConnectivityActionModel],
        executor: ThreadPoolExecutor,
    ) -> None:
        existed_pg_names = set()
        net_to_create = {}  # {(pg_name, host_name): action}

        for action in filter(is_set_action, actions):
            if pg_name := get_existed_port_group_name(action):
                existed_pg_names.add(pg_name)
            else:
                vm = self.get_target(action)
                # we need to create network only once for every used host
                key = (self._generate_pg_name(action), vm.host.name)
                net_to_create[key] = action

        # check that existed networks exist
        tuple(executor.map(self._dc.get_network, existed_pg_names))

        # create networks
        tuple(executor.map(self._create_network, net_to_create.values()))

    def load_target(self, target_name: str) -> Any:
        return self._dc.get_vm_by_uuid(target_name)

    def get_vnics(self, vm: VmHandler) -> Collection[VnicInfo]:
        def get_vnic_info(vnic: Vnic) -> VnicInfo:
            return VnicInfo(
                vnic.name,
                int(self.vnic_name_to_index(vnic.name, vm)),
                self._network_can_be_replaced(vnic.network),
            )

        return tuple(map(get_vnic_info, vm.vnics))

    def set_vlan(
        self, action: VcenterConnectivityActionModel, target: VmHandler = None
    ) -> str:
        assert isinstance(target, VmHandler)
        vnic_name = action.custom_action_attrs.vnic
        pg_name = get_existed_port_group_name(action) or self._generate_pg_name(action)
        logger.info(f"Connecting {pg_name} to the {target}.{vnic_name} iface")

        network = self._dc.get_network(pg_name)
        try:
            vnic = target.get_vnic(vnic_name)
        except VnicNotFound:
            vnic = create_new_vnic(target, network, vnic_name)
        else:
            vnic.connect(network)

        return vnic.mac_address

    def remove_vlan(
        self, action: VcenterConnectivityActionModel, target: VmHandler = None
    ) -> str:
        assert isinstance(target, VmHandler)
        vnic = target.get_vnic_by_mac(action.connector_attrs.interface)
        logger.info(f"Disconnecting {vnic.network} from the {vnic} on the {target}")
        vnic.connect(self._default_network)
        return vnic.mac_address

    def clear(self, action: VcenterConnectivityActionModel, target: Any) -> str:
        assert isinstance(target, VmHandler)
        vnic_name = action.custom_action_attrs.vnic
        try:
            vnic = target.get_vnic(vnic_name)
        except VnicNotFound:
            logger.info(f"VNIC {vnic_name} is not created. Skip disconnecting")
            mac = ""
        else:
            logger.info(f"Disconnecting {vnic} from the {vnic.network} on the {target}")
            vnic.connect(self._default_network)
            mac = vnic.mac_address
        return mac

    def post_connectivity(
        self,
        actions: Collection[VcenterConnectivityActionModel],
        executor: ThreadPoolExecutor,
    ) -> None:
        net_to_remove = {}  # {(pg_name, host_name): action}

        for action in actions:
            if not get_existed_port_group_name(action):
                vm = self.get_target(action)
                # we need to remove network only once for every used host
                key = (self._generate_pg_name(action), vm.host.name)
                net_to_remove[key] = action

        # remove unused networks
        r = executor.map(self._remove_pg_with_checks, net_to_remove.values())
        tags = set(chain.from_iterable(r))
        self._remove_tags(tags)

    def _get_switch(
        self, action: VcenterConnectivityActionModel
    ) -> AbstractSwitchHandler:
        switch_name = self._get_switch_name(action)
        if not (switch := self._switches.get(switch_name)):
            try:
                switch = self._dc.get_dv_switch(switch_name)
            except DvSwitchNotFound:
                vm = self.get_target(action)
                switch = vm.get_v_switch(switch_name)
            self._switches[switch_name] = switch
        return switch

    @staticmethod
    def _validate_network(
        network: NetworkHandler | DVPortGroupHandler,
        switch: AbstractSwitchHandler,
        promiscuous_mode: bool,
        forged_transmits: bool,
        mac_changes: bool,
        port_mode: ConnectionModeEnum,
        vlan_id: str,
    ) -> None:
        try:
            pg = switch.get_port_group(network.name)
        except HostPortGroupNotFound:
            # In vCenter the host's port group can be deleted but the network remains.
            # In this case we need to recreate the port group.
            # It's possible if the network is used in a VM's snapshot
            # but the VM is disconnected from the network.
            switch.create_port_group(
                network.name,
                vlan_id,
                port_mode,
                promiscuous_mode,
                forged_transmits,
                mac_changes,
            )
            pg = switch.wait_port_group_appears(network.name)

        if pg.allow_promiscuous != promiscuous_mode:
            raise BaseVCenterException(f"{pg} has incorrect promiscuous mode setting")
        if pg.forged_transmits != forged_transmits:
            raise BaseVCenterException(f"{pg} has incorrect forged transmits setting")
        if pg.mac_changes != mac_changes:
            raise BaseVCenterException(
                f"{pg} has incorrect MAC address changes setting"
            )

    def _create_network(
        self, action: VcenterConnectivityActionModel
    ) -> AbstractNetwork:
        port_mode = action.connection_params.mode
        vlan_id = action.connection_params.vlan_id
        promiscuous_mode = self._get_promiscuous_mode(action)
        forged_transmits = self._get_forged_transmits(action)
        mac_changes = self._get_mac_changes(action)
        pg_name = self._generate_pg_name(action)

        switch = self._get_switch(action)
        try:
            network = self._dc.get_network(pg_name)
        except NetworkNotFound:
            try:
                switch.create_port_group(
                    pg_name,
                    vlan_id,
                    port_mode,
                    promiscuous_mode,
                    forged_transmits,
                    mac_changes,
                )
            except PortGroupExists:
                pass
            port_group = switch.wait_port_group_appears(pg_name)
            network = self._dc.wait_network_appears(pg_name)
            try:
                self._add_tags(network)
            except Exception:
                with suppress(ResourceInUse):
                    port_group.destroy()
                raise
        else:
            # we validate only network created by the Shell
            self._validate_network(
                network,
                switch,
                promiscuous_mode,
                forged_transmits,
                mac_changes,
                port_mode,
                vlan_id,
            )
        return network

    def _remove_pg_with_checks(
        self, action: VcenterConnectivityActionModel
    ) -> set[str]:
        tags = set()
        try:
            tags |= self._remove_pg(action)
        except PgCanNotBeRemoved as e:
            logger.info(f"Port group {e.name} should not be removed")
        except NetworkNotFound as e:
            logger.info(f"Network {e.name} is already removed")
        except ResourceInUse as e:
            logger.info(f"Network {e.name} is still in use, skip removing")
        return tags

    def _remove_pg(self, action: VcenterConnectivityActionModel) -> set[str]:
        pg_name = get_existed_port_group_name(action) or self._generate_pg_name(action)
        check_pg_can_be_removed(pg_name, action)
        network = self._dc.get_network(pg_name)
        network.wait_network_become_free(raise_=True)

        try:
            tags = self._get_network_tags(network)
        finally:
            if isinstance(network, DVPortGroupHandler):
                network.destroy()
            else:
                vm = self.get_target(action)
                # remove from the host where the VM is located
                vm.host.remove_port_group(network.name)
            del network
        logger.info(f"Network {pg_name} was removed")
        return tags

    def _get_network_tags(
        self, network: NetworkHandler | DVPortGroupHandler
    ) -> set[str]:
        """Get network's tag IDs."""
        tags = set()
        if self._vsphere_client and self._resource_conf.is_static:
            tags |= self._vsphere_client.get_attached_tags(network)
        return tags

    def _remove_tags(self, tags: set[str]) -> None:
        # In case of static resource we need to remove unused tags
        # in other cases tags would be removed in Delete Instance command
        if self._vsphere_client and self._resource_conf.is_static:
            self._vsphere_client.delete_unused_tags(tags)

    def _add_tags(self, network: NetworkHandler | DVPortGroupHandler) -> None:
        if self._vsphere_client:
            self._vsphere_client.assign_tags(network)

    def _network_can_be_replaced(self, net: AbstractNetwork) -> bool:
        reserved_networks = self._resource_conf.reserved_networks
        not_quali_name = not is_network_generated_name(net.name)
        if not net.name:
            result = True
        elif net.name == self._resource_conf.holding_network:
            result = True
        elif net.name not in reserved_networks and not_quali_name:
            result = True
        else:
            result = False
        return result

    def _generate_pg_name(self, action: VcenterConnectivityActionModel) -> str:
        switch_name = self._get_switch_name(action)
        vlan_id = action.connection_params.vlan_id
        port_mode = action.connection_params.mode
        return generate_port_group_name(switch_name, vlan_id, port_mode)

    def _get_switch_name(self, action: VcenterConnectivityActionModel) -> str:
        if not (switch_name := action.connection_params.vlan_service_attrs.switch_name):
            switch_name = self._resource_conf.default_dv_switch
        return switch_name

    def _get_forged_transmits(self, action: VcenterConnectivityActionModel) -> bool:
        if not (ft := action.connection_params.vlan_service_attrs.forged_transmits):
            ft = self._resource_conf.forged_transmits
        return ft

    def _get_promiscuous_mode(self, action: VcenterConnectivityActionModel) -> bool:
        if not (pm := action.connection_params.vlan_service_attrs.promiscuous_mode):
            pm = self._resource_conf.promiscuous_mode
        return pm

    def _get_mac_changes(self, action: VcenterConnectivityActionModel) -> bool:
        if not (mc := action.connection_params.vlan_service_attrs.mac_changes):
            mc = self._resource_conf.mac_changes
        return mc
