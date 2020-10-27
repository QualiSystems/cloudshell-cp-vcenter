from logging import Logger

from cloudshell.cp.vcenter.api.client import VCenterAPIClient
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


class ValidationActions:
    def __init__(
        self,
        vcenter_client: VCenterAPIClient,
        resource_conf: VCenterResourceConfig,
        logger: Logger,
    ):
        self._vcenter_client = vcenter_client
        self._resource_conf = resource_conf
        self._logger = logger

    def validate(self):
        self._validate_resource_conf()
        self._validate_connection()
        self._validate_dc()
        # todo should we return attributes?
        #  auto_att.append(AutoLoadAttribute('', DEFAULT_DATACENTER, dc.name))  noqa

    def _validate_resource_conf(self):
        conf = self._resource_conf
        _is_not_empty(conf.address, "address")
        _is_not_empty(conf.user, conf.ATTR_NAMES.user)
        _is_not_empty(conf.password, conf.ATTR_NAMES.password)
        _is_not_empty(conf.default_datacenter, conf.ATTR_NAMES.default_datacenter)

    def _validate_connection(self):
        _ = self._vcenter_client._si  # try to connect

    def _validate_dc(self):
        self._vcenter_client.get_dc(self._resource_conf.default_datacenter)


def _is_not_empty(value: str, attr_name: str):
    if not value:
        raise ValueError(f"{attr_name} cannot be empty")
