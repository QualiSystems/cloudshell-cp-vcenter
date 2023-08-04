from unittest.mock import Mock

from cloudshell.cp.vcenter.constants import SHELL_NAME
from cloudshell.cp.vcenter.resource_config import ShutdownMethod, VCenterResourceConfig

RESOURCE_NAME = "vcenter"
RESOURCE_FAMILY = "CS_CloudProvider"
RESOURCE_ADDRESS = "localhost"
USER = "user name"
PASSWORD = "password"
DEFAULT_DATACENTER = "default datacenter"
DEFAULT_DV_SWITCH = "default dvSwitch"
HOLDING_NETWORK = "holding network"
VM_CLUSTER = "vm cluster"
VM_RESOURCE_POOL = "vm resource pool"
VM_STORAGE = "vm storage"
SAVED_SANDBOX_STORAGE = "saved sandbox storage"
BEHAVIOR_DURING_SAVE = "behavior during save"
VM_LOCATION = "vm location"
SHUTDOWN_METHOD = "soft"
EXPECTED_SHUTDOWN_METHOD = ShutdownMethod.SOFT
OVF_TOOL_PATH = "ovf tool path"
RESERVED_NETWORKS = "10.1.0.0/24;10.1.1.0/24"
EXPECTED_RESERVED_NETWORKS = ["10.1.0.0/24", "10.1.1.0/24"]
EXECUTION_SERVER_SELECTOR = "Execution Server Selector"
PROMISCUOUS_MODE = "true"
EXPECTED_PROMISCUOUS_MODE = True
FORGED_TRANSMITS = "true"
EXPECTED_FORGED_TRANSMITS = True
MAC_ADDRESS_CHANGES = "false"
EXPECTED_MAC_ADDRESS_CHANGES = False
ENABLE_TAGS = "true"
EXPECTED_ENABLE_TAGS = True


def test_resource_config(resource_command_context, cs_api):
    a_name = VCenterResourceConfig.ATTR_NAMES
    get_full_a_name = lambda n: f"{SHELL_NAME}.{n}"  # noqa: E731
    resource_command_context.resource.name = RESOURCE_NAME
    resource_command_context.resource.family = RESOURCE_FAMILY
    resource_command_context.resource.address = RESOURCE_ADDRESS
    resource_command_context.resource.attributes.update(
        {
            get_full_a_name(a_name.user): USER,
            get_full_a_name(a_name.password): PASSWORD,
            get_full_a_name(a_name.default_datacenter): DEFAULT_DATACENTER,
            get_full_a_name(a_name.default_dv_switch): DEFAULT_DV_SWITCH,
            get_full_a_name(a_name.holding_network): HOLDING_NETWORK,
            get_full_a_name(a_name.vm_cluster): VM_CLUSTER,
            get_full_a_name(a_name.vm_resource_pool): VM_RESOURCE_POOL,
            get_full_a_name(a_name.vm_storage): VM_STORAGE,
            get_full_a_name(a_name.saved_sandbox_storage): SAVED_SANDBOX_STORAGE,
            get_full_a_name(a_name.behavior_during_save): BEHAVIOR_DURING_SAVE,
            get_full_a_name(a_name.vm_location): VM_LOCATION,
            get_full_a_name(a_name.shutdown_method): SHUTDOWN_METHOD,
            get_full_a_name(a_name.ovf_tool_path): OVF_TOOL_PATH,
            get_full_a_name(a_name.reserved_networks): RESERVED_NETWORKS,
            get_full_a_name(
                a_name.execution_server_selector
            ): EXECUTION_SERVER_SELECTOR,
            get_full_a_name(a_name.promiscuous_mode): PROMISCUOUS_MODE,
            get_full_a_name(a_name.forged_transmits): FORGED_TRANSMITS,
            get_full_a_name(a_name.mac_changes): MAC_ADDRESS_CHANGES,
            get_full_a_name(a_name.enable_tags): ENABLE_TAGS,
        }
    )
    conf = VCenterResourceConfig.from_context(resource_command_context, cs_api)

    assert conf.name == RESOURCE_NAME
    assert conf.family_name == RESOURCE_FAMILY
    assert conf.address == RESOURCE_ADDRESS
    assert conf.user == USER
    assert conf.password == PASSWORD
    assert conf.default_datacenter == DEFAULT_DATACENTER
    assert conf.default_dv_switch == DEFAULT_DV_SWITCH
    assert conf.holding_network == HOLDING_NETWORK
    assert conf.vm_cluster == VM_CLUSTER
    assert conf.vm_resource_pool == VM_RESOURCE_POOL
    assert conf.vm_storage == VM_STORAGE
    assert conf.saved_sandbox_storage == SAVED_SANDBOX_STORAGE
    assert conf.behavior_during_save == BEHAVIOR_DURING_SAVE
    assert conf.vm_location == VM_LOCATION
    assert conf.shutdown_method == EXPECTED_SHUTDOWN_METHOD
    assert conf.ovf_tool_path == OVF_TOOL_PATH
    assert conf.reserved_networks == EXPECTED_RESERVED_NETWORKS
    assert conf.promiscuous_mode == EXPECTED_PROMISCUOUS_MODE
    assert conf.forged_transmits == EXPECTED_FORGED_TRANSMITS
    assert conf.mac_changes == EXPECTED_MAC_ADDRESS_CHANGES
    assert conf.enable_tags == EXPECTED_ENABLE_TAGS


def test_from_cs_resource_details(cs_api):
    a_name = VCenterResourceConfig.ATTR_NAMES
    get_full_a_name = lambda n: f"{SHELL_NAME}.{n}"  # noqa: E731
    r_attrs = {
        get_full_a_name(a_name.user): USER,
        get_full_a_name(a_name.password): PASSWORD,
        get_full_a_name(a_name.default_datacenter): DEFAULT_DATACENTER,
        get_full_a_name(a_name.default_dv_switch): DEFAULT_DV_SWITCH,
        get_full_a_name(a_name.holding_network): HOLDING_NETWORK,
        get_full_a_name(a_name.vm_cluster): VM_CLUSTER,
        get_full_a_name(a_name.vm_resource_pool): VM_RESOURCE_POOL,
        get_full_a_name(a_name.vm_storage): VM_STORAGE,
        get_full_a_name(a_name.saved_sandbox_storage): SAVED_SANDBOX_STORAGE,
        get_full_a_name(a_name.behavior_during_save): BEHAVIOR_DURING_SAVE,
        get_full_a_name(a_name.vm_location): VM_LOCATION,
        get_full_a_name(a_name.shutdown_method): SHUTDOWN_METHOD,
        get_full_a_name(a_name.ovf_tool_path): OVF_TOOL_PATH,
        get_full_a_name(a_name.reserved_networks): RESERVED_NETWORKS,
        get_full_a_name(a_name.execution_server_selector): EXECUTION_SERVER_SELECTOR,
        get_full_a_name(a_name.promiscuous_mode): PROMISCUOUS_MODE,
        get_full_a_name(a_name.forged_transmits): FORGED_TRANSMITS,
        get_full_a_name(a_name.mac_changes): MAC_ADDRESS_CHANGES,
        get_full_a_name(a_name.enable_tags): ENABLE_TAGS,
    }
    r_attrs = [Mock(Name=k, Value=v) for k, v in r_attrs.items()]

    details = Mock(
        Name=RESOURCE_NAME,
        ResourceModelName=SHELL_NAME,
        ResourceFamilyName=RESOURCE_FAMILY,
        Address=RESOURCE_ADDRESS,
        ResourceAttributes=r_attrs,
    )

    conf = VCenterResourceConfig.from_cs_resource_details(details, cs_api)

    assert conf.name == RESOURCE_NAME
    assert conf.family_name == RESOURCE_FAMILY
    assert conf.address == RESOURCE_ADDRESS
    assert conf.user == USER
    assert conf.password == PASSWORD
    assert conf.default_datacenter == DEFAULT_DATACENTER
    assert conf.default_dv_switch == DEFAULT_DV_SWITCH
    assert conf.holding_network == HOLDING_NETWORK
    assert conf.vm_cluster == VM_CLUSTER
    assert conf.vm_resource_pool == VM_RESOURCE_POOL
    assert conf.vm_storage == VM_STORAGE
    assert conf.saved_sandbox_storage == SAVED_SANDBOX_STORAGE
    assert conf.behavior_during_save == BEHAVIOR_DURING_SAVE
    assert conf.vm_location == VM_LOCATION
    assert conf.shutdown_method == EXPECTED_SHUTDOWN_METHOD
    assert conf.ovf_tool_path == OVF_TOOL_PATH
    assert conf.reserved_networks == EXPECTED_RESERVED_NETWORKS
    assert conf.promiscuous_mode == EXPECTED_PROMISCUOUS_MODE
    assert conf.forged_transmits == EXPECTED_FORGED_TRANSMITS
    assert conf.mac_changes == EXPECTED_MAC_ADDRESS_CHANGES
    assert conf.enable_tags == EXPECTED_ENABLE_TAGS
