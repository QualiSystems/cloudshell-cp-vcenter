import sys
from unittest import TestCase

from pyVmomi import vim

from cloudshell.cp.vcenter.common.vcenter.vmomi_service import pyVmomiService
from cloudshell.cp.vcenter.network.vnic.vnic_service import VNicService

if sys.version_info >= (3, 0):
    from unittest.mock import MagicMock, create_autospec
else:
    from mock import MagicMock, create_autospec


class TestNetwork(TestCase):
    def setUp(self):
        pass

    def test_vnic_reconfig_task(self):
        vm = MagicMock()
        vm.ReconfigVM_Task = lambda x: isinstance(x, vim.vm.ConfigSpec)

        api_wrapper = pyVmomiService(MagicMock, MagicMock(), MagicMock(), MagicMock())
        res = api_wrapper.vm_reconfig_task(vm, [])
        self.assertTrue(res)

    def test_compose_empty(self):
        nicspec = VNicService.vnic_compose_empty()
        self.assertTrue(isinstance(nicspec, vim.vm.device.VirtualDeviceSpec))
        self.assertTrue(isinstance(nicspec.device, vim.vm.device.VirtualVmxnet3))
        self.assertTrue(
            isinstance(
                nicspec.device.connectable, vim.vm.device.VirtualDevice.ConnectInfo
            )
        )

    def test_device_attahed_to_network_standard(self):

        self.assertFalse(VNicService.device_is_attached_to_network(None, None))

        network_name = "TEST"
        device = MagicMock()
        device.backing = MagicMock()
        device.backing.network = MagicMock()
        device.backing.network.name = network_name
        self.assertTrue(VNicService.device_is_attached_to_network(device, network_name))

        network = MagicMock(spec=vim.Network)
        network.name = "xnet"
        nicspec = MagicMock()

        nicspec.device = device
        res = VNicService.vnic_attach_to_network_standard(
            nicspec=nicspec, network=network, logger=MagicMock()
        )
        self.assertEqual(res.device.backing.network.name, "xnet")

    def test_device_attahed_to_network_distributed(self):
        network_name = "PORT-GROUP"
        device = MagicMock()
        device.backing = MagicMock()
        device.backing.port = MagicMock()
        hasattr(device.backing, "network")
        del device.backing.network
        device.backing.port.portgroupKey = network_name
        self.assertTrue(VNicService.device_is_attached_to_network(device, network_name))

        port_group = MagicMock(spec=vim.dvs.DistributedVirtualPortgroup)
        port_group.key = "group_net"
        port_group.config.distributedVirtualSwitch.uuid = "6686"
        nicspec = MagicMock()

        nicspec.device = device
        res = VNicService.vnic_attach_to_network_distributed(
            nicspec=nicspec, port_group=port_group, logger=MagicMock()
        )
        self.assertEqual(res.device.backing.port.portgroupKey, "group_net")

    def test_xx(self):
        vm = MagicMock()
        vm.ReconfigVM_Task = lambda x: isinstance(x, vim.vm.ConfigSpec)
        nicspec = MagicMock()
        res = VNicService.vnic_add_to_vm_task(
            nicspec=nicspec, virtual_machine=vm, logger=MagicMock()
        )
        self.assertIsNone(res)

        # nicspec = MagicMock(spec=vim.vm.device.VirtualDeviceSpec)
        # res = vnic_add_to_vm_task(nicspec, vm)
        # pass

    def test_vnic_add_to_vm_task(self):
        # arrange
        nicspec = vim.vm.device.VirtualDeviceSpec()
        vm = MagicMock()
        VNicService.vnic_set_connectivity_status = MagicMock()
        pyVmomiService.vm_reconfig_task = MagicMock()

        # act
        res = VNicService.vnic_add_to_vm_task(
            nicspec=nicspec, virtual_machine=vm, logger=MagicMock()
        )

        # assert
        self.assertTrue(VNicService.vnic_set_connectivity_status.called)
        self.assertTrue(pyVmomiService.vm_reconfig_task.called)

    def test_set_connectiv(self):
        nicspec = MagicMock()
        nicspec.device = MagicMock()
        connect_status = True
        nicspec = VNicService.vnic_set_connectivity_status(
            nicspec=nicspec, is_connected=connect_status, logger=MagicMock()
        )
        self.assertEqual(nicspec.device.connectable.connected, connect_status)

    def test_vnic_is_attachet_to_network(self):
        nicspec = MagicMock()
        nicspec.device = MagicMock()
        res = VNicService.vnic_is_attachet_to_network(nicspec, MagicMock())
        self.assertFalse(res)

    def test_vnic_remove_from_vm_list(self):
        # arrange
        vm = create_autospec(spec=vim.vm)
        vm.config = MagicMock()
        vm.config.hardware = MagicMock()
        vm.config.hardware.device = [
            create_autospec(spec=vim.vm.device.VirtualEthernetCard)
        ]

        # act
        device_change = VNicService.vnic_remove_from_vm_list(vm)

        # assert
        self.assertTrue(len(device_change) == 1)

    def test_get_device_spec(self):
        # arrange
        vnic = MagicMock()
        VNicService.create_vnic_spec = MagicMock()
        VNicService.set_vnic_connectivity_status = MagicMock()

        # act
        VNicService.get_device_spec(vnic, True)

        # assert
        self.assertTrue(VNicService.create_vnic_spec.called)
        self.assertTrue(VNicService.set_vnic_connectivity_status.called)

    def test_vnic_add_new_to_vm_task(self):
        # arrange

        vm = create_autospec(spec=vim.vm)
        VNicService.vnic_new_attached_to_network = MagicMock()
        # VNicService.vnic_add_to_vm_task = MagicMock()

        # act
        VNicService.vnic_add_new_to_vm_task(vm=vm, network=None, logger=MagicMock())

        # assert
        self.assertTrue(VNicService.vnic_new_attached_to_network.called)
        # self.assertTrue(VNicService.vnic_add_to_vm_task.called)

    def test_vnic_attached_to_network_1(self):
        # arrange
        network = create_autospec(spec=vim.dvs.DistributedVirtualPortgroup)
        nicspec = create_autospec(spec=vim.vm.device.VirtualDeviceSpec)
        VNicService.vnic_attach_to_network_distributed = MagicMock()

        # act
        VNicService.vnic_attached_to_network(nicspec, network, logger=MagicMock())

        # assert
        self.assertTrue(VNicService.vnic_attach_to_network_distributed.called)

    def test_vnic_attached_to_network_2(self):
        # arrange
        network = create_autospec(spec=vim.Network)
        nicspec = create_autospec(spec=vim.vm.device.VirtualDeviceSpec)
        VNicService.vnic_attach_to_network_standard = MagicMock()

        # act
        VNicService.vnic_attached_to_network(nicspec, network, logger=MagicMock())

        # assert
        self.assertTrue(VNicService.vnic_attach_to_network_standard.called)
