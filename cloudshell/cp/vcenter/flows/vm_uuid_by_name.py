from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


def get_vm_uuid_by_name(
    vcenter_client: VCenterAPIClient, resource_conf: VCenterResourceConfig, vm_name: str
) -> str:
    dc = vcenter_client.get_dc(resource_conf.default_datacenter)
    dc = DcHandler(dc)
    vm = dc.get_vm_by_name(vm_name, vcenter_client)
    return vm.uuid
