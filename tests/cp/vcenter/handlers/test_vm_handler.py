from unittest.mock import Mock

import pytest
from pyVmomi import vim

from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler
from cloudshell.cp.vcenter.handlers.vnic_handler import VnicHandler, VnicNotFound


@pytest.fixture
def vc_vm():
    return Mock(
        config=Mock(
            hardware=Mock(
                device=[
                    Mock(
                        spec=vim.vm.device.VirtualEthernetCard,
                        macAddress="00:50:56:8D:2E:0E",
                        deviceInfo=Mock(
                            label="Network adapter 1",
                            summary="VM Network",
                        ),
                    ),
                    Mock(
                        spec=vim.vm.device.VirtualEthernetCard,
                        macAddress="00:50:56:8D:2E:0F",
                        deviceInfo=Mock(
                            label="Network adapter 2",
                            summary="VM Network",
                        ),
                    ),
                    Mock(
                        spec=vim.vm.device.VirtualEthernetCard,
                        macAddress="00:50:56:8D:2E:10",
                        deviceInfo=Mock(
                            label="Network adapter 3",
                            summary="VM Network",
                        ),
                    ),
                ]
            )
        )
    )


@pytest.fixture
def vm(vc_vm, si):
    return VmHandler(vc_vm, si)


def test_get_vnic(vm):
    vnic2 = vm.get_vnic("Network adapter 2")
    assert isinstance(vnic2, VnicHandler)
    assert vnic2.label == "Network adapter 2"
    assert vnic2.mac_address == "00:50:56:8D:2E:0F"

    vnic3 = vm.get_vnic("Network adapter 3")
    assert isinstance(vnic3, VnicHandler)
    assert vnic3.label == "Network adapter 3"
    assert vnic3.mac_address == "00:50:56:8D:2E:10"


def test_not_found_vnic(vm):
    with pytest.raises(VnicNotFound):
        vm.get_vnic("Network adapter 4")
    with pytest.raises(VnicNotFound):
        vm.get_vnic("4")
