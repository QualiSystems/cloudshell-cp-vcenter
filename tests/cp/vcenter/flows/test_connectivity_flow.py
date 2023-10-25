from __future__ import annotations

import logging

import pytest

from cloudshell.shell.flows.connectivity.parse_request_service import (
    ParseConnectivityRequestService,
)

from cloudshell.cp.vcenter.flows.connectivity_flow import VCenterConnectivityFlow
from cloudshell.cp.vcenter.models.connectivity_action_model import (
    VcenterConnectivityActionModel,
)
from cloudshell.cp.vcenter.utils.connectivity_helpers import DvSwitchNameEmpty

logger = logging.getLogger(__name__)


ACTION_DICT = {
    "connectionId": "96582265-2728-43aa-bc97-cefb2457ca44",
    "connectionParams": {
        "vlanId": "11",
        "mode": "Access",
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
                "attributeName": "VLAN ID",
                "attributeValue": "11",
                "type": "vlanServiceAttribute",
            },
            {
                "attributeName": "Virtual Network",
                "attributeValue": "",
                "type": "vlanServiceAttribute",
            },
        ],
        "type": "setVlanParameter",
    },
    "connectorAttributes": [
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
    "type": "setVlan",
}


@pytest.fixture
def parse_connectivity_service():
    return ParseConnectivityRequestService(
        is_vlan_range_supported=True, is_multi_vlan_supported=True
    )


@pytest.fixture
def flow(
    si, parse_connectivity_service, resource_conf, reservation_info, dc, network_watcher
):
    return VCenterConnectivityFlow(
        parse_connectivity_service, si, resource_conf, reservation_info
    )


@pytest.fixture
def set_action():
    return VcenterConnectivityActionModel.model_validate(ACTION_DICT)


def test_validate_actions(flow, set_action):
    flow.validate_actions([set_action])


def test_validate_actions_without_switch(flow, set_action, resource_conf):
    resource_conf.default_dv_switch = None
    with pytest.raises(DvSwitchNameEmpty):
        flow.validate_actions([set_action])


def test_validate_actions_switch_in_vlan_service(flow, set_action, resource_conf):
    resource_conf.default_dv_switch = None
    set_action.connection_params.vlan_service_attrs.switch_name = "switch"
    flow.validate_actions([set_action])


def test_validate_actions_switch_is_empty_but_we_use_user_created_network(
    flow, set_action, resource_conf
):
    resource_conf.default_dv_switch = None
    set_action.connection_params.vlan_service_attrs.existing_network = "network"
    flow.validate_actions([set_action])
