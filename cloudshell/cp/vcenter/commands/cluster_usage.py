import json

from pyVmomi import vim

from cloudshell.cp.vcenter.common.utilites import units_converter


class GetClusterUsageCommand(object):
    def __init__(self, pv_service):
        """

        :type pv_service: cloudshell.cp.vcenter.common.vcenter.vmomi_service.pyVmomiService
        """
        self.pv_service = pv_service

    def _get_datastore_usage(self, si, logger, vcenter_data_model, datastore_name):
        """

        :param si:
        :param logger:
        :param vcenter_data_model:
        :param datastore_name:
        :return:
        """
        datastore_name = datastore_name or vcenter_data_model.vm_storage

        logger.info(f"Getting Datastore '{datastore_name}'... ")
        datastore = self.pv_service.get_obj(
            si.content, [[vim.Datastore]], datastore_name
        )

        if not datastore:
            logger.info(
                f"Unable to find Datastore '{datastore_name}'. "
                f"Trying to find Storage Pod with same name..."
            )

            datastore = self.pv_service.get_obj(
                si.content, [[vim.StoragePod]], datastore_name
            )

            if datastore:
                datastore = sorted(
                    datastore.childEntity,
                    key=lambda data: data.summary.freeSpace,
                    reverse=True,
                )[0]

        if not datastore:
            raise Exception(f"Unable to find Datastore '{datastore_name}'")

        used_space = datastore.summary.capacity - datastore.summary.freeSpace

        return {
            "capacity": units_converter.format_bytes(datastore.summary.capacity),
            "used": units_converter.format_bytes(used_space),
            "free": units_converter.format_bytes(datastore.summary.freeSpace),
            "used_percentage": round(used_space / datastore.summary.capacity * 100),
        }

    def _get_cpu_usage(self, si, logger, cluster):
        """

        :param si:
        :param logger:
        :param cluster:
        :return:
        """
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

    def _get_ram_usage(self, si, logger, cluster):
        """

        :param si:
        :param logger:
        :param cluster:
        :return:
        """
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

    def get_cluster_usage(self, si, logger, vcenter_data_model, datastore_name):
        """

        :param si:
        :param logger:
        :param vcenter_data_model:
        :param datastore_name:
        :return:
        """
        accepted_types = [
            [vim.ClusterComputeResource],
            [vim.HostSystem],
        ]

        cluster = self.pv_service.get_obj(
            content=si.content,
            vimtypes=accepted_types,
            name=vcenter_data_model.vm_cluster,
        )
        logger.info(f"Found cluster/host {cluster}")

        return json.dumps(
            {
                "datastore": self._get_datastore_usage(
                    si=si,
                    logger=logger,
                    vcenter_data_model=vcenter_data_model,
                    datastore_name=datastore_name,
                ),
                "cpu": self._get_cpu_usage(si=si, logger=logger, cluster=cluster),
                "ram": self._get_ram_usage(si=si, logger=logger, cluster=cluster),
            }
        )
