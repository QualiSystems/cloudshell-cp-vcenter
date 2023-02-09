from __future__ import annotations

from abc import abstractmethod
from collections.abc import Collection
from typing import TYPE_CHECKING

from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.cluster_specs import (
    AffinityRule,
    AffinityRuleNotFound,
    AffinityRulesHasConflicts,
    ClusterConfigSpec,
)
from cloudshell.cp.vcenter.handlers.datastore_handler import DatastoreHandler
from cloudshell.cp.vcenter.handlers.managed_entity_handler import (
    ManagedEntityHandler,
    ManagedEntityNotFound,
)
from cloudshell.cp.vcenter.handlers.network_handler import HostPortGroupHandler
from cloudshell.cp.vcenter.handlers.resource_pool import ResourcePoolHandler
from cloudshell.cp.vcenter.handlers.si_handler import ResourceInUse
from cloudshell.cp.vcenter.handlers.switch_handler import (
    PortGroupExists,
    VSwitchHandler,
    VSwitchNotFound,
)
from cloudshell.cp.vcenter.handlers.task import Task
from cloudshell.cp.vcenter.handlers.vcenter_path import VcenterPath
from cloudshell.cp.vcenter.utils.units_converter import (
    BASE_10,
    BASE_SI,
    PREFIX_MB,
    PREFIX_MHZ,
    UsageInfo,
    format_bytes,
    format_hertz,
)

if TYPE_CHECKING:
    from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler


class ClusterNotFound(BaseVCenterException):
    def __init__(self, dc: DcHandler, name: str):
        self.dc = dc
        self.name = name
        super().__init__(f"Cluster with name '{name}' not found in the {dc}")


class HostNotFound(BaseVCenterException):
    def __init__(self, cluster: ClusterHandler, name: str):
        self.cluster = cluster
        self.name = name
        super().__init__(f"Host with name '{name}' not found in the {cluster}")


class BasicComputeEntityHandler(ManagedEntityHandler):
    @property
    def datastores(self) -> list[DatastoreHandler]:
        return [DatastoreHandler(store, self.si) for store in self._vc_obj.datastore]

    @property
    @abstractmethod
    def cpu_usage(self) -> UsageInfo:
        ...

    @property
    @abstractmethod
    def ram_usage(self) -> UsageInfo:
        ...

    @abstractmethod
    def get_v_switch(self, name: str) -> VSwitchHandler:
        ...


class ClusterHandler(BasicComputeEntityHandler):
    _vc_obj: vim.ComputeResource | vim.ClusterComputeResource

    @property
    def cpu_usage(self) -> UsageInfo:
        usage = self._vc_obj.GetResourceUsage()
        capacity = usage.cpuCapacityMHz
        used = usage.cpuUsedMHz
        return UsageInfo(
            capacity=format_hertz(capacity, prefix=PREFIX_MHZ),
            used=format_hertz(used, prefix=PREFIX_MHZ),
            free=format_hertz(capacity - used, prefix=PREFIX_MHZ),
            used_percentage=str(round(used / capacity * 100)),
        )

    @property
    def ram_usage(self) -> UsageInfo:
        usage = self._vc_obj.GetResourceUsage()
        capacity = usage.memCapacityMB
        used = usage.memUsedMB
        return UsageInfo(
            capacity=format_bytes(capacity, prefix=PREFIX_MB),
            used=format_bytes(used, prefix=PREFIX_MB),
            free=format_bytes(capacity - used, prefix=PREFIX_MB),
            used_percentage=str(round(used / capacity * 100)),
        )

    @property
    def hosts(self) -> list[HostHandler]:
        return [HostHandler(host, self.si) for host in self._vc_obj.host]

    @property
    def _class_name(self) -> str:
        return "Cluster"

    def get_host(self, name: str) -> HostHandler:
        for host in self.hosts:
            if host.name == name:
                return host
        raise HostNotFound(self, name)

    def get_resource_pool(self, path: str | None) -> ResourcePoolHandler:
        rp = ResourcePoolHandler(self._vc_obj.resourcePool, self.si)
        for name in VcenterPath(path or ""):
            rp = rp.get_resource_pool(name)
        return rp

    def get_v_switch(self, name: str) -> VSwitchHandler:
        for host in self.hosts:
            try:
                v_switch = host.get_v_switch(name)
            except VSwitchNotFound:
                pass
            else:
                return v_switch
        raise VSwitchNotFound(self, name)

    def get_affinity_rule(self, name: str) -> AffinityRule:
        for rule in self._vc_obj.configuration.rule:
            if rule.name == name:
                return AffinityRule.from_vcenter_rule(rule, self.si)
        raise AffinityRuleNotFound(name, self)

    def add_affinity_rule(self, *rules: AffinityRule) -> list[AffinityRule]:
        assert all(rule.new for rule in rules)
        return self._add_rules(rules)

    def update_affinity_rule(self, *rules: AffinityRule) -> list[AffinityRule]:
        assert all(not rule.new for rule in rules)
        return self._add_rules(rules)

    def reconfigure(self, spec: ClusterConfigSpec) -> None:
        # Required Privileges Host.Inventory.EditCluster
        vc_task = self._vc_obj.ReconfigureEx(
            spec.get_vc_obj(),
            # if modify is False all skipped properties will be reset to default
            modify=True,
        )
        task = Task(vc_task, self.logger)
        task.wait()

    def _add_rules(self, rules: Collection[AffinityRule]) -> list[AffinityRule]:
        spec = ClusterConfigSpec(rules=rules)
        self.reconfigure(spec)
        new_rules = [self.get_affinity_rule(rule.name) for rule in rules]
        not_enabled = [rule for rule in new_rules if not rule.enabled]
        if not_enabled:
            raise AffinityRulesHasConflicts(not_enabled)
        return new_rules


class HostHandler(BasicComputeEntityHandler):
    _vc_obj: vim.HostSystem

    @property
    def cluster(self) -> ClusterHandler:
        return ClusterHandler(self._vc_obj.parent, self.si)

    @property
    def cpu_usage(self) -> UsageInfo:
        used = self._vc_obj.summary.quickStats.overallCpuUsage * BASE_SI * BASE_SI
        capacity = (
            self._vc_obj.hardware.cpuInfo.hz * self._vc_obj.hardware.cpuInfo.numCpuCores
        )
        return UsageInfo(
            capacity=format_hertz(capacity),
            used=format_hertz(used),
            free=format_hertz(capacity - used),
            used_percentage=str(round(used / capacity * 100)),
        )

    @property
    def ram_usage(self) -> UsageInfo:
        used = self._vc_obj.summary.quickStats.overallMemoryUsage * BASE_10 * BASE_10
        capacity = self._vc_obj.hardware.memorySize
        return UsageInfo(
            capacity=format_bytes(capacity),
            used=format_bytes(used),
            free=format_bytes(capacity, used),
            used_percentage=str(round(used / capacity * 100)),
        )

    @property
    def port_groups(self) -> list[HostPortGroupHandler]:
        return [
            HostPortGroupHandler(pg, self)
            for pg in self._vc_obj.config.network.portgroup
        ]

    @property
    def _class_name(self) -> str:
        return "Host"

    def get_resource_pool(self, path: str | None) -> ResourcePoolHandler:
        return self.cluster.get_resource_pool(path)

    def get_v_switch(self, name: str) -> VSwitchHandler:
        for v_switch in self._vc_obj.config.network.vswitch:
            if v_switch.name == name:
                return VSwitchHandler(v_switch, self)
        raise VSwitchNotFound(self, name)

    def remove_port_group(self, name: str):
        try:
            self._vc_obj.configManager.networkSystem.RemovePortGroup(name)
        except (vim.fault.NotFound, ManagedEntityNotFound):
            pass
        except vim.fault.ResourceInUse:
            raise ResourceInUse(name)

    def add_port_group(self, port_group_spec):
        try:
            self._vc_obj.configManager.networkSystem.AddPortGroup(port_group_spec)
        except vim.fault.AlreadyExists:
            raise PortGroupExists(port_group_spec.name)
