from __future__ import annotations

from unittest.mock import Mock

import pytest

from cloudshell.cp.vcenter.actions.vm_network import (
    VMNetworkActions,
    get_ip_regex_match_func,
)


@pytest.fixture()
def vm_net_actions(cancellation_manager, resource_conf):
    return VMNetworkActions(resource_conf, cancellation_manager)


@pytest.mark.parametrize(
    ("primary_ip", "vnic_ips", "ip_regex", "expected_ip"),
    [
        (None, [], None, None),
        ("192.168.1.2", [], None, "192.168.1.2"),
        (None, ["192.168.2.3", "192.168.3.4"], None, "192.168.2.3"),
        ("172.16.2.3", [], r"10\.1\.5\.\d{1,3}", None),
        ("172.16.2.3", ["10.2.6.4", "10.1.5.250"], r"10\.1\.5\.\d{1,3}", "10.1.5.250"),
    ],
)
def test__find_vm_ip(vm_net_actions, primary_ip, vnic_ips, ip_regex, expected_ip):
    vnics = [Mock(ipv4=vnic_ip, network=Mock()) for vnic_ip in vnic_ips]
    vm = Mock(primary_ipv4=primary_ip, vnics=vnics)
    regex_func = get_ip_regex_match_func(ip_regex)

    ip = vm_net_actions._find_vm_ip(vm, [], regex_func)

    assert ip == expected_ip
