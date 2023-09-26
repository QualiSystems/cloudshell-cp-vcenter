import attr

from cloudshell.shell.core.driver_context import AutoLoadDetails

from cloudshell.cp.vcenter.actions.validation import ValidationActions
from cloudshell.cp.vcenter.constants import DEPLOYED_APPS_FOLDER
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.vcenter_path import VcenterPath
from cloudshell.cp.vcenter.handlers.vcenter_tag_handler import VCenterTagsManager
from cloudshell.cp.vcenter.handlers.vsphere_sdk_handler import VSphereSDKHandler
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


@attr.s(auto_attribs=True)
class VCenterAutoloadFlow:
    _si: SiHandler
    _resource_config: VCenterResourceConfig

    def discover(self) -> AutoLoadDetails:
        validation_actions = ValidationActions(self._si, self._resource_config)
        validation_actions.validate_resource_conf()
        validation_actions.validate_resource_conf_dc_objects()

        dc = DcHandler.get_dc(self._resource_config.default_datacenter, self._si)
        deployed_apps_folder_path = VcenterPath(self._resource_config.vm_location)
        deployed_apps_folder_path.append(DEPLOYED_APPS_FOLDER)
        deployed_apps_folder = dc.get_or_create_vm_folder(deployed_apps_folder_path)

        vsphere_client = VSphereSDKHandler.from_config(
            resource_config=self._resource_config,
            reservation_info=None,
            si=self._si,
        )
        if vsphere_client is not None:
            vsphere_client.create_categories()
            tags = VCenterTagsManager.get_tags_created_by()
            vsphere_client.assign_tags(deployed_apps_folder, tags)

        return AutoLoadDetails([], [])
