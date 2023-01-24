from unittest.mock import Mock

import pytest

from cloudshell.cp.vcenter.handlers.vnic_handler import Vnic


@pytest.fixture
def vc_vnic1():
    return Mock(deviceInfo=Mock(label="Network adapter 1"))


def test_representation(vc_vnic1, vm):
    vm._vc_obj.name = "vm_name"
    Vnic.vm = vm
    vnic = Vnic(vc_vnic1)

    assert str(vnic) == "Network adapter 1 of the VM 'vm_name'"
    assert repr(vnic) == "Network adapter 1 of the VM 'vm_name'"
