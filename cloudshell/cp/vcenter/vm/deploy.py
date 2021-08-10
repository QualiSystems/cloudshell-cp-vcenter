import os
import traceback

from pyVmomi import vim

from cloudshell.cp.core.models import Attribute, DeployAppResult, VmDetailsProperty
from cloudshell.cp.core.utils import convert_to_bool

from cloudshell.cp.vcenter.common.cloud_shell.conn_details_retriever import (
    ResourceConnectionDetailsRetriever,
)
from cloudshell.cp.vcenter.common.vcenter.vm_location import VMLocation
from cloudshell.cp.vcenter.constants import VM_CUSTOMIZATION_SPEC_CUSTOM_PARAM
from cloudshell.cp.vcenter.exceptions.reconfigure_vm import ReconfigureVMException
from cloudshell.cp.vcenter.models.vCenterCloneVMFromVMResourceModel import (
    vCenterCloneVMFromVMResourceModel,
)
from cloudshell.cp.vcenter.models.VCenterDeployVMFromLinkedCloneResourceModel import (
    VCenterDeployVMFromLinkedCloneResourceModel,
)
from cloudshell.cp.vcenter.models.vCenterVMFromImageResourceModel import (
    vCenterVMFromImageResourceModel,
)
from cloudshell.cp.vcenter.models.vCenterVMFromTemplateResourceModel import (
    vCenterVMFromTemplateResourceModel,
)
from cloudshell.cp.vcenter.vm.ovf_image_params import OvfImageParams
from cloudshell.cp.vcenter.vm.vcenter_details_factory import VCenterDetailsFactory


class VirtualMachineDeployer(object):
    def __init__(
        self,
        pv_service,
        name_generator,
        ovf_service,
        resource_model_parser,
        vm_details_provider,
        folder_manager,
    ):
        """

        :param pv_service:
        :type pv_service: cloudshell.cp.vcenter.common.vcenter.vmomi_service.pyVmomiService
        :param name_generator:
        :param ovf_service:
        :type ovf_service: cloudshell.cp.vcenter.common.vcenter.ovf_service.OvfImageDeployerService
        :type resource_model_parser: ResourceModelParser
        :param vm_details_provider:
        :type vm_details_provider: cloudshell.cp.vcenter.vm.vm_details_provider.VmDetailsProvider
        :param folder_manager:
        :return:
        """
        self.pv_service = pv_service
        self.folder_manager = folder_manager
        self.name_generator = name_generator
        self.ovf_service = (
            ovf_service  # type common.vcenter.ovf_service.OvfImageDeployerService
        )
        self.resource_model_parser = resource_model_parser  # type ResourceModelParser
        self.vm_details_provider = vm_details_provider

    def deploy_from_linked_clone(
        self,
        si,
        logger,
        session,
        data_holder,
        app_resource_model,
        vcenter_data_model,
        reservation_id,
        cancellation_context,
    ):
        """
        deploy Cloned VM From VM Command, will deploy vm from a snapshot

        :param cancellation_context:
        :param si:
        :param logger:
        :param data_holder:
        :param vcenter_data_model:
        :param str reservation_id:
        :rtype DeployAppResult:
        :return:
        """

        template_resource_model = data_holder.template_resource_model
        orig_vm_path, orig_vm_name = os.path.split(template_resource_model.vcenter_vm)
        orig_vm_path = VMLocation.combine(
            [vcenter_data_model.default_datacenter, orig_vm_path]
        )
        original_vm = self.pv_service.find_vm_by_name(
            si=si,
            path=orig_vm_path,
            name=orig_vm_name,
        )

        disk_count = 0
        for device in original_vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualDisk):
                disk_count += 1
                logger.debug(
                    "Original VM Disk {} size {}".format(
                        disk_count,
                        device.capacityInKB,
                    )
                )
                if f"{disk_count}:" in template_resource_model.hdd:
                    logger.error(
                        f"Disk {disk_count} can not be reconfigured "
                        f"because it exists in original Virtual Machine."
                    )
                    self.folder_manager.delete_folder_if_empty(
                        si=si,
                        folder_full_path=VMLocation.combine(
                            [
                                vcenter_data_model.default_datacenter,
                                template_resource_model.vm_location,
                            ]
                        ),
                        logger=logger,
                    )
                    raise Exception(
                        "Can not deploy current VM configuration. See logs for details."
                    )

        return self._deploy_a_clone(
            si=si,
            logger=logger,
            session=session,
            app_name=data_holder.app_name,
            template_name=template_resource_model.vcenter_vm,
            deploy_params=template_resource_model,
            app_resource_model=app_resource_model,
            vcenter_data_model=vcenter_data_model,
            reservation_id=reservation_id,
            cancellation_context=cancellation_context,
            snapshot=template_resource_model.vcenter_vm_snapshot,
        )

    def deploy_clone_from_vm(
        self,
        si,
        logger,
        session,
        data_holder,
        app_resource_model,
        vcenter_data_model,
        reservation_id,
        cancellation_context,
    ):
        """
        deploy Cloned VM From VM Command, will deploy vm from another vm

        :param cancellation_context:
        :param reservation_id:
        :param si:
        :param logger:
        :type data_holder:
        :type vcenter_data_model:
        :rtype DeployAppResult:
        :return:
        """
        template_resource_model = data_holder.template_resource_model
        return self._deploy_a_clone(
            si,
            logger,
            session,
            data_holder.app_name,
            template_resource_model.vcenter_vm,
            template_resource_model,
            app_resource_model,
            vcenter_data_model,
            reservation_id,
            cancellation_context,
        )

    def deploy_from_template(
        self,
        si,
        logger,
        session,
        data_holder,
        app_resource_model,
        vcenter_data_model,
        reservation_id,
        cancellation_context,
    ):
        """
        :param cancellation_context:
        :param reservation_id:
        :param si:
        :param logger:
        :type data_holder: DeployFromTemplateDetails
        :type vcenter_data_model
        :rtype DeployAppResult:
        :return:
        """
        template_resource_model = data_holder.template_resource_model
        return self._deploy_a_clone(
            si,
            logger,
            session,
            data_holder.app_name,
            template_resource_model.vcenter_template,
            template_resource_model,
            app_resource_model,
            vcenter_data_model,
            reservation_id,
            cancellation_context,
        )

    def _deploy_a_clone(
        self,
        si,
        logger,
        session,
        app_name,
        template_name,
        deploy_params,
        app_resource_model,
        vcenter_data_model,
        reservation_id,
        cancellation_context,
        snapshot="",
    ):
        """
        :rtype DeployAppResult:
        """
        # generate unique name
        vm_name = self.name_generator(app_name, reservation_id)

        VCenterDetailsFactory.set_deplyment_vcenter_params(
            vcenter_resource_model=vcenter_data_model, deploy_params=deploy_params
        )

        template_name = VMLocation.combine(
            [deploy_params.default_datacenter, template_name]
        )

        password = (
            session.DecryptPassword(app_resource_model.password).Value
            if app_resource_model.password
            else None
        )

        params = self.pv_service.CloneVmParameters(
            si=si,
            template_name=template_name,
            vm_name=vm_name,
            vm_folder=deploy_params.vm_location,
            datastore_name=deploy_params.vm_storage,
            cluster_name=deploy_params.vm_cluster,
            resource_pool=deploy_params.vm_resource_pool,
            power_on=False,
            snapshot=snapshot,
            customization_spec=deploy_params.customization_spec,
            hostname=deploy_params.hostname,
            password=password,
            private_ip=deploy_params.private_ip,
            cpu=deploy_params.cpu,
            ram=deploy_params.ram,
            hdd=deploy_params.hdd,
        )

        if cancellation_context.is_cancelled:
            raise Exception("Action 'Clone VM' was cancelled.")

        try:
            clone_vm_result = self.pv_service.clone_vm(
                clone_params=params,
                logger=logger,
                cancellation_context=cancellation_context,
            )
        except Exception:
            self.folder_manager.delete_folder_if_empty(
                si=si,
                folder_full_path=params.vm_folder,
                logger=logger,
            )
            raise

        if clone_vm_result.error:
            raise Exception(clone_vm_result.error)

        # remove a new created vm due to cancellation
        if cancellation_context.is_cancelled:
            self.pv_service.destroy_vm(vm=clone_vm_result.vm, logger=logger)

            self.folder_manager.delete_folder_if_empty(
                si=si,
                folder_full_path=params.vm_folder,
                logger=logger,
            )

            if clone_vm_result.customization_spec:
                self.pv_service.delete_customization_spec(
                    si=si, name=clone_vm_result.customization_spec
                )

            raise Exception("Action 'Clone VM' was cancelled.")

        vm_details_data = self._safely_get_vm_details(
            clone_vm_result.vm, vm_name, vcenter_data_model, deploy_params, logger
        )

        deployed_app_attrs = []

        if clone_vm_result.user is not None:
            logger.debug("Username is: {}".format(clone_vm_result.user))
            deployed_app_attrs.append(Attribute("User", clone_vm_result.user))

        if clone_vm_result.password is not None:
            deployed_app_attrs.append(Attribute("Password", clone_vm_result.password))

        if clone_vm_result.vm.guest.hostName is not None:
            deployed_app_attrs.append(
                Attribute("System Name", clone_vm_result.vm.guest.hostName)
            )

        return DeployAppResult(
            vmName=vm_name,
            vmUuid=clone_vm_result.vm.summary.config.uuid,
            vmDetailsData=vm_details_data,
            deployedAppAttributes=deployed_app_attrs,
            deployedAppAdditionalData={
                "ip_regex": deploy_params.ip_regex,
                "refresh_ip_timeout": deploy_params.refresh_ip_timeout,
                "auto_power_off": convert_to_bool(deploy_params.auto_power_off),
                "auto_delete": convert_to_bool(deploy_params.auto_delete),
                VM_CUSTOMIZATION_SPEC_CUSTOM_PARAM: clone_vm_result.customization_spec,
            },
        )

    def deploy_from_image(
        self,
        si,
        logger,
        session,
        vcenter_data_model,
        data_holder,
        resource_context,
        reservation_id,
        cancellation_context,
    ):
        vm_name = self.name_generator(data_holder.app_name, reservation_id)

        connection_details = ResourceConnectionDetailsRetriever.get_connection_details(
            session=session,
            vcenter_resource_model=vcenter_data_model,
            resource_context=resource_context,
        )

        VCenterDetailsFactory.set_deplyment_vcenter_params(
            vcenter_resource_model=vcenter_data_model,
            deploy_params=data_holder.image_params,
        )

        image_params = self._get_deploy_image_params(
            data_holder.image_params, connection_details, vm_name
        )

        vm_path = f"{image_params.datacenter}/{image_params.vm_folder}"

        if cancellation_context.is_cancelled:
            self.folder_manager.delete_folder_if_empty(
                si=si,
                folder_full_path=vm_path,
                logger=logger,
            )
            raise Exception("Action 'Deploy from image' was cancelled.")

        try:
            self.ovf_service.deploy_image(vcenter_data_model, image_params, logger)
        except Exception:
            self.folder_manager.delete_folder_if_empty(
                si=si,
                folder_full_path=vm_path,
                logger=logger,
            )
            raise

        vm = self.pv_service.find_vm_by_name(si, vm_path, vm_name)

        if vm:
            # remove a new created vm due to cancellation
            if cancellation_context.is_cancelled:
                self.pv_service.destroy_vm(vm=vm, logger=logger)

                self.folder_manager.delete_folder_if_empty(
                    si=si,
                    folder_full_path=vm_path,
                    logger=logger,
                )

                raise Exception("Action 'Deploy from image' was cancelled.")

            try:
                self.pv_service.reconfigure_vm(
                    vm=vm,
                    cpu=image_params.cpu,
                    ram=image_params.ram,
                    hdd=image_params.hdd,
                    logger=logger,
                )
            except ReconfigureVMException:
                raise
            except Exception as e:
                logger.error("error reconfiguring deployed VM: {0}".format(e))
                raise Exception(
                    "Error has occurred while reconfiguring deployed VM, please look at the log for more info."
                )

            if cancellation_context.is_cancelled:
                self.pv_service.destroy_vm(vm=vm, logger=logger)

                if vm_path:
                    self.folder_manager.delete_folder_if_empty(
                        si=si,
                        folder_full_path=vm_path,
                        logger=logger,
                    )

                raise Exception("Action 'Deploy from image' was cancelled.")

            vm_details_data = self._safely_get_vm_details(
                vm, vm_name, vcenter_data_model, data_holder.image_params, logger
            )

            additional_data = {
                "ip_regex": data_holder.image_params.ip_regex,
                "refresh_ip_timeout": data_holder.image_params.refresh_ip_timeout,
                "auto_power_off": convert_to_bool(
                    data_holder.image_params.auto_power_off
                ),
                "auto_delete": convert_to_bool(data_holder.image_params.auto_delete),
            }

            return DeployAppResult(
                vmName=vm_name,
                vmUuid=vm.config.uuid,
                vmDetailsData=vm_details_data,
                deployedAppAdditionalData=additional_data,
            )

        self.folder_manager.delete_folder_if_empty(
            si=si,
            folder_full_path=vm_path,
            logger=logger,
        )

        raise Exception(
            "the deployed vm from image({0}/{1}) could not be found".format(
                vm_path, vm_name
            )
        )

    def _safely_get_vm_details(self, vm, vm_name, vcenter_model, deploy_model, logger):
        data = None
        try:
            data = self.vm_details_provider.create(
                vm=vm,
                name=vm_name,
                reserved_networks=vcenter_model.reserved_networks,
                ip_regex=deploy_model.ip_regex,
                deployment_details_provider=DeploymentDetailsProviderFromTemplateModel(
                    deploy_model
                ),
                wait_for_ip=deploy_model.wait_for_ip,
                logger=logger,
            )
        except Exception:
            logger.error(
                "Error getting vm details for '{0}': {1}".format(
                    vm_name, traceback.format_exc()
                )
            )
        return data

    @staticmethod
    def _get_deploy_image_params(data_holder, host_info, vm_name):
        """
        :type data_holder: models.vCenterVMFromImageResourceModel.vCenterVMFromImageResourceModel
        """
        image_params = OvfImageParams()
        if (
            hasattr(data_holder, "vcenter_image_arguments")
            and data_holder.vcenter_image_arguments
        ):
            image_params.user_arguments = data_holder.vcenter_image_arguments
        image_params.vm_folder = data_holder.vm_location.replace(
            data_holder.default_datacenter + "/", ""
        )
        image_params.cluster = data_holder.vm_cluster
        image_params.resource_pool = data_holder.vm_resource_pool
        image_params.connectivity = host_info
        image_params.vm_name = vm_name
        image_params.datastore = data_holder.vm_storage
        image_params.datacenter = data_holder.default_datacenter
        image_params.image_url = data_holder.vcenter_image
        image_params.power_on = False
        image_params.vcenter_name = data_holder._vcenter_name
        image_params.cpu = data_holder.cpu
        image_params.ram = data_holder.ram
        image_params.hdd = data_holder.hdd

        return image_params


class DeploymentDetailsProviderFromTemplateModel(object):
    def __init__(self, template_resource_model):
        self.model = template_resource_model

    def get_details(self):
        """
        :rtype list[VmDataField]
        """
        data = []
        if isinstance(self.model, vCenterCloneVMFromVMResourceModel):
            data.append(
                VmDetailsProperty(key="Cloned VM Name", value=self.model.vcenter_vm)
            )

        if isinstance(self.model, VCenterDeployVMFromLinkedCloneResourceModel):
            template = self.model.vcenter_vm
            snapshot = self.model.vcenter_vm_snapshot
            data.append(
                VmDetailsProperty(
                    key="Cloned VM Name",
                    value="{0} (snapshot: {1})".format(template, snapshot),
                )
            )

        if isinstance(self.model, vCenterVMFromImageResourceModel):
            data.append(
                VmDetailsProperty(
                    key="Base Image Name", value=self.model.vcenter_image.split("/")[-1]
                )
            )

        if isinstance(self.model, vCenterVMFromTemplateResourceModel):
            data.append(
                VmDetailsProperty(
                    key="Template Name", value=self.model.vcenter_template
                )
            )

        return data
