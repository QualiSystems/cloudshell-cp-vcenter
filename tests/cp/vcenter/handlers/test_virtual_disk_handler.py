from unittest.mock import Mock

import pytest

from cloudshell.cp.vcenter.handlers.virtual_disk_handler import VirtualDisk


@pytest.fixture
def disk1():
    return Mock(deviceInfo=Mock(label="Disk 1"))


def test_representation(disk1, vm):
    vm._vc_obj.name = "vm_name"
    VirtualDisk.vm = vm
    vnic = VirtualDisk(disk1)

    assert str(vnic) == "Disk 1 of the VM 'vm_name'"
    assert repr(vnic) == "Disk 1 of the VM 'vm_name'"
