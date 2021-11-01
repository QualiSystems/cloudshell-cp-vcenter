from logging import Logger

from cloudshell.cp.core.cancellation_manager import CancellationContextManager

from cloudshell.cp.vcenter.actions.vm_network import VMNetworkActions
from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


def refresh_ip(
    vcenter_client: VCenterAPIClient,
    deployed_app: BaseVCenterDeployedApp,
    resource_conf: VCenterResourceConfig,
    cancellation_manager: CancellationContextManager,
    logger: Logger,
):
    dc = vcenter_client.get_dc(resource_conf.default_datacenter)
    vm = vcenter_client.get_vm(deployed_app.vmdetails.uid, dc)
    default_net = vcenter_client.get_network(resource_conf.holding_network, dc)
    ip = VMNetworkActions(
        vcenter_client, resource_conf, logger, cancellation_manager
    ).get_vm_ip(vm, default_net, deployed_app.ip_regex, deployed_app.refresh_ip_timeout)
    if ip != deployed_app.private_ip:
        deployed_app.update_private_ip(deployed_app.name, ip)
