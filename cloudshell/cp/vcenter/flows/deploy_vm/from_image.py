from cloudshell.cp.vcenter.actions.validation import ValidationActions
from cloudshell.cp.vcenter.actions.vm_details import VMDetailsActions
from cloudshell.cp.vcenter.flows.deploy_vm.base_flow import AbstractVCenterDeployVMFlow
from cloudshell.cp.vcenter.flows.deploy_vm.commands.deploy_vm_from_image import (
    DeployVMFromImageCommand,
)


class VCenterDeployVMFromImageFlow(AbstractVCenterDeployVMFlow):
    def _validate_deploy_app(self, deploy_app):
        """Validate Deploy App before deployment."""
        super()._validate_deploy_app(deploy_app)

        validation_actions = ValidationActions(
            vcenter_client=self._vcenter_client,
            resource_conf=self._resource_config,
            logger=self._logger,
        )
        validation_actions.validate_deploy_app_from_image(deploy_app)
        validation_actions.validate_ovf_tool(self._resource_config.ovf_tool_path)

    def _prepare_vm_details_data(self, deployed_vm, deploy_app):
        """Prepare CloudShell VM Details model."""
        vm_details_actions = VMDetailsActions(
            resource_conf=self._resource_config,
            vcenter_client=self._vcenter_client,
            cancellation_manager=self._cancellation_manager,
            logger=self._logger,
        )

        return vm_details_actions.prepare_vm_from_image_details(
            virtual_machine=deployed_vm,
            deploy_app=deploy_app,
        )

    def _create_vm(
        self, deploy_app, vm_name, vm_resource_pool, vm_storage, vm_folder, dc
    ):
        """Create VM on the vCenter."""
        # todo: check with defined "vm_resource_pool" in vCenter model
        vm_folder = self._prepare_vm_folder_path(deploy_app=deploy_app)

        return DeployVMFromImageCommand(
            rollback_manager=self._rollback_manager,
            cancellation_manager=self._cancellation_manager,
            vcenter_client=self._vcenter_client,
            resource_conf=self._resource_config,
            vcenter_image=deploy_app.vcenter_image,
            vcenter_image_arguments=deploy_app.vcenter_image_arguments,
            vm_name=vm_name,
            vm_resource_pool=deploy_app.vm_resource_pool
            or self._resource_config.vm_resource_pool,
            vm_storage=vm_storage.name,
            # todo: check if it will work with the nested folder folder1/folder2/folder3
            vm_folder=vm_folder,
            dc=dc,
            logger=self._logger,
        ).execute()
