from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from cloudshell.cp.core.request_actions.models import (
    VmDetailsData,
    VmDetailsNetworkInterface,
    VmDetailsProperty,
)

from cloudshell.cp.vcenter.actions.vm import VMActions
from cloudshell.cp.vcenter.actions.vm_network import VMNetworkActions
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
from cloudshell.cp.vcenter.utils import bytes_converter

if TYPE_CHECKING:
    from logging import Logger

    from cloudshell.cp.core.cancellation_manager import CancellationContextManager

    from cloudshell.cp.vcenter.api_client import VCenterAPIClient
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


class VMDetailsActions(VMActions, VMNetworkActions):
    def __init__(
        self,
        vcenter_client: VCenterAPIClient,
        resource_conf: VCenterResourceConfig,
        logger: Logger,
        cancellation_manager: CancellationContextManager,
    ):
        VMNetworkActions.__init__(
            self,
            vcenter_client=vcenter_client,
            resource_conf=resource_conf,
            logger=logger,
            cancellation_manager=cancellation_manager,
        )

    def _prepare_common_vm_instance_data(self, virtual_machine):
        return [
            VmDetailsProperty(
                key="CPU",
                value=f"{virtual_machine.summary.config.numCpu} vCPU",
            ),
            VmDetailsProperty(
                key="Memory",
                value=bytes_converter.format_bytes(
                    virtual_machine.summary.config.memorySizeMB,
                    prefix=bytes_converter.PREFIX_MB,
                ),
            ),
            VmDetailsProperty(
                key="Disk Size",
                value=bytes_converter.format_bytes(
                    self.get_vm_disk_size(virtual_machine)
                ),
            ),
            VmDetailsProperty(
                key="Guest OS",
                value=virtual_machine.summary.config.guestFullName,
            ),
            VmDetailsProperty(
                key="Managed Object Reference ID", value=virtual_machine._GetMoId()
            ),
        ]

    def _prepare_vm_network_data(self, virtual_machine, deploy_app):
        """Prepare VM Network data."""
        self._logger.info(
            f"Preparing VM Details network data for the VM {virtual_machine} ..."
        )

        network_interfaces = []

        if deploy_app.wait_for_ip:
            primary_ip = self.get_vm_ip(
                vm=virtual_machine, ip_regex=deploy_app.ip_regex
            )
        else:
            primary_ip = None

        for vnic in self.get_vm_vnics(vm=virtual_machine):
            network = self.get_network_from_vnic(vm=virtual_machine, vnic=vnic)
            vlan_id = self.get_network_vlan_id(network)
            is_predefined = self.is_reserved_network(network)
            private_ip = self.get_vm_ip_from_vnic(vm=virtual_machine, vnic=vnic)

            if vlan_id and (self.is_quali_network(network) or is_predefined):
                is_primary = private_ip and primary_ip == private_ip

                network_data = [
                    VmDetailsProperty(key="IP", value=private_ip),
                    VmDetailsProperty(key="MAC Address", value=vnic.macAddress),
                    VmDetailsProperty(
                        key="Network Adapter", value=vnic.deviceInfo.label
                    ),
                    VmDetailsProperty(key="Port Group Name", value=network.name),
                ]

                interface = VmDetailsNetworkInterface(
                    interfaceId=vnic.macAddress,
                    networkId=self.convert_vlan_id_to_str(vlan_id),
                    isPrimary=is_primary,
                    isPredefined=is_predefined,
                    networkData=network_data,
                    privateIpAddress=private_ip,
                )
                network_interfaces.append(interface)

        return network_interfaces

    @handle_vm_details_error
    def prepare_vm_from_vm_details(self, virtual_machine, deploy_app):
        vm_instance_data = [
            VmDetailsProperty(
                key="Cloned VM Name",
                value=deploy_app.vcenter_vm,
            ),
        ] + self._prepare_common_vm_instance_data(virtual_machine=virtual_machine)

        vm_network_data = self._prepare_vm_network_data(
            virtual_machine=virtual_machine,
            deploy_app=deploy_app,
        )
        return VmDetailsData(
            appName=virtual_machine.name,
            vmInstanceData=vm_instance_data,
            vmNetworkData=vm_network_data,
        )

    @handle_vm_details_error
    def prepare_vm_from_template_details(self, virtual_machine, deploy_app):
        vm_instance_data = [
            VmDetailsProperty(
                key="Template Name",
                value=deploy_app.vcenter_template,
            ),
        ] + self._prepare_common_vm_instance_data(virtual_machine=virtual_machine)

        vm_network_data = self._prepare_vm_network_data(
            virtual_machine=virtual_machine,
            deploy_app=deploy_app,
        )
        return VmDetailsData(
            appName=virtual_machine.name,
            vmInstanceData=vm_instance_data,
            vmNetworkData=vm_network_data,
        )

    @handle_vm_details_error
    def prepare_vm_from_clone_details(self, virtual_machine, deploy_app):
        vm_instance_data = [
            VmDetailsProperty(
                key="Cloned VM Name",
                value=(
                    f"{deploy_app.vcenter_vm} "
                    f"(snapshot: {deploy_app.vcenter_vm_snapshot})"
                ),
            ),
        ] + self._prepare_common_vm_instance_data(virtual_machine=virtual_machine)

        vm_network_data = self._prepare_vm_network_data(
            virtual_machine=virtual_machine,
            deploy_app=deploy_app,
        )
        return VmDetailsData(
            appName=virtual_machine.name,
            vmInstanceData=vm_instance_data,
            vmNetworkData=vm_network_data,
        )

    @handle_vm_details_error
    def prepare_vm_from_image_details(self, virtual_machine, deploy_app):
        vm_instance_data = [
            VmDetailsProperty(
                key="Base Image Name",
                value=deploy_app.vcenter_image.split("/")[-1],
            ),
        ] + self._prepare_common_vm_instance_data(virtual_machine=virtual_machine)

        vm_network_data = self._prepare_vm_network_data(
            virtual_machine=virtual_machine,
            deploy_app=deploy_app,
        )
        return VmDetailsData(
            appName=virtual_machine.name,
            vmInstanceData=vm_instance_data,
            vmNetworkData=vm_network_data,
        )

    def create(
        self, vm, app_model: BaseVCenterDeployApp | BaseVCenterDeployedApp
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

        return res
