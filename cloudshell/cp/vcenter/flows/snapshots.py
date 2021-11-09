from __future__ import annotations

import json
from logging import Logger

import attr

from cloudshell.api.cloudshell_api import CloudShellAPISession

from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.exceptions import InvalidCommandParam
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler
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


@attr.s(auto_attribs=True)
class SnapshotFlow:
    _vcenter_client: VCenterAPIClient
    _resource_conf: VCenterResourceConfig
    _deployed_app: BaseVCenterDeployedApp
    _logger: Logger

    def _get_vm(self) -> VmHandler:
        dc = self._vcenter_client.get_dc(self._resource_conf.default_datacenter)
        dc = DcHandler(dc)
        return dc.get_vm_by_uuid(self._deployed_app.vmdetails.uid, self._vcenter_client)

    def get_snapshot_paths(self) -> str:
        vm = self._get_vm()
        paths = vm.get_snapshot_paths(self._logger)
        return json.dumps(paths)

    def save_snapshot(self, snapshot_name: str, dump_memory: str) -> str:
        _validate_dump_memory_param(dump_memory)
        vm = self._get_vm()
        dump_memory = dump_memory == "Yes"
        snapshot_path = vm.create_snapshot(snapshot_name, dump_memory, self._logger)
        return snapshot_path

    def restore_from_snapshot(
        self,
        cs_api: CloudShellAPISession,
        snapshot_path: str,
    ):
        vm = self._get_vm()
        vm.restore_from_snapshot(snapshot_path, self._logger)
        cs_api.SetResourceLiveStatus(self._deployed_app.name, "Offline", "Powered Off")
