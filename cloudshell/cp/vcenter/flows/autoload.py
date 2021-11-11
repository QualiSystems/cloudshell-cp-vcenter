from logging import Logger

import attr

from cloudshell.shell.core.driver_context import AutoLoadDetails

from cloudshell.cp.vcenter.actions.validation import ValidationActions
from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


@attr.s(auto_attribs=True)
class VCenterAutoloadFlow:
    _resource_config: VCenterResourceConfig
    _vcenter_client: VCenterAPIClient
    _logger: Logger

    def discover(self) -> AutoLoadDetails:
        """Discover command."""
        validation_actions = ValidationActions(
            vcenter_client=self._vcenter_client,
            resource_conf=self._resource_config,
            logger=self._logger,
        )

        validation_actions.validate_resource_conf()
        validation_actions.validate_connection()
        validation_actions.validate_resource_conf_dc_objects()

        return AutoLoadDetails([], [])
