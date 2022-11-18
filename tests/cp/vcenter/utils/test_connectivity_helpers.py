from unittest.mock import Mock

import pytest

from cloudshell.cp.vcenter.utils.connectivity_helpers import (
    generate_port_group_name,
    get_available_vnic,
    is_correct_vnic,
)


@pytest.mark.parametrize(
    ("expected_vnic", "vnic_label", "is_correct"),
    (
        ("2", "Network adapter 2", True),
        ("network adapter 1", "Network adapter 1", True),
        ("10", "Network adapter 10", True),
        ("Network adapter 3", "Network adapter 2", False),
        (" 3", "Network adapter 3", False),
        ("2", "not expected network name", False),
    ),
)
def test_is_correct_vnic(expected_vnic, vnic_label, is_correct):
    assert is_correct_vnic(expected_vnic, vnic_label) == is_correct


@pytest.mark.parametrize(
    ("default_net_name", "reserved_networks", "expected_vnic_name"),
    (
        ("Local", [], "vnic2"),
        ("another-name", [], "vnic2"),
        ("default-net", ["another-name", "Local"], "vnic4"),
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
    net1.name = generate_port_group_name("switch", "11", "access")
    vnic1 = Mock(name="vnic1", network=net1)
    # vNIC2
    net2 = Mock()
    net2.name = "Local"
    vnic2 = Mock(name="vnic2", network=net2)
    # vNIC3
    net3 = Mock()
    net3.name = "another-name"
    vnic3 = Mock(name="vnic3", network=net3)
    # new vNIC4
    vnic4 = Mock(name="vnic4", network=default_network)
    # VM
    vm = Mock(vnics=[vnic1, vnic2, vnic3])
    vm.get_network_from_vnic.side_effect = lambda v: v.network

    def create_vnic(logger):
        vm.vnics = [*vm.vnics, vnic4]

    vm.create_vnic = create_vnic
    # expected vNIC
    expected_vnic = locals()[expected_vnic_name]

    vnic = get_available_vnic(vm, default_network, reserved_networks, logger)

    assert vnic == expected_vnic
