from cloudshell.shell.standards.core.resource_config_entities import (
    GenericResourceConfig,
    PasswordAttrRO,
    ResourceAttrRO,
    ResourceBoolAttrRO,
    ResourceListAttrRO,
)

from cloudshell.cp.vcenter.constants import SHELL_NAME


class ResourceAttrROShellName(ResourceAttrRO):
    def __init__(self, name, namespace=ResourceAttrRO.NAMESPACE.SHELL_NAME):
        super().__init__(name, namespace)


class VCenterAttributeNames:
    user = "User"
    password = "Password"
    default_datacenter = "Default Datacenter"
    default_dv_switch = "Default dvSwitch"
    holding_network = "Holding Network"
    vm_cluster = "VM Cluster"
    vm_resource_pool = "VM Resource Pool"
    vm_storage = "VM Storage"
    saved_sandbox_storage = "Saved Sandbox Storage"
    behavior_during_save = "Behavior during save"
    vm_location = "VM Location"
    shutdown_method = "Shutdown Method"
    ovf_tool_path = "OVF Tool Path"
    reserved_networks = "Reserved Networks"
    execution_server_selector = "Execution Server Selector"
    promiscuous_mode = "Promiscuous Mode"


class VCenterResourceConfig(GenericResourceConfig):
    ATTR_NAMES = VCenterAttributeNames

    user = ResourceAttrROShellName(ATTR_NAMES.user)
    password = PasswordAttrRO(ATTR_NAMES.password, PasswordAttrRO.NAMESPACE.SHELL_NAME)
    default_datacenter = ResourceAttrROShellName(ATTR_NAMES.default_datacenter)
    default_dv_switch = ResourceAttrROShellName(ATTR_NAMES.default_dv_switch)
    holding_network = ResourceAttrROShellName(ATTR_NAMES.holding_network)
    vm_cluster = ResourceAttrROShellName(ATTR_NAMES.vm_cluster)
    vm_resource_pool = ResourceAttrROShellName(ATTR_NAMES.vm_resource_pool)
    vm_storage = ResourceAttrROShellName(ATTR_NAMES.vm_storage)
    saved_sandbox_storage = ResourceAttrROShellName(ATTR_NAMES.saved_sandbox_storage)
    behavior_during_save = ResourceAttrROShellName(ATTR_NAMES.behavior_during_save)
    vm_location = ResourceAttrROShellName(ATTR_NAMES.vm_location)
    shutdown_method = ResourceAttrROShellName(ATTR_NAMES.shutdown_method)
    ovf_tool_path = ResourceAttrROShellName(ATTR_NAMES.ovf_tool_path)
    reserved_networks = ResourceListAttrRO(
        ATTR_NAMES.reserved_networks, ResourceListAttrRO.NAMESPACE.SHELL_NAME
    )
    execution_server_selector = ResourceAttrROShellName(
        ATTR_NAMES.execution_server_selector
    )
    promiscuous_mode = ResourceBoolAttrRO(
        ATTR_NAMES.promiscuous_mode, ResourceBoolAttrRO.NAMESPACE.SHELL_NAME
    )

    @classmethod
    def from_context(cls, context, shell_name=SHELL_NAME, api=None, supported_os=None):
        """Creates an instance of a Resource by given context.

        :param str shell_name: Shell Name
        :param list supported_os: list of supported OS
        :param cloudshell.shell.core.driver_context.ResourceCommandContext context:
        :param cloudshell.api.cloudshell_api.CloudShellAPISession api:
        :rtype: VCenterResourceConfig
        """
        return super(VCenterResourceConfig, cls).from_context(
            context=context, shell_name=shell_name, api=api, supported_os=supported_os
        )
