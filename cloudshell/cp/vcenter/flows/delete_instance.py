from logging import Logger

from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


def delete_instance(
    vcenter_client: VCenterAPIClient,
    deployed_app: BaseVCenterDeployedApp,
    resource_conf: VCenterResourceConfig,
    logger: Logger,
):
    dc = vcenter_client.get_dc(resource_conf.default_datacenter)
    vm = vcenter_client.get_vm(deployed_app.vmdetails.uid, dc)
    if vm:
        vcenter_client.delete_customization_spec(vm.name)
        vcenter_client.destroy_vm(vm)
    else:
        logger.info(f"Could not find the VM {deployed_app.vmdetails.uid}")

    # todo delete vm folder?
