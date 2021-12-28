from unittest.mock import MagicMock

import pytest

from cloudshell.shell.core.driver_context import (
    AppContext,
    ConnectivityContext,
    ReservationContextDetails,
    ResourceCommandContext,
    ResourceContextDetails,
)


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
        model="model",
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
    )


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
