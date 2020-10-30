from logging import Logger

from cloudshell.cp.vcenter.api.client import VCenterAPIClient
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig
from cloudshell.cp.vcenter.utils.cached_property import cached_property


class PowerFlow:
    def __init__(
        self,
        vcenter_client: VCenterAPIClient,
        deployed_app: BaseVCenterDeployedApp,
        resource_conf: VCenterResourceConfig,
        logger: Logger,
    ):
        self._vcenter_client = vcenter_client
        self._deployed_app = deployed_app
        self._resource_conf = resource_conf
        self._logger = logger

    @cached_property
    def _vm(self):
        dc = self._vcenter_client.get_dc(self._resource_conf.default_datacenter)
        return self._vcenter_client.get_vm(self._deployed_app.vmdetails.uid, dc)

    def power_on(self):
        self._vcenter_client.power_on_vm(self._vm)

    def power_off(self):
        soft = self._resource_conf.shutdown_method.lower() == "soft"
        self._vcenter_client.power_off_vm(self._vm, soft)
