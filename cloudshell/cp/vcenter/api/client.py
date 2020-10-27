from logging import Logger

from pyVmomi import vim  # noqa

from cloudshell.cp.vcenter.exceptions import LoginException
from cloudshell.cp.vcenter.utils.cached_property import cached_property
from cloudshell.cp.vcenter.utils.client_helpers import get_si


class VCenterAPIClient:
    def __init__(
        self, host: str, user: str, password: str, logger: Logger, port: int = 443
    ):
        self._host = host
        self._user = user
        self._password = password
        self._port = port
        self._logger = logger

    # todo: check id we need this
    # def back_slash_to_front_converter(string):
    #     """
    #     Replacing all \ in the str to /
    #     :param string: single string to modify
    #     :type string: str
    #     """
    #     pass

    def _get_si(self):
        self._logger.info("Initializing vCenter API client SI...")
        try:
            si = get_si(self._host, self._user, self._password, self._port)
        except vim.fault.InvalidLogin:
            self._logger.exception("Unable to login to the vCenter")
            raise LoginException("Can't connect to the vCenter. Invalid user/password")
        return si

    @cached_property
    def _si(self):
        return self._get_si()
