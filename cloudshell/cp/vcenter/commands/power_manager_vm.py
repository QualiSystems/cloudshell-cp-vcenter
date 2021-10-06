from datetime import datetime


class VirtualMachinePowerManagementCommand(object):
    def __init__(self, pyvmomi_service, synchronous_task_waiter, event_manager):
        """

        :param pyvmomi_service:
        :param synchronous_task_waiter:
        :type synchronous_task_waiter:  cloudshell.cp.vcenter.common.vcenter.task_waiter.SynchronousTaskWaiter
        :param event_manager:
        :return:
        """
        self.pv_service = pyvmomi_service
        self.synchronous_task_waiter = synchronous_task_waiter
        self.event_manager = event_manager

    def power_off(
        self, si, logger, session, vcenter_data_model, vm_uuid, resource_fullname
    ):
        """Power off of a vm.

        :param vcenter_data_model: vcenter model
        :param si: Service Instance
        :param logger:
        :param session:
        :param vcenter_data_model: vcenter_data_model
        :param vm_uuid: the uuid of the vm
        :param resource_fullname: the full name of the deployed app resource
        :return:
        """
        logger.info("Retrieving vm by uuid: {0}".format(vm_uuid))
        vm = self.pv_service.find_by_uuid(si, vm_uuid)

        if vm.summary.runtime.powerState == "poweredOff":
            logger.info("vm already powered off")
            task_result = "Already powered off"
        else:
            # hard power off
            logger.info("{0} powering of vm".format(vcenter_data_model.shutdown_method))
            if vcenter_data_model.shutdown_method.lower() != "soft":
                task = vm.PowerOff()
                task_result = self.synchronous_task_waiter.wait_for_task(
                    task=task, logger=logger, action_name="Power Off"
                )
            else:
                if vm.guest.toolsStatus == "toolsNotInstalled":
                    logger.warning(
                        "VMWare Tools status on virtual machine '{0}' are not installed".format(
                            vm.name
                        )
                    )
                    raise ValueError(
                        "Cannot power off the vm softly because VMWare Tools are not installed"
                    )

                if vm.guest.toolsStatus == "toolsNotRunning":
                    logger.warning(
                        "VMWare Tools status on virtual machine '{0}' are not running".format(
                            vm.name
                        )
                    )
                    raise ValueError(
                        "Cannot power off the vm softly because VMWare Tools are not running"
                    )

                vm.ShutdownGuest()
                task_result = "vm powered off"

        return task_result

    def power_on(self, si, logger, session, vm_uuid, resource_fullname):
        """Power on the specified vm.

        :param si:
        :param logger:
        :param session:
        :param vm_uuid: the uuid of the vm
        :param resource_fullname: the full name of the deployed app resource
        :return:
        """
        logger.info(f"Retrieving VM by uuid: {vm_uuid}")
        vm = self.pv_service.find_by_uuid(si, vm_uuid)

        if vm.summary.runtime.powerState == "poweredOn":
            logger.info("VM already powered on")
            return "Already powered on"
        else:
            logger.info("Checking if Customization Spec exists for the VM...")
            custom_spec = self.pv_service.get_customization_spec(si=si, name=vm.name)

            if custom_spec is None:
                logger.info("No VM Customization Spec found, powering on the VM...")
                task = vm.PowerOn()
                return self.synchronous_task_waiter.wait_for_task(
                    task=task, logger=logger, action_name="Power On"
                )
            else:
                logger.info("Adding Customization Spec to the VM...")
                task = vm.CustomizeVM_Task(custom_spec.spec)
                self.synchronous_task_waiter.wait_for_task(
                    task=task,
                    logger=logger,
                    action_name="Applying Customization Spec for the VM",
                )

                start_time = datetime.now()

                task = vm.PowerOn()
                task_result = self.synchronous_task_waiter.wait_for_task(
                    task=task, logger=logger, action_name="Power On"
                )

                logger.info("Checking for the VM OS customization events...")
                self.event_manager.wait_for_vm_os_customization_start_event(
                    si=si, vm=vm, logger=logger, event_start_time=start_time
                )

                logger.info(
                    "Waiting for the VM OS customization event to be proceeded..."
                )
                self.event_manager.wait_for_vm_os_customization_end_event(
                    si=si, vm=vm, logger=logger, event_start_time=start_time
                )

                self.pv_service.delete_customization_spec(si=si, name=vm.name)

                return task_result
