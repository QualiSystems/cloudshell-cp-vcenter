import logging

import attr

from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.si_handler import CustomSpecNotFound, SiHandler
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import ShutdownMethod, VCenterResourceConfig

logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True)
class VCenterPowerFlow:
    _si: SiHandler
    _deployed_app: BaseVCenterDeployedApp
    _resource_config: VCenterResourceConfig

    def _get_vm(self) -> VmHandler:
        logger.info(f"Getting VM by its UUID {self._deployed_app.vmdetails.uid}")
        dc = DcHandler.get_dc(self._resource_config.default_datacenter, self._si)
        return dc.get_vm_by_uuid(self._deployed_app.vmdetails.uid)

    def power_on(self):
        vm = self._get_vm()

        logger.info(f"Powering On the {vm}")
        spec_name = vm.name
        spec = None
        try:
            spec = self._si.get_customization_spec(spec_name)
        except CustomSpecNotFound:
            logger.info(f"No VM Customization Spec found, powering on the {vm}")
        else:
            logger.info(f"Adding Customization Spec to the {vm}")
            vm.add_customization_spec(spec)

        powered_time = vm.power_on()

        if spec:
            vm.wait_for_customization_ready(powered_time)
            self._si.delete_customization_spec(spec_name)

    def power_off(self):
        vm = self._get_vm()
        logger.info(f"Powering Off {vm}")
        soft = self._resource_config.shutdown_method is ShutdownMethod.SOFT
        vm.power_off(soft)
