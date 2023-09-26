from __future__ import annotations

import logging

from cloudshell.cp.vcenter.handlers.config_spec_handler import ConfigSpecHandler
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig

logger = logging.getLogger(__name__)


def reconfigure_vm(
    si: SiHandler,
    resource_conf: VCenterResourceConfig,
    deployed_app: BaseVCenterDeployedApp,
    cpu: str | None,
    ram: str | None,
    hdd: str | None,
):
    logger.info("Reconfiguring VM")
    dc = DcHandler.get_dc(resource_conf.default_datacenter, si)
    vm = dc.get_vm_by_uuid(deployed_app.vmdetails.uid)
    config_spec = ConfigSpecHandler.from_strings(cpu, ram, hdd)
    vm.reconfigure_vm(config_spec)
