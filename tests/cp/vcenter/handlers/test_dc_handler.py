from unittest.mock import Mock

import pytest

from cloudshell.cp.vcenter.handlers.cluster_handler import ClusterNotFound, HostNotFound
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler


@pytest.fixture
def vc_host():
    host = Mock()
    host.name = "host1"
    return host


@pytest.fixture
def vc_cluster1(vc_host):
    cluster = Mock(host=[vc_host])
    cluster.name = "Cluster1"
    vc_host.parent = cluster
    return cluster


@pytest.fixture
def vc_dc():
    dc = Mock()
    return dc


@pytest.fixture
def si_mock():
    return Mock()


@pytest.fixture
def dc(vc_dc, si_mock, vc_cluster1):
    si_mock.find_items.return_value = [vc_cluster1]
    return DcHandler(vc_dc, si_mock)


def test_get_compute_entity(dc):
    cluster = dc.get_compute_entity("Cluster1")

    assert cluster.name == "Cluster1"


def test_get_host_from_cluster(dc):
    host = dc.get_compute_entity("Cluster1/host1")

    assert host.name == "host1"
    assert host.cluster.name == "Cluster1"


def test_compute_entity_not_found(dc):
    with pytest.raises(ClusterNotFound):
        dc.get_compute_entity("Cluster2")

    with pytest.raises(HostNotFound):
        dc.get_compute_entity("Cluster1/host2")
