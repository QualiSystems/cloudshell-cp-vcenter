from __future__ import annotations

from functools import cached_property
from logging import Logger

from attrs import define

from cloudshell.cp.vcenter.handlers.cluster_handler import ClusterHandler
from cloudshell.cp.vcenter.handlers.cluster_specs import (
    AffinityRule,
    AffinityRuleNotFound,
)
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


@define(slots=False)
class AffinityRulesFlow:
    resource_conf: VCenterResourceConfig
    reservation_id: str
    logger: Logger

    @cached_property
    def si(self) -> SiHandler:
        return SiHandler.from_config(self.resource_conf, self.logger)

    @cached_property
    def dc(self) -> DcHandler:
        return DcHandler.get_dc(self.resource_conf.default_datacenter, self.si)

    @cached_property
    def cluster(self) -> ClusterHandler:
        # affinity rules can be added only for cluster,
        # compute resource is not supported
        return self.dc.get_cluster(self.resource_conf.vm_cluster)

    def add_vms_to_affinity_rule(
        self, vm_uuids: list[str], affinity_rule_name: str | None = None
    ) -> str:
        vms = [self.dc.get_vm_by_uuid(uuid) for uuid in vm_uuids]

        if affinity_rule_name:
            self._add_vms_to_existing_affinity_rule(vms, affinity_rule_name)
        else:
            affinity_rule_name = self._create_new_affinity_rule(vms)
        return affinity_rule_name

    def _create_new_affinity_rule(self, vms: list[VmHandler]) -> str:
        rule_name = self._get_new_affinity_rule_name()
        rule = AffinityRule(
            name=rule_name,
            enabled=True,
            mandatory=True,
            vms=vms,
        )
        self.cluster.add_affinity_rule(rule)
        return rule_name

    def _get_new_affinity_rule_name(self) -> str:
        name = self.reservation_id
        index = 1
        while True:
            try:
                self.cluster.get_affinity_rule(name)
            except AffinityRuleNotFound:
                break
            else:
                name = f"{self.reservation_id} ({index})"
                index += 1
        return name

    def _add_vms_to_existing_affinity_rule(
        self, vms: list[VmHandler], affinity_rule_name: str
    ) -> None:
        rule = self.cluster.get_affinity_rule(affinity_rule_name)
        rule.add_vm(*vms)
        self.cluster.update_affinity_rule(rule)
