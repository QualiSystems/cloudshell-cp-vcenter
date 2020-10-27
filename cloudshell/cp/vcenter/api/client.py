from contextlib import contextmanager
from logging import Logger

from pyVmomi import vim  # noqa

from cloudshell.cp.vcenter.exceptions import LoginException, ObjectNotFoundException
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

    @property
    def root_container(self):
        return self._si.content.rootFolder

    @contextmanager
    def _get_ctx_view(self, container, vim_type, recursive=True):
        if not isinstance(vim_type, list):
            vim_type = [vim_type]
        view = self._si.content.viewManager.CreateContainerView(
            container, vim_type, recursive
        )
        try:
            yield view.view
        finally:
            view.DestroyView()

    def get_dc(self, name: str):
        with self._get_ctx_view(self.root_container, vim.Datacenter) as dcs:
            for dc in dcs:
                if dc.name == name:
                    return dc
        raise ObjectNotFoundException(f"Datacenter '{name}' not found")
