import unittest

from mock import MagicMock, Mock, create_autospec
from pyVmomi import vim

from cloudshell.cp.vcenter.commands.DeleteInstance import DestroyVirtualMachineCommand


class TestDestroyVirtualMachineCommand(unittest.TestCase):
    def test_destroyVirtualMachineCommand(self):
        # arrange
        pv_service = Mock()
        folder_manager = Mock()
        resource_remover = Mock()
        disconnector = Mock()
        si = create_autospec(spec=vim.ServiceInstance)
        resource_name = "this/is the name of the template"
        uuid = "uuid"
        vm = Mock()

        pv_service.destory_vm = Mock(return_value=True)
        disconnector.remove_interfaces_from_vm = Mock(return_value=True)
        resource_remover.remove_resource = Mock(return_value=True)
        pv_service.find_by_uuid = Mock(return_value=vm)

        reservation_details = Mock()
        reservation_details.ReservationDescription = Mock()
        reservation_details.ReservationDescription.Connectors = []

        session = Mock()
        session.GetReservationDetails = Mock(return_value=reservation_details)
        vcenter_data_model = Mock()
        destroyer = DestroyVirtualMachineCommand(
            pv_service, folder_manager, resource_remover, disconnector
        )

        # act
        res = destroyer.destroy(
            si=si,
            logger=Mock(),
            session=session,
            vcenter_data_model=vcenter_data_model,
            vm_uuid=uuid,
            vm_name=resource_name,
            reservation_id="reservation_id",
        )

        # assert
        self.assertTrue(res)
        self.assertTrue(pv_service.destory_vm.called_with(vm))
        self.assertTrue(disconnector.remove_interfaces_from_vm.called_with(si, vm))
        self.assertTrue(resource_remover.remove_resource.called_with(resource_name))
        self.assertTrue(pv_service.find_by_uuid.called_with(si, uuid))

    def test_destroyVirtualMachineCommandDeletesResourceWhenTheVMActualllyRemovedInVCenter(
        self,
    ):
        # arrange
        pv_service = Mock()
        folder_manager = Mock()
        resource_remover = Mock()
        disconnector = Mock()
        si = create_autospec(spec=vim.ServiceInstance)
        resource_name = "this/is the name of the template"
        uuid = "uuid"
        vm = None

        pv_service.destory_vm = Mock(return_value=True)
        disconnector.remove_interfaces_from_vm = Mock(return_value=True)
        resource_remover.remove_resource = Mock(return_value=True)
        pv_service.find_by_uuid = Mock(return_value=vm)

        reservation_details = Mock()
        reservation_details.ReservationDescription = Mock()
        reservation_details.ReservationDescription.Connectors = []

        session = Mock()
        session.GetReservationDetails = Mock(return_value=reservation_details)
        vcenter_data_model = Mock()
        destroyer = DestroyVirtualMachineCommand(
            pv_service, folder_manager, resource_remover, disconnector
        )

        # act
        res = destroyer.destroy(
            si=si,
            logger=Mock(),
            session=session,
            vcenter_data_model=vcenter_data_model,
            vm_uuid=uuid,
            vm_name=resource_name,
            reservation_id="reservation_id",
        )

        # assert
        self.assertTrue(res)
        self.assertTrue(pv_service.destory_vm.called_with(vm))
        self.assertTrue(disconnector.remove_interfaces_from_vm.called_with(si, vm))
        self.assertTrue(resource_remover.remove_resource.called_with(resource_name))
        self.assertTrue(pv_service.find_by_uuid.called_with(si, uuid))

    def test_destroyVirtualMachineOnlyCommand(self):
        # arrange
        pv_service = Mock()
        folder_manager = Mock()
        resource_remover = Mock()
        disconnector = Mock()
        si = create_autospec(spec=vim.ServiceInstance)
        vm = Mock()

        resource_model = MagicMock()
        resource_model.vm_uuid = "uuid"
        resource_model.fullname = "this/is the name of the template"
        resource_model.app_request_model.vm_location = "vm folder"
        reservation_id = "9e5b7004-e62e-4a8d-be1a-96bd1e58cb13"

        pv_service.destory_mv = Mock(return_value=True)
        disconnector.remove_interfaces_from_vm = Mock(return_value=True)
        resource_remover.remove_resource = Mock(return_value=True)
        pv_service.find_by_uuid = Mock(return_value=vm)

        reservation_details = Mock()
        reservation_details.ReservationDescription = Mock()
        reservation_details.ReservationDescription.Connectors = []

        session = Mock()
        session.GetReservationDetails = Mock(return_value=reservation_details)
        vcenter_data_model = Mock()
        vcenter_data_model.default_datacenter = "Default Datacenter"

        destroyer = DestroyVirtualMachineCommand(
            pv_service, folder_manager, resource_remover, disconnector
        )

        # act
        res = destroyer.DeleteInstance(
            si=si,
            logger=Mock(),
            session=session,
            vcenter_data_model=vcenter_data_model,
            reservation_id=reservation_id,
            resource_model=resource_model,
        )

        # assert
        self.assertTrue(res)
        self.assertTrue(pv_service.destory_mv.called_with(vm))
        self.assertTrue(disconnector.remove_interfaces_from_vm.called_with(si, vm))
        self.assertTrue(pv_service.find_by_uuid.called_with(si, resource_model.vm_uuid))
