from cloudshell.cp.vcenter.actions.validation import ValidationActions
from cloudshell.cp.vcenter.actions.vm_details import VMDetailsActions
from cloudshell.cp.vcenter.flows.deploy_vm.base_flow import (
    AbstractVCenterDeployVMFromTemplateFlow,
)


class VCenterDeployVMFromLinkedCloneFlow(AbstractVCenterDeployVMFromTemplateFlow):
    def _get_vm_template(self, deploy_app, dc):
        """Get VM template to clone VM from."""
        return self._vcenter_client.get_vm_by_name(name=deploy_app.vcenter_vm, dc=dc)

    def _validate_deploy_app(self, deploy_app):
        """Validate Deploy App before deployment."""
        super()._validate_deploy_app(deploy_app)

        validation_actions = ValidationActions(
            vcenter_client=self._vcenter_client,
            resource_conf=self._resource_config,
            logger=self._logger,
        )
        validation_actions.validate_deploy_app_from_clone(deploy_app)

    def _get_vm_snapshot(self, deploy_app, vm_template):
        return self._vcenter_client.get_vm_snapshot(
            snapshot_name=deploy_app.vcenter_vm_snapshot, vm=vm_template
        )

    def _prepare_vm_details_data(self, deployed_vm, deploy_app):
        """Prepare CloudShell VM Details model."""
        vm_details_actions = VMDetailsActions(
            resource_conf=self._resource_config,
            vcenter_client=self._vcenter_client,
            cancellation_manager=self._cancellation_manager,
            logger=self._logger,
        )

        return vm_details_actions.prepare_vm_from_clone_details(
            virtual_machine=deployed_vm,
            deploy_app=deploy_app,
        )
