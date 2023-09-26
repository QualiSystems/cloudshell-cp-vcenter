from __future__ import annotations

import json
import logging

from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig

logger = logging.getLogger(__name__)


def get_cluster_usage(
    si: SiHandler,
    resource_conf: VCenterResourceConfig,
    datastore_name: str,
):
    datastore_name = datastore_name or resource_conf.vm_storage
    dc = DcHandler.get_dc(resource_conf.default_datacenter, si)
    compute_entity = dc.get_compute_entity(resource_conf.vm_cluster)
    datastore = dc.get_datastore(datastore_name)
    logger.info(f"Found {compute_entity}")
    return json.dumps(
        {
            "datastore": datastore.usage_info.to_dict(),
            "cpu": compute_entity.cpu_usage.to_dict(),
            "ram": compute_entity.ram_usage.to_dict(),
        }
    )
