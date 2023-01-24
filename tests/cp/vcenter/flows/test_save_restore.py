import json
from unittest.mock import Mock, call, patch

import pytest

from cloudshell.cp.core.request_actions.models import Attribute, SaveApp, SaveAppParams

from cloudshell.cp.vcenter.constants import VM_FROM_LINKED_CLONE_DEPLOYMENT_PATH
from cloudshell.cp.vcenter.flows.save_restore_app import (
    SNAPSHOT_NAME,
    SaveRestoreAppFlow,
)
from cloudshell.cp.vcenter.handlers.vcenter_path import VcenterPath
from cloudshell.cp.vcenter.handlers.vm_handler import PowerState
from cloudshell.cp.vcenter.models.base_deployment_app import (
    VCenterVMFromCloneDeployAppAttributeNames,
)


@pytest.fixture
def flow(resource_conf, cs_api, cancellation_manager, logger, si_handler):
    flow = SaveRestoreAppFlow(resource_conf, cs_api, cancellation_manager, logger)
    return flow


@pytest.fixture
def dc_handler(si_handler):
    dc = Mock(name="DC")
    dc.si = si_handler
    dc_class = Mock(return_value=dc, get_dc=Mock(return_value=dc))
    p = patch("cloudshell.cp.vcenter.flows.save_restore_app.DcHandler", dc_class)
    p.start()
    yield dc
    p.stop()


@pytest.fixture
def si_handler():
    si = Mock(name="SI")
    si_class = Mock(return_value=si, from_config=Mock(return_value=si))
    p = patch("cloudshell.cp.vcenter.flows.save_restore_app.SiHandler", si_class)
    p.start()
    yield si
    p.stop()


@pytest.fixture
def vm(dc_handler):
    vm_name = "VM name"
    vm_path = f"folder/{vm_name}"
    vm = Mock(name=vm_name, vm_uuid="VM UUID", path=vm_path)
    vm.name = vm_name

    def power_on(*args, **kwargs):
        vm.power_state = PowerState.ON

    def power_off(*args, **kwargs):
        vm.power_state = PowerState.OFF

    vm.power_state = PowerState.ON
    vm.power_on.side_effect = power_on
    vm.power_off.side_effect = power_off

    dc_handler.get_vm_by_uuid.return_value = vm
    return vm


def _get_save_action(
    vm_uuid: str, behavior_during_save: str, action_id: str = "action id"
) -> SaveApp:
    attr_names = VCenterVMFromCloneDeployAppAttributeNames
    return SaveApp(
        action_id,
        SaveAppParams(
            saveDeploymentModel="",
            savedSandboxId="",
            sourceVmUuid=vm_uuid,
            sourceAppName="",
            deploymentPathAttributes=[
                Attribute(
                    attributeName=attr_names.behavior_during_save,
                    attributeValue=behavior_during_save,
                ),
                Attribute(
                    attributeName=attr_names.vm_resource_pool,
                    attributeValue="",
                ),
                Attribute(
                    attributeName=attr_names.vm_cluster,
                    attributeValue="",
                ),
            ],
        ),
    )


def test_save(flow, vm, dc_handler, resource_conf, logger):
    vm_uuid = vm.uuid
    action_id = "action id"
    action = _get_save_action(vm_uuid, "Inherited", action_id)
    resource_conf.behavior_during_save = "Power Off"
    cloned_vm_name = f"Clone of {vm.name}"
    cloned_vm = Mock(name=cloned_vm_name, path=f"folder/{cloned_vm_name}", uuid="uuid")
    cloned_vm.name = cloned_vm_name
    vm.clone_vm.return_value = cloned_vm

    result = flow.save_apps([action])

    attr_names = VCenterVMFromCloneDeployAppAttributeNames
    expected_result = {
        "driverResponse": {
            "actionResults": [
                {
                    "actionId": action_id,
                    "additionalData": [],
                    "artifacts": [
                        {
                            "artifactName": cloned_vm.name,
                            "artifactRef": cloned_vm.uuid,
                        }
                    ],
                    "errorMessage": "",
                    "infoMessage": "",
                    "saveDeploymentModel": VM_FROM_LINKED_CLONE_DEPLOYMENT_PATH,
                    "savedEntityAttributes": [
                        {
                            "attributeName": attr_names.vcenter_vm,
                            "attributeValue": str(cloned_vm.path),
                        },
                        {
                            "attributeName": attr_names.vcenter_vm_snapshot,
                            "attributeValue": SNAPSHOT_NAME,
                        },
                        {
                            "attributeName": attr_names.hostname,
                            "attributeValue": None,
                        },
                        {
                            "attributeName": attr_names.private_ip,
                            "attributeValue": None,
                        },
                        {
                            "attributeName": attr_names.customization_spec,
                            "attributeValue": None,
                        },
                    ],
                    "success": True,
                    "type": "SaveApp",
                }
            ]
        }
    }
    assert json.loads(result) == expected_result

    save_apps_folder_path = VcenterPath(f"{resource_conf.vm_location}/Saved Sandboxes")
    expected_dc_calls = [
        call.get_vm_by_uuid(vm_uuid),
        call.get_compute_entity(resource_conf.vm_cluster),
        call.get_datastore(resource_conf.saved_sandbox_storage),
        call.get_or_create_vm_folder(save_apps_folder_path),
    ]
    assert dc_handler.method_calls == expected_dc_calls

    expected_vm_calls = [
        call.power_off(soft=False),
        call.clone_vm(
            vm_name=cloned_vm_name,
            vm_storage=dc_handler.get_datastore(),
            vm_folder=dc_handler.get_or_create_vm_folder(),
            vm_resource_pool=dc_handler.get_compute_entity().get_resource_pool(),
            snapshot=None,
            config_spec=None,
            on_task_progress=flow._on_task_progress,
        ),
        call.power_on(on_task_progress=flow._on_task_progress),
    ]
    assert vm.method_calls == expected_vm_calls
