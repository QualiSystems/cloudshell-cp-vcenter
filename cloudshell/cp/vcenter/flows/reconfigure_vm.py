from logging import Logger

from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.handlers.config_spec_handler import ConfigSpecHandler
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


def reconfigure_vm(
    vcenter_client: VCenterAPIClient,
    resource_conf: VCenterResourceConfig,
    deployed_app: BaseVCenterDeployedApp,
    cpu: str,
    ram: str,
    hdd: str,
    logger: Logger,
):
    logger.info("Reconfiguring VM...")
    dc = vcenter_client.get_dc(resource_conf.default_datacenter)
    dc = DcHandler(dc)
    vm = dc.get_vm_by_uuid(deployed_app.vmdetails.uid, vcenter_client)
    config_spec = ConfigSpecHandler.from_strings(cpu, ram, hdd)
    vm.reconfigure_vm(config_spec, logger)
