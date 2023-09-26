import jsonpickle

from cloudshell.cp.vcenter.flows.get_attribute_hints.deployment_type_handlers import (
    get_handler,
)
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.models.DeployDataHolder import DeployDataHolder
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


def get_hints(
    si: SiHandler,
    resource_conf: VCenterResourceConfig,
    request: str,
) -> str:
    # todo replace with a model
    request = DeployDataHolder(jsonpickle.decode(request))
    dc = DcHandler.get_dc(resource_conf.default_datacenter, si)

    handler = get_handler(request, dc)
    response = handler.prepare_hints()
    return jsonpickle.encode(response, unpicklable=False)
