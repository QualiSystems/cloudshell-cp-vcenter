from __future__ import annotations

import json
from logging import Logger

from pyVmomi import vim

from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.common.utilites import units_converter
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


def _get_datastore_usage(
    vcenter_client: VCenterAPIClient,
    resource_conf: VCenterResourceConfig,
    datastore_name: str,
    logger: Logger,
) -> dict[str, str]:
    datastore_name = datastore_name or resource_conf.vm_storage

    logger.info(f"Getting Datastore '{datastore_name}'... ")
    dc = vcenter_client.get_dc(resource_conf.default_datacenter)
    datastore = vcenter_client.get_storage(datastore_name, dc)

    if not datastore:
        raise Exception(f"Unable to find Datastore '{datastore_name}'")

    used_space = datastore.summary.capacity - datastore.summary.freeSpace
    return {
        "capacity": units_converter.format_bytes(datastore.summary.capacity),
        "used": units_converter.format_bytes(used_space),
        "free": units_converter.format_bytes(datastore.summary.freeSpace),
        "used_percentage": round(used_space / datastore.summary.capacity * 100),
    }


def _get_cpu_usage(cluster, logger: Logger) -> dict[str, str]:
    if isinstance(cluster, vim.ClusterComputeResource):
        usage_summary = cluster.GetResourceUsage()
        logger.info(f"Cluster usage summary: {usage_summary}")

        total_cpu_capacity = units_converter.format_hertz(
            usage_summary.cpuCapacityMHz, prefix=units_converter.PREFIX_MHZ
        )
        used_cpu = units_converter.format_hertz(
            usage_summary.cpuUsedMHz, prefix=units_converter.PREFIX_MHZ
        )
        free_cpu = units_converter.format_hertz(
            usage_summary.cpuCapacityMHz - usage_summary.cpuUsedMHz,
            prefix=units_converter.PREFIX_MHZ,
        )
        used_cpu_percentage = round(
            usage_summary.cpuUsedMHz / usage_summary.cpuCapacityMHz * 100
        )

    else:
        logger.info(f"Host usage stats: {cluster.summary.quickStats}")
        cpu_usage_hz = (
            cluster.summary.quickStats.overallCpuUsage
            * units_converter.BASE_SI
            * units_converter.BASE_SI
        )
        total_cpu_hz = (
            cluster.hardware.cpuInfo.hz * cluster.hardware.cpuInfo.numCpuCores
        )

        total_cpu_capacity = units_converter.format_hertz(total_cpu_hz)
        used_cpu = units_converter.format_hertz(cpu_usage_hz)
        free_cpu = units_converter.format_hertz(total_cpu_hz - cpu_usage_hz)
        used_cpu_percentage = round(cpu_usage_hz / total_cpu_hz * 100)

    return {
        "capacity": total_cpu_capacity,
        "used": used_cpu,
        "free": free_cpu,
        "used_percentage": used_cpu_percentage,
    }


def _get_ram_usage(cluster, logger: Logger) -> dict[str, str]:
    if isinstance(cluster, vim.ClusterComputeResource):
        usage_summary = cluster.GetResourceUsage()
        logger.info(f"Cluster usage summary: {usage_summary}")

        total_memory_capacity = units_converter.format_bytes(
            usage_summary.memCapacityMB, prefix=units_converter.PREFIX_MB
        )
        used_memory = units_converter.format_bytes(
            usage_summary.memUsedMB, prefix=units_converter.PREFIX_MB
        )
        free_memory = units_converter.format_bytes(
            usage_summary.memCapacityMB - usage_summary.memUsedMB,
            prefix=units_converter.PREFIX_MB,
        )
        used_memory_percentage = round(
            usage_summary.memUsedMB / usage_summary.memCapacityMB * 100
        )

    else:
        logger.info(f"Host usage stats: {cluster.summary.quickStats}")

        used_memory_bytes = (
            cluster.summary.quickStats.overallMemoryUsage
            * units_converter.BASE_10
            * units_converter.BASE_10
        )
        total_memory_capacity = units_converter.format_bytes(
            cluster.hardware.memorySize
        )
        used_memory = units_converter.format_bytes(used_memory_bytes)
        free_memory = units_converter.format_bytes(
            cluster.hardware.memorySize - used_memory_bytes
        )
        used_memory_percentage = round(
            used_memory_bytes / cluster.hardware.memorySize * 100
        )

    return {
        "capacity": total_memory_capacity,
        "used": used_memory,
        "free": free_memory,
        "used_percentage": used_memory_percentage,
    }


def get_cluster_usage(
    vcenter_client: VCenterAPIClient,
    resource_config: VCenterResourceConfig,
    datastore_name: str,
    logger: Logger,
):
    dc = vcenter_client.get_dc(resource_config.default_datacenter)
    cluster = vcenter_client.get_cluster(resource_config.vm_cluster, dc)
    logger.info(f"Found cluster/host {cluster}")

    return json.dumps(
        {
            "datastore": _get_datastore_usage(
                vcenter_client,
                resource_config,
                datastore_name,
                logger,
            ),
            "cpu": _get_cpu_usage(cluster, logger),
            "ram": _get_ram_usage(cluster, logger),
        }
    )
