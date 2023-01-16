from functools import cached_property
from logging import Logger

from attrs import define
from pyVim.task import WaitForTask
from pyVmomi import vim

from cloudshell.cp.vcenter.handlers.cluster_handler import BasicComputeEntityHandler
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig


@define(slots=False)
class AffinityRulesFlow:
    resource_conf: VCenterResourceConfig
    logger: Logger

    @cached_property
    def si(self) -> SiHandler:
        return SiHandler.from_config(self.resource_conf, self.logger)

    @cached_property
    def dc(self) -> DcHandler:
        return DcHandler.get_dc(self.resource_conf.default_datacenter, self.si)

    @cached_property
    def cluster(self) -> BasicComputeEntityHandler:
        return self.dc.get_compute_entity(self.resource_conf.vm_cluster)

    def add_vms_to_affinity_rule(
        self, vm_paths: list[str], affinity_rule_id: str | None = None
    ) -> str:
        # todo it can be executed only for cluster, compute resource is not a case
        vms = [self.dc.get_vm_by_path(path) for path in vm_paths]
        vc_vms = [vm._entity for vm in vms]

        rule = vim.cluster.AffinityRuleSpec(
            # todo check affinity rules with the same name
            vm=vc_vms,
            enabled=True,
            mandatory=True,
            name="affinity-between-2-vms",
        )
        ruleSpec = vim.cluster.RuleSpec(info=rule, operation="add")
        configSpec = vim.cluster.ConfigSpecEx(rulesSpec=[ruleSpec])
        WaitForTask(cluster.ReconfigureEx(configSpec, modify=True))  # noqa
