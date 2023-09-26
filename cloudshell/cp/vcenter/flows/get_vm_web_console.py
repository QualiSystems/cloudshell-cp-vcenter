from __future__ import annotations

import logging

from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig
from cloudshell.cp.vcenter.utils.get_vm_web_console import get_vm_console_link
from cloudshell.cp.vcenter.utils.vm_console_link_attr import (
    set_deployed_app_vm_console_link_attr,
)

logger = logging.getLogger(__name__)


def get_vm_web_console(
    si: SiHandler,
    resource_conf: VCenterResourceConfig,
    deployed_app: BaseVCenterDeployedApp,
) -> str:
    logger.info("Get VM Web Console")
    dc = DcHandler.get_dc(resource_conf.default_datacenter, si)
    vm = dc.get_vm_by_uuid(deployed_app.vmdetails.uid)
    link = get_vm_console_link(resource_conf.address, si, vm)
    set_deployed_app_vm_console_link_attr(deployed_app, resource_conf, vm, si)
    return link
