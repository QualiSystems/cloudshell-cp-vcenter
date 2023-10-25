from __future__ import annotations

import logging
from collections import namedtuple
from unittest.mock import Mock

import pytest
from pyVmomi import vim

from cloudshell.cp.vcenter.handlers.network_handler import (
    NetworkHandler,
    NetworkNotFound,
)

logger = logging.getLogger(__name__)


@pytest.fixture()
def update_network_do_nothing(monkeypatch, network_watcher):
    m = Mock()
    monkeypatch.setattr(network_watcher, "update_networks", m)
    return m


def test_init_network_watcher(
    si, network_watcher, property_collector, filter_spec, object_spec, container
):
    assert network_watcher._si == si
    assert network_watcher._container == container
    assert network_watcher._recursive is True
    assert network_watcher._networks == {}
    assert network_watcher._network_to_name == {}
    assert network_watcher._collector == property_collector
    assert network_watcher._version == ""
    property_collector.CreateFilter.assert_called_once_with(
        filter_spec.return_value, partialUpdates=True
    )


def test_context(network_watcher):
    with network_watcher as nw:
        assert nw is network_watcher
    assert network_watcher._collector.Destroy.call_count == 1


def test_update_networks(
    network_watcher, property_collector, filter_spec, object_spec, container
):
    net1 = Mock(spec=vim.Network)
    net1.name = "Network 1"
    net2 = Mock(spec=vim.Network)
    net2.name = "Network 2"
    net3 = Mock(spec=vim.Network)
    net3.name = "Network 3"
    change = namedtuple("change", "name val")
    obj_set1 = [  # add 2 networks
        Mock(obj=net1, kind="enter", changeSet=[change(name="name", val=net1.name)]),
        Mock(obj=net2, kind="enter", changeSet=[change(name="name", val=net2.name)]),
    ]
    obj_set2 = [  # add network 3 and remove network 1
        Mock(obj=net3, kind="enter", changeSet=[change(name="name", val=net3.name)]),
        # changeSet is empty because the network is removed
        Mock(obj=net1, kind="leave", changeSet=[]),
    ]
    property_collector.WaitForUpdatesEx.side_effect = [
        Mock(version="1", filterSet=[Mock(objectSet=obj_set1)]),
        Mock(version="2", filterSet=[Mock(objectSet=obj_set2)]),
        None,  # no updates
    ]

    # run update
    network_watcher.update_networks(wait=0)

    # check
    assert network_watcher._networks == {
        net2.name: net2,
        net3.name: net3,
    }
    assert network_watcher._network_to_name == {
        net2: net2.name,
        net3: net3.name,
    }


def test_network_exists(network_watcher, update_network_do_nothing):
    net = Mock(spec=vim.Network)
    network_watcher._networks = {"Network 1": net}

    assert network_watcher.exists("Network 1") is True
    assert network_watcher.exists("Network 2") is False


def test_populate_in_bg(network_watcher, update_network_do_nothing):
    network_watcher.populate_in_bg()
    update_network_do_nothing.assert_called_once_with(wait=0)


def test_get_network(network_watcher, update_network_do_nothing):
    net = Mock(spec=vim.Network)
    network_watcher._networks = {"Network 1": net}

    nh = network_watcher.get_network("Network 1")
    assert isinstance(nh, NetworkHandler)
    assert nh.get_vc_obj() == net
    with pytest.raises(NetworkNotFound):
        network_watcher.get_network("Network 2")


def test_find_networks(network_watcher, update_network_do_nothing):
    net1 = Mock(spec=vim.Network)
    net1.name = "Network 1"
    net2 = Mock(spec=vim.Network)
    net2.name = "Network 2"
    network_watcher._networks = {"Network 1": net1, "Network 2": net2}

    networks = list(network_watcher.find_networks(lambda name: name.endswith(" 1")))
    assert len(networks) == 1
    assert networks[0].get_vc_obj() == net1

    networks = list(network_watcher.find_networks(lambda name: name == "Network 3"))
    assert len(networks) == 0


def test_wait_appears(network_watcher, monkeypatch):
    net1 = Mock(spec=vim.Network)
    net1.name = "Network 1"
    net2 = Mock(spec=vim.Network)
    net2.name = "Network 2"
    net3 = Mock(spec=vim.Network)
    net3.name = "Network 3"
    updates = [net1, None, net2, None, net3]

    def _adding_nets(wait):
        # update network doesn't get networks each time
        if n := updates.pop(0):
            network_watcher._networks[n.name] = n

    # with each update add a new networks
    monkeypatch.setattr(network_watcher, "update_networks", _adding_nets)

    net = network_watcher.wait_appears("Network 2", wait=100)

    assert net.get_vc_obj() == net2
    # we don't need to wait for the last update
    assert len(network_watcher._networks) == 2
