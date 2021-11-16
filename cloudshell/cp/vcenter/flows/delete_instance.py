from logging import Logger

from cloudshell.cp.core.reservation_info import ReservationInfo

from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import ShutdownMethod, VCenterResourceConfig
from cloudshell.cp.vcenter.utils.vm_helpers import get_vm_folder_path


def delete_instance(
    deployed_app: BaseVCenterDeployedApp,
    resource_conf: VCenterResourceConfig,
    reservation_info: ReservationInfo,
    logger: Logger,
):
    si = SiHandler.from_config(resource_conf, logger)
    dc = DcHandler.get_dc(resource_conf.default_datacenter, si)
    vm = dc.get_vm_by_uuid(deployed_app.vmdetails.uid)

    si.delete_customization_spec(vm.name)

    soft = resource_conf.shutdown_method is ShutdownMethod.SOFT
    vm.power_off(soft=soft, logger=logger)
    vm.delete(logger)

    path = get_vm_folder_path(
        deployed_app, resource_conf, reservation_info.reservation_id
    )
    folder = dc.get_vm_folder(path)
    folder.destroy(logger)
