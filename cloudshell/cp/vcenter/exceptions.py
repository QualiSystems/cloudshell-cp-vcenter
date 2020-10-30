class BaseVCenterException(Exception):
    pass


class LoginException(BaseVCenterException):
    """Login Exception."""


class ObjectNotFoundException(BaseVCenterException):
    """Object not found."""


class TaskFaultException(BaseVCenterException):
    """Task Failed."""


class VMWareToolsNotInstalled(BaseVCenterException):
    """VMWare Tools are not installed."""
