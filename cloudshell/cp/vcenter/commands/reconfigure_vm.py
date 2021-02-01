from pyVmomi import vim

from cloudshell.cp.vcenter.common.vcenter.task_waiter import SynchronousTaskWaiter
from cloudshell.cp.vcenter.common.vcenter.vmomi_service import pyVmomiService
from cloudshell.cp.vcenter.exceptions.reconfigure_vm import ReconfigureVMException


class ReconfigureVMCommand:
    def __init__(self, pyvmomi_service, task_waiter):
        """

        :param pyvmomi_service:
        :type pyvmomi_service: pyVmomiService
        :param task_waiter: Waits for the task to be completed
        :type task_waiter:  SynchronousTaskWaiter
        :return:
        """
        self.pyvmomi_service = pyvmomi_service
        self.task_waiter = task_waiter

    def reconfigure(
        self,
        si,
        logger,
        session,
        vm_uuid,
        cpu,
        ram,
        hhd,
    ):
        """

        :param vim.ServiceInstance si: py_vmomi service instance
        :param logger: Logger
        :param session: CloudShellAPISession
        :type session: cloudshell_api.CloudShellAPISession
        :param vm_uuid: uuid of the virtual machine
        """
        logger.info("Reconfiguring VM...")

        vm = self.pyvmomi_service.find_by_uuid(si, vm_uuid)

        if not vm:
            raise ReconfigureVMException(
                f"Unable to find virtual machine with uuid {vm_uuid}"
            )

        if vm.summary.runtime.powerState == vim.VirtualMachine.PowerState.poweredOn:
            raise ReconfigureVMException(
                "Unable to reconfigure virtual machine while it is powered on. Turn off machine first"
            )

        return self.pyvmomi_service.reconfigure_vm(
            vm=vm, cpu=cpu, ram=ram, hhd=hhd, logger=logger
        )
