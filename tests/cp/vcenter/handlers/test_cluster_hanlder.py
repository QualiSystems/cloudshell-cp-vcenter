from unittest.mock import Mock

import pytest

from cloudshell.cp.vcenter.handlers.cluster_handler import HostHandler


@pytest.fixture
def vc_host():
    host = Mock()
    host.name = "host1"
    return host


@pytest.fixture
def host(vc_host, si):
    return HostHandler(vc_host, si)


def test_get_resource_pool_from_host(host):
    rp1 = host.get_resource_pool(None)
    rp2 = host.cluster.get_resource_pool(None)

    assert rp1 == rp2
