from logging import Logger

from cloudshell.cp.core.cancellation_manager import CancellationContextManager

from cloudshell.cp.vcenter.actions.vm_network import VMNetworkActions
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


def refresh_ip(
    deployed_app: BaseVCenterDeployedApp,
    resource_conf: VCenterResourceConfig,
    cancellation_manager: CancellationContextManager,
    logger: Logger,
):
    si = SiHandler.from_config(resource_conf, logger)
    dc = DcHandler.get_dc(resource_conf.default_datacenter, si)
    vm = dc.get_vm_by_uuid(deployed_app.vmdetails.uid)
    default_net = dc.get_network(resource_conf.holding_network)
    ip = VMNetworkActions(resource_conf, logger, cancellation_manager).get_vm_ip(
        vm._entity,
        default_net._entity,
        deployed_app.ip_regex,
        deployed_app.refresh_ip_timeout,
    )
    if ip != deployed_app.private_ip:
        deployed_app.update_private_ip(deployed_app.name, ip)
