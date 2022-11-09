from unittest.mock import Mock

import pytest

from cloudshell.cp.vcenter.flows.deploy_vm.commands import CloneVMCommand


@pytest.fixture
def vm_template():
    return Mock()


@pytest.fixture
def vm_folder():
    return Mock()


@pytest.fixture
def command(vm_template, vm_folder, logger, cancellation_manager):
    return CloneVMCommand(
        vm_template=vm_template,
        rollback_manager=Mock(),
        cancellation_manager=cancellation_manager,
        vm_name="name",
        vm_storage=Mock(),
        vm_folder=vm_folder,
        logger=logger,
    )


def test_clone(command, vm_template, vm_folder):
    result = command.execute()

    vm_template.clone_vm.assert_called_once()
    assert result == vm_template.clone_vm()
    assert vm_folder.mock_calls == []


def test_clone_failed(command, vm_template, vm_folder):
    vm_template.clone_vm.side_effect = Exception()

    with pytest.raises(Exception):
        command.execute()

    vm_folder.destroy.assert_called_once()


def test_rollback(command, vm_folder):
    cloned_vm = Mock()
    command._cloned_vm = cloned_vm

    command.rollback()

    cloned_vm.delete.assert_called_once()
    vm_folder.destroy.assert_called_once()
