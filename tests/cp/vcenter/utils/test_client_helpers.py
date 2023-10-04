from __future__ import annotations

import ssl
from unittest.mock import patch

import pytest
from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import LoginException
from cloudshell.cp.vcenter.utils.client_helpers import (
    ApiConnectionError,
    VcenterConnectionError,
    get_si,
)

HOST = "host"
USER = "user"
PASSWORD = "password"
PORT = 443


@pytest.fixture()
def connect_mock():
    with patch("cloudshell.cp.vcenter.utils.client_helpers.SmartConnect") as mock:
        yield mock


def _check_connection_mock(kwargs, ssl_protocol):
    assert kwargs["host"] == HOST
    assert kwargs["user"] == USER
    assert kwargs["pwd"] == PASSWORD
    assert kwargs["port"] == PORT

    if ssl_protocol is None:
        assert "sslContext" not in kwargs
    else:
        context = kwargs["sslContext"]
        assert isinstance(context, ssl.SSLContext)
        assert context.verify_mode == ssl.CERT_NONE
        assert context.protocol == ssl_protocol


def test_get_si_tls_v1_2(connect_mock):
    si = get_si(HOST, USER, PASSWORD, PORT)

    connect_mock.assert_called_once()
    _check_connection_mock(connect_mock.call_args.kwargs, ssl.PROTOCOL_TLSv1_2)
    assert si is connect_mock.return_value


def test_get_si_tls_v1(connect_mock):
    connect_mock.side_effect = [
        ssl.SSLError("wrong protocol"),
        connect_mock.return_value,
    ]
    si = get_si(HOST, USER, PASSWORD, PORT)

    assert connect_mock.call_count == 2
    kwargs1 = connect_mock.call_args_list[0].kwargs
    _check_connection_mock(kwargs1, ssl.PROTOCOL_TLSv1_2)
    kwargs2 = connect_mock.call_args_list[1].kwargs
    _check_connection_mock(kwargs2, ssl.PROTOCOL_TLSv1)

    assert si is connect_mock.return_value


def test_get_si_without_ssl(connect_mock):
    connect_mock.side_effect = [
        ssl.SSLError("wrong protocol"),
        ssl.SSLError("wrong protocol"),
        connect_mock.return_value,
    ]
    si = get_si(HOST, USER, PASSWORD, PORT)

    assert connect_mock.call_count == 3
    kwargs1 = connect_mock.call_args_list[0].kwargs
    _check_connection_mock(kwargs1, ssl.PROTOCOL_TLSv1_2)
    kwargs2 = connect_mock.call_args_list[1].kwargs
    _check_connection_mock(kwargs2, ssl.PROTOCOL_TLSv1)
    kwargs3 = connect_mock.call_args_list[2].kwargs
    _check_connection_mock(kwargs3, None)

    assert si is connect_mock.return_value


@pytest.mark.parametrize("error", (ssl.SSLEOFError, ssl.SSLError))
def test_api_connection_error(connect_mock, error):
    connect_mock.side_effect = error

    with pytest.raises(ApiConnectionError):
        get_si(HOST, USER, PASSWORD, PORT)


@pytest.mark.parametrize("error", (vim.fault.HostConnectFault, OSError))
def test_vcenter_connection_error(connect_mock, error):
    connect_mock.side_effect = error

    with pytest.raises(VcenterConnectionError):
        get_si(HOST, USER, PASSWORD, PORT)


def test_get_si_invalid_login(connect_mock, sleepless):
    connect_mock.side_effect = vim.fault.InvalidLogin

    with pytest.raises(LoginException):
        get_si(HOST, USER, PASSWORD, PORT)
