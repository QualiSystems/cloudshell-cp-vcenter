from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from cloudshell.cp.core.request_actions.models import (
    VmDetailsData,
    VmDetailsNetworkInterface,
    VmDetailsProperty,
)

from cloudshell.cp.vcenter.actions.vm_network import VMNetworkActions
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.vm_handler import PowerState, VmHandler
from cloudshell.cp.vcenter.models.deploy_app import (
    BaseVCenterDeployApp,
    VMFromImageDeployApp,
    VMFromLinkedCloneDeployApp,
    VMFromTemplateDeployApp,
    VMFromVMDeployApp,
)
from cloudshell.cp.vcenter.models.deployed_app import (
    BaseVCenterDeployedApp,
    VMFromImageDeployedApp,
    VMFromLinkedCloneDeployedApp,
    VMFromTemplateDeployedApp,
    VMFromVMDeployedApp,
)
from cloudshell.cp.vcenter.utils.bytes_converter import format_bytes

if TYPE_CHECKING:
    from logging import Logger

    from cloudshell.cp.core.cancellation_manager import CancellationContextManager

    from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


def handle_vm_details_error(func):
    @functools.wraps(func)
    def wrapper(self, virtual_machine, *args, **kwargs):
        try:
            return func(self, virtual_machine, *args, **kwargs)
        except Exception as e:
            self._logger.exception("Failed to created VM Details:")
            return VmDetailsData(appName=virtual_machine.name, errorMessage=str(e))

    return wrapper


class VMDetailsActions(VMNetworkActions):
    def __init__(
        self,
        si: SiHandler,
        resource_conf: VCenterResourceConfig,
        logger: Logger,
        cancellation_manager: CancellationContextManager,
    ):
        self._si = si
        super().__init__(resource_conf, logger, cancellation_manager)

    @staticmethod
    def _prepare_common_vm_instance_data(vm: VmHandler) -> list[VmDetailsProperty]:
        return [
            VmDetailsProperty(key="CPU", value=f"{vm.num_cpu} vCPU"),
            VmDetailsProperty(key="Memory", value=format_bytes(vm.memory_size)),
            VmDetailsProperty(key="Disk Size", value=format_bytes(vm.disk_size)),
            VmDetailsProperty(key="Guest OS", value=vm.guest_os),
            VmDetailsProperty(key="Managed Object Reference ID", value=vm._moId),
        ]

    def _prepare_vm_network_data(
        self, vm: VmHandler, deploy_app: BaseVCenterDeployApp | BaseVCenterDeployedApp
    ) -> list[VmDetailsNetworkInterface]:
        """Prepare VM Network data."""
        self._logger.info(f"Preparing VM Details network data for the {vm}")
        network_interfaces = []

        if deploy_app.wait_for_ip and vm.power_state is PowerState.ON:
            primary_ip = self.get_vm_ip(vm._entity, ip_regex=deploy_app.ip_regex)
        else:
            primary_ip = None

        for vnic in vm.vnics:
            network = vm.get_network_from_vnic(vnic)
            is_predefined = network.name in self._resource_conf.reserved_networks
            private_ip = self.get_vm_ip_from_vnic(vm._entity, vnic._device)
            vlan_id = vm.get_network_vlan_id(network)

            if vlan_id and (self.is_quali_network(network.name) or is_predefined):
                is_primary = private_ip and primary_ip == private_ip

                network_data = [
                    VmDetailsProperty(key="IP", value=private_ip),
                    VmDetailsProperty(key="MAC Address", value=vnic.mac_address),
                    VmDetailsProperty(key="Network Adapter", value=vnic.label),
                    VmDetailsProperty(key="Port Group Name", value=network.name),
                ]

                interface = VmDetailsNetworkInterface(
                    interfaceId=vnic.mac_address,
                    networkId=str(vlan_id),
                    isPrimary=is_primary,
                    isPredefined=is_predefined,
                    networkData=network_data,
                    privateIpAddress=private_ip,
                )
                network_interfaces.append(interface)

        return network_interfaces

    @handle_vm_details_error
    def prepare_vm_from_vm_details(
        self, vm: VmHandler, deploy_app: VMFromVMDeployApp | VMFromVMDeployedApp
    ) -> VmDetailsData:
        vm_instance_data = [
            VmDetailsProperty(
                key="Cloned VM Name",
                value=deploy_app.vcenter_vm,
            ),
        ] + self._prepare_common_vm_instance_data(vm)

        vm_network_data = self._prepare_vm_network_data(vm, deploy_app)
        return VmDetailsData(
            appName=vm.name,
            vmInstanceData=vm_instance_data,
            vmNetworkData=vm_network_data,
        )

    @handle_vm_details_error
    def prepare_vm_from_template_details(
        self,
        vm: VmHandler,
        deploy_app: VMFromTemplateDeployApp | VMFromTemplateDeployedApp,
    ) -> VmDetailsData:
        vm_instance_data = [
            VmDetailsProperty(
                key="Template Name",
                value=deploy_app.vcenter_template,
            ),
        ] + self._prepare_common_vm_instance_data(vm)

        vm_network_data = self._prepare_vm_network_data(vm, deploy_app)
        return VmDetailsData(
            appName=vm.name,
            vmInstanceData=vm_instance_data,
            vmNetworkData=vm_network_data,
        )

    @handle_vm_details_error
    def prepare_vm_from_clone_details(
        self,
        vm: VmHandler,
        deploy_app: VMFromLinkedCloneDeployApp | VMFromLinkedCloneDeployedApp,
    ) -> VmDetailsData:
        vm_instance_data = [
            VmDetailsProperty(
                key="Cloned VM Name",
                value=(
                    f"{deploy_app.vcenter_vm} "
                    f"(snapshot: {deploy_app.vcenter_vm_snapshot})"
                ),
            ),
        ] + self._prepare_common_vm_instance_data(vm)

        vm_network_data = self._prepare_vm_network_data(vm, deploy_app)
        return VmDetailsData(
            appName=vm.name,
            vmInstanceData=vm_instance_data,
            vmNetworkData=vm_network_data,
        )

    @handle_vm_details_error
    def prepare_vm_from_image_details(
        self, vm: VmHandler, deploy_app: VMFromImageDeployApp | VMFromImageDeployedApp
    ) -> VmDetailsData:
        vm_instance_data = [
            VmDetailsProperty(
                key="Base Image Name",
                value=deploy_app.vcenter_image.split("/")[-1],
            ),
        ] + self._prepare_common_vm_instance_data(vm)

        vm_network_data = self._prepare_vm_network_data(vm, deploy_app)
        return VmDetailsData(
            appName=vm.name,
            vmInstanceData=vm_instance_data,
            vmNetworkData=vm_network_data,
        )

    def create(
        self, vm: VmHandler, app_model: BaseVCenterDeployApp | BaseVCenterDeployedApp
    ) -> VmDetailsData:
        if isinstance(app_model, (VMFromVMDeployApp, VMFromVMDeployedApp)):
            res = self.prepare_vm_from_vm_details(vm, app_model)
        elif isinstance(
            app_model, (VMFromTemplateDeployApp, VMFromTemplateDeployedApp)
        ):
            res = self.prepare_vm_from_template_details(vm, app_model)
        elif isinstance(
            app_model, (VMFromLinkedCloneDeployApp, VMFromLinkedCloneDeployedApp)
        ):
            res = self.prepare_vm_from_clone_details(vm, app_model)
        elif isinstance(app_model, (VMFromImageDeployApp, VMFromImageDeployedApp)):
            res = self.prepare_vm_from_image_details(vm, app_model)
        else:
            raise NotImplementedError(f"Not supported type {type(app_model)}")
        self._logger.info(f"VM Details: {res}")
        return res
