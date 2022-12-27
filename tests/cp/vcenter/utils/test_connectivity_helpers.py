from unittest.mock import Mock

import pytest

from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ConnectionModeEnum,
)

from cloudshell.cp.vcenter.handlers.vnic_handler import Vnic
from cloudshell.cp.vcenter.models.connectivity_action_model import (
    VcenterConnectivityActionModel,
)
from cloudshell.cp.vcenter.utils.connectivity_helpers import (
    generate_port_group_name,
    get_available_vnic,
    get_existed_port_group_name,
    is_correct_vnic,
    should_remove_port_group,
)


@pytest.fixture
def action_request():
    return {
        "connectionId": "96582265-2728-43aa-bc97-cefb2457ca44",
        "connectionParams": {
            "vlanId": "10-11",
            "mode": "Trunk",
            "vlanServiceAttributes": [
                {
                    "attributeName": "QnQ",
                    "attributeValue": "False",
                    "type": "vlanServiceAttribute",
                },
                {
                    "attributeName": "CTag",
                    "attributeValue": "",
                    "type": "vlanServiceAttribute",
                },
                {
                    "attributeName": "Port Group Name",
                    "attributeValue": "existed-pg",
                    "type": "vlanServiceAttribute",
                },
                {
                    "attributeName": "VLAN ID",
                    "attributeValue": "10-11",
                    "type": "vlanServiceAttribute",
                },
                {
                    "attributeName": "Virtual Network",
                    "attributeValue": "network name",
                    "type": "vlanServiceAttribute",
                },
            ],
            "type": "setVlanParameter",
        },
        "connectorAttributes": [
            {
                "attributeName": "Selected Network",
                "attributeValue": "2",
                "type": "connectorAttribute",
            },
            {
                "attributeName": "Interface",
                "attributeValue": "mac address",
                "type": "connectorAttribute",
            },
        ],
        "actionTarget": {
            "fullName": "centos",
            "fullAddress": "full address",
            "type": "actionTarget",
        },
        "customActionAttributes": [
            {
                "attributeName": "VM_UUID",
                "attributeValue": "vm_uid",
                "type": "customAttribute",
            },
            {
                "attributeName": "Vnic Name",
                "attributeValue": "vnic",
                "type": "customAttribute",
            },
        ],
        "actionId": "96582265-2728-43aa-bc97-cefb2457ca44_0900c4b5-0f90-42e3-b495",
        "type": "removeVlan",
    }


def test_connectivity_action_model_parse_port_group_name(action_request):
    action = VcenterConnectivityActionModel.parse_obj(action_request)
    action.connection_params.vlan_service_attrs.virtual_network = None

    assert get_existed_port_group_name(action) == "existed-pg"


def test_connectivity_action_model_without_port_group_name(action_request):
    action = VcenterConnectivityActionModel.parse_obj(action_request)
    action.connection_params.vlan_service_attrs.port_group_name = None
    action.connection_params.vlan_service_attrs.virtual_network = None

    assert get_existed_port_group_name(action) is None


def test_existed_port_group_name_in_virtual_network(action_request):
    action = VcenterConnectivityActionModel.parse_obj(action_request)

    assert get_existed_port_group_name(action) == "network name"


@pytest.mark.parametrize(
    ("expected_vnic", "vnic_label", "is_correct"),
    (
        ("2", "Network adapter 2", True),
        ("network adapter 1", "Network adapter 1", True),
        ("10", "Network adapter 10", True),
        ("Network adapter 3", "Network adapter 2", False),
        (" 3", "Network adapter 3", False),
    ),
)
def test_is_correct_vnic(expected_vnic, vnic_label, is_correct):
    vnic = Vnic(Mock(deviceInfo=Mock(label=vnic_label)))
    assert is_correct_vnic(expected_vnic, vnic) is is_correct


@pytest.mark.parametrize(
    ("net_name", "virtual_network", "expected_result"),
    (
        ("network-name", "network-name", False),
        (
            generate_port_group_name("switch", "11", ConnectionModeEnum.ACCESS),
            generate_port_group_name("switch", "11", ConnectionModeEnum.ACCESS),
            False,
        ),
        ("network-name", None, False),
        (
            generate_port_group_name("switch", "11", ConnectionModeEnum.ACCESS),
            None,
            True,
        ),
    ),
)
def test_should_remove_port_group(
    action_request, net_name, virtual_network, expected_result
):
    action = VcenterConnectivityActionModel.parse_obj(action_request)
    action.connection_params.vlan_service_attrs.port_group_name = None
    action.connection_params.vlan_service_attrs.virtual_network = virtual_network

    result = should_remove_port_group(net_name, action)

    assert result == expected_result


@pytest.mark.parametrize(
    ("default_net_name", "reserved_networks", "expected_vnic_name"),
    (
        ("Local", [], "vnic2"),
        ("another-name", [], "vnic2"),
        ("default-net", ["another-name", "Local"], None),
    ),
)
def test_get_available_vnic(
    default_net_name, reserved_networks, expected_vnic_name, logger
):
    # Default Network
    default_network = Mock()
    default_network.name = default_net_name
    # vNIC1
    net1 = Mock()
    net1.name = generate_port_group_name("switch", "11", ConnectionModeEnum.ACCESS)
    vnic1 = Mock(name="vnic1", network=net1)
    # vNIC2
    net2 = Mock()
    net2.name = "Local"
    vnic2 = Mock(name="vnic2", network=net2)
    # vNIC3
    net3 = Mock()
    net3.name = "another-name"
    vnic3 = Mock(name="vnic3", network=net3)
    # VM
    vm = Mock(vnics=[vnic1, vnic2, vnic3])

    # expected vNIC
    expected_vnic = expected_vnic_name and locals()[expected_vnic_name]

    vnic = get_available_vnic(vm, default_network, reserved_networks)

    assert vnic == expected_vnic
