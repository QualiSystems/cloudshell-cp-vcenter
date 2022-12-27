from unittest.mock import Mock

import pytest

from cloudshell.cp.vcenter.handlers.config_spec_handler import (
    CannotChangeLinkedDisk,
    ConfigSpecHandler,
)
from cloudshell.cp.vcenter.models.base_deployment_app import HddSpec


@pytest.mark.parametrize(
    ("cpu", "ram", "hdd", "spec"),
    (
        (None, None, "1:30", ConfigSpecHandler(None, None, [HddSpec(1, 30)])),
        (1, 2, "1:30", ConfigSpecHandler(1, 2, [HddSpec(1, 30)])),
        (
            None,
            None,
            "1:30;Hard Disk 2:45",
            ConfigSpecHandler(None, None, [HddSpec(1, 30), HddSpec(2, 45)]),
        ),
        (
            None,
            None,
            "3:30;2:10",
            ConfigSpecHandler(None, None, [HddSpec(3, 30), HddSpec(2, 10)]),
        ),
    ),
)
def test_from_string(cpu, ram, hdd, spec):
    assert ConfigSpecHandler.from_strings(cpu, ram, hdd) == spec


def test_validate_spec_for_vm():
    vm = Mock(disks=[Mock(index=1, has_parent=False)])
    spec = ConfigSpecHandler(None, None, [HddSpec(1, 10)])

    spec._validate_hdd_spec(vm)


def test_validate_spec_for_vm_linked_disk():
    vm = Mock(disks=[Mock(index=1, has_parent=True)])
    spec = ConfigSpecHandler(None, None, [HddSpec(1, 10)])

    with pytest.raises(CannotChangeLinkedDisk):
        spec._validate_hdd_spec(vm)
