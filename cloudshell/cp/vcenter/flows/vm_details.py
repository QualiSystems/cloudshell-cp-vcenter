from logging import Logger

from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.flows import AbstractVMDetailsFlow
from cloudshell.cp.core.request_actions.models import VmDetailsData

from cloudshell.cp.vcenter.actions.vm_details import VMDetailsActions
from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


class VCenterGetVMDetailsFlow(AbstractVMDetailsFlow):
    def __init__(
        self,
        vcenter_client: VCenterAPIClient,
        resource_conf: VCenterResourceConfig,
        cancellation_manager: CancellationContextManager,
        logger: Logger,
    ):
        super().__init__(logger)
        self._resource_conf = resource_conf
        self._cancellation_manager = cancellation_manager
        self._vcenter_client = vcenter_client

    def _get_vm_details(self, deployed_app: BaseVCenterDeployedApp) -> VmDetailsData:
        dc = self._vcenter_client.get_dc(self._resource_conf.default_datacenter)
        vm = self._vcenter_client.get_vm(deployed_app.vmdetails.uid, dc)
        return VMDetailsActions(
            self._vcenter_client,
            self._resource_conf,
            self._logger,
            self._cancellation_manager,
        ).create(vm, deployed_app)
