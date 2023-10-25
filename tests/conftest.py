import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from pyVmomi import vim, vmodl

from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.request_actions import GetVMDetailsRequestActions
from cloudshell.cp.core.reservation_info import ReservationInfo
from cloudshell.shell.core.driver_context import (
    AppContext,
    ConnectivityContext,
    ReservationContextDetails,
    ResourceCommandContext,
    ResourceContextDetails,
)

from .base import SiMock, VmMock

from cloudshell.cp.vcenter.constants import SHELL_NAME, STATIC_SHELL_NAME
from cloudshell.cp.vcenter.handlers.cluster_handler import ClusterHandler
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler
from cloudshell.cp.vcenter.models.deployed_app import StaticVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig
from cloudshell.cp.vcenter.utils.network_watcher import NetworkWatcher


@pytest.fixture()
def logger():
    return MagicMock()


@pytest.fixture
def sleepless(monkeypatch):
    with patch("time.sleep"):
        yield


@pytest.fixture()
def connectivity_context() -> ConnectivityContext:
    return ConnectivityContext(
        server_address="localhost",
        cloudshell_api_port="5000",
        quali_api_port="5001",
        admin_auth_token="token",
        cloudshell_version="2021.2",
        cloudshell_api_scheme="https",
    )


@pytest.fixture()
def resource_context_details() -> ResourceContextDetails:
    return ResourceContextDetails(
        id="id",
        name="name",
        fullname="fullname",
        type="type",
        address="192.168.1.2",
        model=SHELL_NAME,
        family="family",
        description="",
        attributes={},
        app_context=AppContext("", ""),
        networks_info=None,
        shell_standard="",
        shell_standard_version="",
    )


@pytest.fixture()
def reservation_context_details() -> ReservationContextDetails:
    return ReservationContextDetails(
        environment_name="env name",
        environment_path="env path",
        domain="domain",
        description="",
        owner_user="user",
        owner_email="email",
        reservation_id="rid",
        saved_sandbox_name="name",
        saved_sandbox_id="id",
        running_user="user",
        cloud_info_access_key="",
    )


@pytest.fixture
def reservation_info(reservation_context_details):
    return ReservationInfo._from_reservation_context(reservation_context_details)


@pytest.fixture()
def resource_command_context(
    connectivity_context, resource_context_details, reservation_context_details
) -> ResourceCommandContext:
    return ResourceCommandContext(
        connectivity_context, resource_context_details, reservation_context_details, []
    )


@pytest.fixture()
def cs_api():
    return MagicMock(DecryptPassword=lambda pswd: MagicMock(Value=pswd))


@pytest.fixture()
def cancellation_manager() -> CancellationContextManager:
    return CancellationContextManager(MagicMock(is_cancelled=False))


@pytest.fixture()
def resource_conf(resource_command_context, cs_api) -> VCenterResourceConfig:
    user = "user name"
    password = "password"
    default_datacenter = "default datacenter"
    default_dv_switch = "default dvSwitch"
    holding_network = "holding network"
    vm_cluster = "vm cluster"
    vm_resource_pool = "vm resource pool"
    vm_storage = "vm storage"
    saved_sandbox_storage = "saved sandbox storage"
    behavior_during_save = "Remain Powered On"
    vm_location = "vm location"
    shutdown_method = "soft"
    ovf_tool_path = "ovf tool path"
    reserved_networks = "10.1.0.0/24;10.1.1.0/24"
    execution_server_selector = "Execution Server Selector"
    promiscuous_mode = "true"
    forged_transmits = "true"
    mac_address_changes = "false"
    enable_tags = "false"

    a_name = VCenterResourceConfig.ATTR_NAMES
    get_full_a_name = lambda n: f"{SHELL_NAME}.{n}"  # noqa: E731
    resource_command_context.resource.attributes.update(
        {
            get_full_a_name(a_name.user): user,
            get_full_a_name(a_name.password): password,
            get_full_a_name(a_name.default_datacenter): default_datacenter,
            get_full_a_name(a_name.default_dv_switch): default_dv_switch,
            get_full_a_name(a_name.holding_network): holding_network,
            get_full_a_name(a_name.vm_cluster): vm_cluster,
            get_full_a_name(a_name.vm_resource_pool): vm_resource_pool,
            get_full_a_name(a_name.vm_storage): vm_storage,
            get_full_a_name(a_name.saved_sandbox_storage): saved_sandbox_storage,
            get_full_a_name(a_name.behavior_during_save): behavior_during_save,
            get_full_a_name(a_name.vm_location): vm_location,
            get_full_a_name(a_name.shutdown_method): shutdown_method,
            get_full_a_name(a_name.ovf_tool_path): ovf_tool_path,
            get_full_a_name(a_name.reserved_networks): reserved_networks,
            get_full_a_name(
                a_name.execution_server_selector
            ): execution_server_selector,
            get_full_a_name(a_name.promiscuous_mode): promiscuous_mode,
            get_full_a_name(a_name.forged_transmits): forged_transmits,
            get_full_a_name(a_name.mac_changes): mac_address_changes,
            get_full_a_name(a_name.enable_tags): enable_tags,
        }
    )

    class Cfg(VCenterResourceConfig):
        __dict__ = {}

        def __setattr__(self, key, value):
            object.__setattr__(self, key, value)

    conf = Cfg.from_context(resource_command_context, cs_api)

    return conf


@pytest.fixture()
def si_mock():
    return SiMock


@pytest.fixture()
def vm_mock():
    return VmMock


@pytest.fixture()
def vc_si():
    return SiMock()


@pytest.fixture
def si(vc_si) -> SiHandler:
    class SH(SiHandler):
        __dict__ = {}

    return SH(vc_si)


@pytest.fixture()
def dc(si, resource_conf, monkeypatch) -> DcHandler:
    class DH(DcHandler):
        __dict__ = {}

    dc_ = Mock()
    dch = DH(dc_, si)

    def _get_default_dc(name, si_):
        if name == resource_conf.default_datacenter and si_ == si:
            return dch
        raise NotImplementedError

    monkeypatch.setattr(DcHandler, "get_dc", _get_default_dc)
    return dch


@pytest.fixture()
def cluster(dc, si, monkeypatch, resource_conf) -> ClusterHandler:
    class CH(ClusterHandler):
        __dict__ = {}

    vc_cluster = Mock()
    ch = CH(vc_cluster, si)

    def _get_cluster(name):
        if name == resource_conf.vm_cluster:
            return ch
        raise NotImplementedError

    monkeypatch.setattr(dc, "get_cluster", _get_cluster)
    return ch


@pytest.fixture
def vm(si):
    vm_ = Mock()
    vm_.name = "vm"
    return VmHandler(vm_, si)


@pytest.fixture()
def static_deployed_app(cs_api) -> StaticVCenterDeployedApp:
    vm_name = "vm folder/vm-name"
    vcenter_name = "vcenter"
    vm_uuid = "uuid"
    requests = {
        "items": [
            {
                "appRequestJson": {
                    "name": "win-static",
                    "description": None,
                    "logicalResource": {
                        "family": None,
                        "model": None,
                        "driver": None,
                        "description": None,
                        "attributes": [],
                    },
                    "deploymentService": {
                        "cloudProviderName": None,
                        "name": "win-static",
                        "model": STATIC_SHELL_NAME,
                        "driver": STATIC_SHELL_NAME,
                        "attributes": [
                            {
                                "name": f"{STATIC_SHELL_NAME}.VM Name",
                                "value": vm_name,
                            },
                            {
                                "name": f"{STATIC_SHELL_NAME}.vCenter Resource Name",
                                "value": vcenter_name,
                            },
                            {
                                "name": f"{STATIC_SHELL_NAME}.User",
                                "value": "",
                            },
                            {
                                "name": f"{STATIC_SHELL_NAME}.Password",
                                "value": "",
                            },
                            {
                                "name": f"{STATIC_SHELL_NAME}.Public IP",
                                "value": "",
                            },
                            {"name": "Execution Server Selector", "value": ""},
                        ],
                    },
                },
                "deployedAppJson": {
                    "name": "win-static",
                    "family": "CS_GenericAppFamily",
                    "model": f"{STATIC_SHELL_NAME}",
                    "address": "192.168.1.2",
                    "attributes": [
                        {
                            "name": f"{STATIC_SHELL_NAME}.VM Name",
                            "value": vm_name,
                        },
                        {
                            "name": f"{STATIC_SHELL_NAME}.vCenter Resource Name",
                            "value": vcenter_name,
                        },
                        {
                            "name": f"{STATIC_SHELL_NAME}.User",
                            "value": "",
                        },
                        {
                            "name": f"{STATIC_SHELL_NAME}.Password",
                            "value": "",
                        },
                        {
                            "name": f"{STATIC_SHELL_NAME}.Public IP",
                            "value": "",
                        },
                        {"name": "Execution Server Selector", "value": ""},
                    ],
                    "vmdetails": {
                        "id": "6132ff9e-379b-4e73-918d-b7e0b7bc93d5",
                        "cloudProviderId": "d4d679c6-3049-4e55-9e64-8692a3400b6a",
                        "uid": vm_uuid,
                        "vmCustomParams": [],
                    },
                },
            }
        ]
    }
    requests = json.dumps(requests)

    GetVMDetailsRequestActions.register_deployment_path(StaticVCenterDeployedApp)
    actions = GetVMDetailsRequestActions.from_request(requests, cs_api)
    return actions.deployed_apps[0]


@pytest.fixture()
def object_spec(monkeypatch):
    m = Mock()
    monkeypatch.setattr(vmodl.query.PropertyCollector, "ObjectSpec", m)
    return m


@pytest.fixture()
def filter_spec(monkeypatch):
    m = Mock()
    monkeypatch.setattr(vmodl.query.PropertyCollector, "FilterSpec", m)
    return m


@pytest.fixture()
def property_collector(si):
    m = Mock()
    si.get_vc_obj().content.propertyCollector.CreatePropertyCollector.return_value = m
    # no updates
    m.WaitForUpdatesEx.side_effect = [None]
    return m


@pytest.fixture()
def container(si):
    vc_container = Mock(spec=vim.Datacenter)
    vc_container.name = "Datacenter"
    return ManagedEntityHandler(vc_container, si)


@pytest.fixture()
def network_watcher(si, container, object_spec, filter_spec, property_collector):
    # add ability to modify class attributes
    class N(NetworkWatcher):
        __dict__ = {}

    return N(si, container)
