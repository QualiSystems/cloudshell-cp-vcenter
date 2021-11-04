from datetime import datetime
from logging import Logger

import attr

from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import ShutdownMethod, VCenterResourceConfig


@attr.s(auto_attribs=True)
class VCenterPowerFlow:
    _vcenter_client: VCenterAPIClient
    _deployed_app: BaseVCenterDeployedApp
    _resource_config: VCenterResourceConfig
    _logger: Logger

    def _get_vm(self) -> VmHandler:
        self._logger.info(f"Getting VM by its UID {self._deployed_app.vmdetails.uid}")
        dc = self._vcenter_client.get_dc(self._resource_config.default_datacenter)
        dc = DcHandler(dc)
        return dc.get_vm_by_uuid(self._deployed_app.vmdetails.uid, self._vcenter_client)

    def power_on(self):
        vm = self._get_vm()
        self._logger.info(f"Powering On {vm}")
        spec_name = self._deployed_app.customization_spec
        spec = self._vcenter_client.get_customization_spec(spec_name)

        if spec:
            self._logger.info(f"Adding Customization Spec to the {vm}")
            vm.add_customization_spec(spec, self._logger)
        else:
            self._logger.info(f"No VM Customization Spec found, powering on the {vm}")

        begin_time = datetime.now()
        vm.power_on(self._logger)

        if spec:
            vm.wait_for_customization_ready(
                self._vcenter_client, begin_time, self._logger
            )
            self._vcenter_client.delete_customization_spec(spec_name)

    def power_off(self):
        vm = self._get_vm()
        self._logger.info(f"Powering Off {vm}")
        soft = self._resource_config.shutdown_method is ShutdownMethod.SOFT
        vm.power_off(soft, self._logger)
