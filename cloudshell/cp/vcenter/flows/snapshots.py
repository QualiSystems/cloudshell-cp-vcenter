from logging import Logger

from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.exceptions import InvalidCommandParam
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


def _validate_dump_memory_param(dump_memory: str):
    expected_values = ("Yes", "No")
    if dump_memory not in ("Yes", "No"):
        raise InvalidCommandParam(
            param_name="save_memory",
            param_value=dump_memory,
            expected_values=expected_values,
        )


def save_snapshot(
    vcenter_client: VCenterAPIClient,
    resource_conf: VCenterResourceConfig,
    deployed_app: BaseVCenterDeployedApp,
    snapshot_name: str,
    dump_memory: str,
    logger: Logger,
) -> str:
    _validate_dump_memory_param(dump_memory)
    dc = vcenter_client.get_dc(resource_conf.default_datacenter)
    dc = DcHandler(dc)
    vm = dc.get_vm_by_uuid(deployed_app.vmdetails.uid, vcenter_client)
    dump_memory = dump_memory == "Yes"
    snapshot_path = vm.create_snapshot(snapshot_name, dump_memory, logger)
    return snapshot_path
