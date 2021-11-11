from __future__ import annotations

import os
from typing import TYPE_CHECKING, Iterable
from urllib.request import urlopen

import attr

from cloudshell.cp.vcenter.exceptions import InvalidAttributeException
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler

if TYPE_CHECKING:
    from logging import Logger

    from cloudshell.cp.vcenter.api_client import VCenterAPIClient
    from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


BEHAVIOURS_DURING_SAVE = ("Remain Powered On", "Power Off")


@attr.s(auto_attribs=True)
class ValidationActions:
    _vcenter_client: VCenterAPIClient
    _resource_conf: VCenterResourceConfig
    _logger: Logger

    def validate_resource_conf(self):
        self._logger.info("Validating resource config ...")
        conf = self._resource_conf
        _is_not_empty(conf.address, "address")
        _is_not_empty(conf.user, conf.ATTR_NAMES.user)
        _is_not_empty(conf.password, conf.ATTR_NAMES.password)
        _is_not_empty(conf.default_datacenter, conf.ATTR_NAMES.default_datacenter)
        _is_not_empty(conf.vm_location, conf.ATTR_NAMES.vm_location)
        _is_value_in(
            conf.behavior_during_save,
            BEHAVIOURS_DURING_SAVE,
            conf.ATTR_NAMES.behavior_during_save,
        )

    def validate_connection(self):
        self._logger.info("Validating connection to the vCenter ...")
        _ = self._vcenter_client._si  # try to connect

    def validate_resource_conf_dc_objects(self):
        self._logger.info("Validating resource config objects on the vCenter ...")

        conf = self._resource_conf
        dc = self._vcenter_client.get_dc(conf.default_datacenter)
        dc_handler = DcHandler(dc)
        dc_handler.get_network(conf.holding_network)
        if conf.vm_location:
            self._vcenter_client.get_folder(conf.vm_location, dc.vmFolder)
        if conf.vm_cluster:
            self._vcenter_client.get_cluster(conf.vm_cluster, dc)
        if conf.vm_storage:
            self._vcenter_client.get_storage(conf.vm_storage, dc)
        if conf.saved_sandbox_storage:
            self._vcenter_client.get_storage(conf.saved_sandbox_storage, dc)
        if conf.default_dv_switch:
            self._vcenter_client.get_dv_switch(conf.default_dv_switch, dc)

    def validate_deploy_app_dc_objects(self, deploy_app):
        self._logger.info("Validating deploy app objects on the vCenter ...")

        dc = self._vcenter_client.get_dc(self._resource_conf.default_datacenter)
        if deploy_app.vm_location:
            self._vcenter_client.get_folder(deploy_app.vm_location, dc.vmFolder)
        if deploy_app.vm_cluster:
            self._vcenter_client.get_cluster(deploy_app.vm_cluster, dc)
        if deploy_app.vm_storage:
            self._vcenter_client.get_storage(deploy_app.vm_storage, dc)

    def validate_deploy_app(self, deploy_app):
        self._logger.info("Validating deploy app ...")

        conf = self._resource_conf
        _one_is_not_empty(
            [deploy_app.vm_cluster, conf.vm_cluster],
            conf.ATTR_NAMES.vm_cluster,
        )
        _one_is_not_empty(
            [deploy_app.vm_storage, conf.vm_storage],
            conf.ATTR_NAMES.vm_storage,
        )
        _one_is_not_empty(
            [deploy_app.vm_location, conf.vm_location],
            conf.ATTR_NAMES.vm_location,
        )

    def validate_deploy_app_from_vm(self, deploy_app):
        self._logger.info("Validating deploy app from VM ...")
        _is_not_empty(deploy_app.vcenter_vm, deploy_app.ATTR_NAMES.vcenter_vm)

    def validate_deploy_app_from_template(self, deploy_app):
        self._logger.info("Validating deploy app from Template ...")
        _is_not_empty(
            deploy_app.vcenter_template, deploy_app.ATTR_NAMES.vcenter_template
        )

    def validate_deploy_app_from_clone(self, deploy_app):
        self._logger.info("Validating deploy app from Linked Clone ...")
        _is_not_empty(deploy_app.vcenter_vm, deploy_app.ATTR_NAMES.vcenter_vm)
        _is_not_empty(
            deploy_app.vcenter_vm_snapshot, deploy_app.ATTR_NAMES.vcenter_vm_snapshot
        )

    def validate_deploy_app_from_image(self, deploy_app):
        self._logger.info("Validating deploy app from Image ...")
        _is_not_empty(deploy_app.vcenter_image, deploy_app.ATTR_NAMES.vcenter_image)
        _is_valid_url(deploy_app.vcenter_image, deploy_app.ATTR_NAMES.vcenter_image)

    def validate_ovf_tool(self, ovf_tool_path):
        self._logger.info("Validating OVF Tool ...")
        _is_not_empty(ovf_tool_path, self._resource_conf.ATTR_NAMES.ovf_tool_path)
        _is_valid_url(ovf_tool_path, self._resource_conf.ATTR_NAMES.ovf_tool_path)


def _is_valid_url(url: str, attr_name: str):
    try:
        urlopen(url)
    except Exception:
        if os.path.isfile(url):
            return True
    else:
        return True

    raise InvalidAttributeException(f"{attr_name} is invalid. Unable to access {url}")


def _is_not_empty(value: str, attr_name: str):
    if not value:
        raise InvalidAttributeException(f"{attr_name} cannot be empty")


def _is_value_in(value: str, expected_values: Iterable[str], attr_name: str):
    if value not in expected_values:
        raise InvalidAttributeException(
            f"{attr_name} should be one of the {list(expected_values)}"
        )


def _one_is_not_empty(values: list, attr_name: str):
    if not any(values):
        raise InvalidAttributeException(f"{attr_name} cannot be empty")
