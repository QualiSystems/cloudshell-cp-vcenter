class BaseVCenterException(Exception):
    pass


class LoginException(BaseVCenterException):
    """Login Exception."""


class ObjectNotFoundException(BaseVCenterException):
    """Object not found."""
