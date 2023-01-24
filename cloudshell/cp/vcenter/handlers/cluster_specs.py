from __future__ import annotations

from collections.abc import Collection
from typing import TYPE_CHECKING

from attrs import define, field, setters
from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException

if TYPE_CHECKING:
    from cloudshell.cp.vcenter.handlers.cluster_handler import ClusterHandler
    from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
    from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler


class AffinityRuleNotFound(BaseVCenterException):
    def __init__(self, name: str, cluster: ClusterHandler):
        self.name = name
        self.cluster = cluster
        super().__init__(f"Affinity rule with name '{name}' not found in the {cluster}")


class AffinityRulesHasConflicts(BaseVCenterException):
    def __init__(self, rules: list[AffinityRule]):
        self.rules = rules
        super().__init__(f"{rules} has conflicts with other rules or with each other")


@define(str=False)
class AffinityRule:
    name: str
    enabled: bool
    mandatory: bool
    vms: list[VmHandler]
    _orig_vc_obj: vim.cluster.AffinityRule | None = field(
        default=None, repr=False, on_setattr=setters.frozen
    )

    def __str__(self) -> str:
        return f"Affinity rule '{self.name}'"

    @classmethod
    def from_vcenter_rule(
        cls, rule: vim.cluster.AffinityRule, si: SiHandler
    ) -> AffinityRule:
        from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler

        self = cls(
            name=rule.name,
            enabled=rule.enabled,
            mandatory=rule.mandatory,
            vms=[VmHandler(vm, si) for vm in rule.vm],
            orig_vc_obj=rule,
        )
        return self

    @property
    def new(self) -> bool:
        return self._orig_vc_obj is None

    @property
    def rule_spec(self) -> vim.cluster.RuleSpec:
        operation = "add" if self.new else "edit"
        return vim.cluster.RuleSpec(info=self.get_vc_obj(), operation=operation)

    def get_vc_obj(self) -> vim.cluster.AffinityRuleSpec:
        vc_vms = [vm.get_vc_obj() for vm in self.vms]
        if self.new:
            spec = vim.cluster.AffinityRuleSpec(
                vm=vc_vms,
                enabled=self.enabled,
                mandatory=self.mandatory,
                name=self.name,
            )
        else:
            spec = self._orig_vc_obj
            spec.vm = vc_vms
            spec.enabled = self.enabled
            spec.mandatory = self.mandatory
            spec.name = self.name
        return spec

    def add_vm(self, *vms: VmHandler) -> None:
        for vm in vms:
            if vm not in self.vms:
                self.vms.append(vm)


@define
class ClusterConfigSpec:
    rules: Collection[AffinityRule] | None = None

    def get_vc_obj(self) -> vim.cluster.ConfigSpecEx:
        rules_spec = [rule.rule_spec for rule in self.rules]
        spec = vim.cluster.ConfigSpecEx(rulesSpec=rules_spec)
        return spec
