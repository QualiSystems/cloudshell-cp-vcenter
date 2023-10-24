from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from pyVmomi import vim

from cloudshell.cp.vcenter.flows.affinity_rules_flow import AffinityRulesFlow

RESERVATION_ID = "reservation_id"


@pytest.fixture()
def flow(si, resource_conf):
    return AffinityRulesFlow(si, resource_conf, RESERVATION_ID)


@pytest.fixture()
def cluster_cfg_spec(monkeypatch):
    m = Mock()
    monkeypatch.setattr(vim.cluster, "ConfigSpecEx", m)
    return m


@pytest.fixture
def cluster_rule_spec(monkeypatch):
    m = Mock()
    monkeypatch.setattr(vim.cluster, "RuleSpec", m)
    return m


@pytest.fixture
def cluster_affinity_rule_spec(monkeypatch):
    m = Mock()
    monkeypatch.setattr(vim.cluster, "AffinityRuleSpec", m)
    return m


@pytest.fixture
def wait_for_task():
    with patch("cloudshell.cp.vcenter.handlers.task.WaitForTask") as m:
        yield m


def test_add_vms_to_existed_rule(
    flow,
    dc,
    cluster,
    cluster_cfg_spec,
    vc_si,
    cluster_rule_spec,
    wait_for_task,
    vm_mock,
):
    # add existing VMs
    with vc_si.t_preparing():
        vc_vm1 = vm_mock(name="vm1", uuid="vm1_uuid")
        vc_vm2 = vm_mock(name="vm2", uuid="vm2_uuid")
        vc_si.t_add_vm(vc_vm1)
        vc_si.t_add_vm(vc_vm2)

    # add existing affinity rule
    rule1 = Mock(vm=[vc_vm1], enabled=True, mandatory=True)
    rule1.name = "rule1"
    cluster.get_vc_obj().configuration.rule = [rule1]

    flow.add_vms_to_affinity_rule([vc_vm1.uuid, vc_vm2.uuid], rule1.name)

    assert rule1.vm == [vc_vm1, vc_vm2]
    cluster_rule_spec.assert_called_once_with(info=rule1, operation="edit")
    cluster_cfg_spec.assert_called_once_with(rulesSpec=[cluster_rule_spec()])
    cluster.get_vc_obj().ReconfigureEx.assert_called_once_with(
        cluster_cfg_spec(), modify=True
    )


def test_add_vms_to_new_rule_with_rule_name(
    flow,
    dc,
    cluster,
    cluster_cfg_spec,
    vc_si,
    cluster_rule_spec,
    wait_for_task,
    cluster_affinity_rule_spec,
    vm_mock,
):
    # add existing VMs
    with vc_si.t_preparing():
        vc_vm1 = vm_mock(name="vm1", uuid="vm1_uuid")
        vc_vm2 = vm_mock(name="vm2", uuid="vm2_uuid")
        vc_si.t_add_vm(vc_vm1)
        vc_si.t_add_vm(vc_vm2)
    cluster.get_vc_obj().configuration.rule = []

    def after_adding_rule(*args, **kwargs):
        rule1 = Mock(vm=[vc_vm1, vc_vm2], enabled=True, mandatory=True)
        rule1.name = "rule1"
        cluster.get_vc_obj().configuration.rule = [rule1]

    wait_for_task.side_effect = after_adding_rule

    flow.add_vms_to_affinity_rule([vc_vm1.uuid, vc_vm2.uuid], "rule1")

    cluster_affinity_rule_spec.assert_called_once_with(
        vm=[vc_vm1, vc_vm2], enabled=True, mandatory=True, name="rule1"
    )
    cluster_rule_spec.assert_called_once_with(
        info=cluster_affinity_rule_spec(),
        operation="add",
    )
    cluster_cfg_spec.assert_called_once_with(rulesSpec=[cluster_rule_spec()])
    cluster.get_vc_obj().ReconfigureEx.assert_called_once_with(
        cluster_cfg_spec(), modify=True
    )


def test_create_rule_with_new_name(
    flow,
    dc,
    cluster,
    cluster_cfg_spec,
    vc_si,
    cluster_rule_spec,
    wait_for_task,
    cluster_affinity_rule_spec,
    vm_mock,
):
    # add existing VMs
    with vc_si.t_preparing():
        vc_vm1 = vm_mock(name="vm1", uuid="vm1_uuid")
        vc_vm2 = vm_mock(name="vm2", uuid="vm2_uuid")
        vc_si.t_add_vm(vc_vm1)
        vc_si.t_add_vm(vc_vm2)

    # add existing affinity rule
    rule1 = Mock(vm=[vc_vm1], enabled=True, mandatory=True)
    rule1.name = RESERVATION_ID
    cluster.get_vc_obj().configuration.rule = [rule1]
    rule2 = Mock(vm=[vc_vm1, vc_vm2], enabled=True, mandatory=True)
    rule2.name = f"{RESERVATION_ID} (1)"

    def after_adding_rule(*args, **kwargs):
        cluster.get_vc_obj().configuration.rule = [rule1, rule2]

    wait_for_task.side_effect = after_adding_rule

    flow.add_vms_to_affinity_rule([vc_vm1.uuid, vc_vm2.uuid])

    cluster_affinity_rule_spec.assert_called_once_with(
        vm=[vc_vm1, vc_vm2], enabled=True, mandatory=True, name=f"{RESERVATION_ID} (1)"
    )
    cluster_rule_spec.assert_called_once_with(
        info=cluster_affinity_rule_spec(), operation="add"
    )
    cluster_cfg_spec.assert_called_once_with(rulesSpec=[cluster_rule_spec()])
    cluster.get_vc_obj().ReconfigureEx.assert_called_once_with(
        cluster_cfg_spec(), modify=True
    )
