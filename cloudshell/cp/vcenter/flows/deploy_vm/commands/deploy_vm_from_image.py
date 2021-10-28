from cloudshell.cp.core.rollback import RollbackCommand

from cloudshell.cp.vcenter.utils.ovf_tool import OVFToolScript
from cloudshell.cp.vcenter.utils.vm_location import prepare_path


class DeployVMFromImageCommand(RollbackCommand):
    def __init__(
        self,
        rollback_manager,
        cancellation_manager,
        vcenter_client,
        resource_conf,
        vcenter_image,
        vcenter_image_arguments,
        vm_name,
        vm_resource_pool,
        vm_storage,
        vm_folder,
        dc,
        logger,
    ):
        super().__init__(
            rollback_manager=rollback_manager, cancellation_manager=cancellation_manager
        )
        self._logger = logger
        self._vcenter_client = vcenter_client
        self._resource_conf = resource_conf
        self._vcenter_image = vcenter_image
        self._vcenter_image_arguments = vcenter_image_arguments
        self._vm_name = vm_name
        self._vm_resource_pool = vm_resource_pool
        self._vm_storage = vm_storage
        self._vm_folder = vm_folder
        self._dc = dc
        self._logger = logger
        self._deployed_vm = None

    def _execute(self):
        ovf_tool_script = OVFToolScript(
            ovf_tool_path=self._resource_conf.ovf_tool_path,
            datacenter=self._resource_conf.default_datacenter,
            vm_cluster=self._resource_conf.vm_cluster,
            vm_storage=self._vm_storage,
            vm_folder=self._vm_folder,
            vm_resource_pool=self._vm_resource_pool,
            vm_name=self._vm_name,
            vcenter_image=self._vcenter_image,
            custom_args=self._vcenter_image_arguments,
            vcenter_user=self._resource_conf.user,
            vcenter_password=self._resource_conf.password,
            vcenter_host=self._resource_conf.address,
            logger=self._logger,
        )

        ovf_tool_script.run()

        vm = self._vcenter_client.get_vm_by_name(
            name=prepare_path(self._vm_folder, self._vm_name), dc=self._dc
        )

        self._deployed_vm = vm
        return vm

    def rollback(self):
        self._vcenter_client.destroy_vm(vm=self._deployed_vm)
