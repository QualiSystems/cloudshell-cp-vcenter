from __future__ import annotations

from collections.abc import Iterable

from attrs import define


class BaseVCenterException(Exception):
    pass


class InvalidCommandParam(BaseVCenterException):
    def __init__(
        self, param_name: str, param_value: str, expected_values: Iterable[str]
    ):
        self.param_name = param_name
        self.param_value = param_value
        self.expected_values = expected_values
        super().__init__(
            f"Param '{param_name}' is invalid. It should be one of the "
            f"'{expected_values}' but the value is '{param_value}'"
        )


class LoginException(BaseVCenterException):
    """Login Exception."""


class InvalidAttributeException(BaseVCenterException):
    """Attribute is not valid."""


@define
class VMIPNotFoundException(BaseVCenterException):
    ip_regex: str | None = None

    def __str__(self):
        msg = "IP address not found"
        if self.ip_regex:
            msg = f"{msg} by regex: {self.ip_regex}"
        return msg


class EmptyOVFToolResultException(BaseVCenterException):
    """No response result from the OVF tool."""


class DeployOVFToolException(BaseVCenterException):
    """Failed to deploy VM via OVF tool."""
