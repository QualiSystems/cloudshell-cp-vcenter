from logging import Logger

import attr

from cloudshell.cp.core.request_actions.models import DeployedApp

from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig
from cloudshell.cp.vcenter.utils.cached_property import cached_property


@attr.s(auto_attribs=True)
class VCenterPowerFlow:
    _vcenter_client: VCenterAPIClient
    _deployed_app: DeployedApp
    _resource_config: VCenterResourceConfig
    _logger: Logger

    @cached_property
    def _vm(self):
        self._logger.info(
            f"Getting VM by its UID {self._deployed_app.vmdetails.uid} ..."
        )
        dc = self._vcenter_client.get_dc(self._resource_config.default_datacenter)
        return self._vcenter_client.get_vm(self._deployed_app.vmdetails.uid, dc)

    def power_on(self):
        self._logger.info(f"Powering On VM {self._vm} ...")
        self._vcenter_client.power_on_vm(self._vm)

    def power_off(self):
        self._logger.info(f"Powering Off VM {self._vm} ...")
        soft = self._resource_config.shutdown_method.lower() == "soft"
        self._vcenter_client.power_off_vm(self._vm, soft)
