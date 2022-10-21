from __future__ import annotations

from logging import Logger

from cloudshell.cp.vcenter.handlers.config_spec_handler import ConfigSpecHandler
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.vm_handler import VmNotFound
from cloudshell.cp.vcenter.models.deployed_app import (
    BaseVCenterDeployedApp,
    VMFromLinkedCloneDeployedApp,
)
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


def reconfigure_vm(
    resource_conf: VCenterResourceConfig,
    deployed_app: BaseVCenterDeployedApp,
    cpu: str | None,
    ram: str | None,
    hdd: str | None,
    logger: Logger,
):
    logger.info("Reconfiguring VM")
    si = SiHandler.from_config(resource_conf, logger)
    dc = DcHandler.get_dc(resource_conf.default_datacenter, si)
    vm = dc.get_vm_by_uuid(deployed_app.vmdetails.uid)
    config_spec = ConfigSpecHandler.from_strings(cpu, ram, hdd)
    _validate_if_change_linked_vm(deployed_app, dc, config_spec)
    vm.reconfigure_vm(config_spec, logger)


def _validate_if_change_linked_vm(
    deployed_app: BaseVCenterDeployedApp, dc: DcHandler, config_spec: ConfigSpecHandler
) -> None:
    if isinstance(deployed_app, VMFromLinkedCloneDeployedApp):
        try:
            source_vm = dc.get_vm_by_path(deployed_app.vcenter_vm)
        except VmNotFound:
            pass  # we cannot check if source VM is removed
        else:
            config_spec.validate_for_linked_vm(source_vm)
