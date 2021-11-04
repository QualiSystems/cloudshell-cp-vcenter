from __future__ import annotations

from datetime import datetime
from enum import Enum
from logging import Logger

from pyVmomi import vim

from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.common.vcenter.event_manager import EventManager
from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.custom_spec_handler import CustomSpecHandler
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler
from cloudshell.cp.vcenter.handlers.network_handler import (
    NetworkHandler,
    NetworkNotFound,
)
from cloudshell.cp.vcenter.handlers.virtual_device_handler import is_vnic
from cloudshell.cp.vcenter.handlers.vnic_handler import VnicHandler
from cloudshell.cp.vcenter.utils.task_waiter import VcenterTaskWaiter


class VMWareToolsNotInstalled(BaseVCenterException):
    def __init__(self, vm: VmHandler):
        self.vm = vm
        super().__init__(f"VMWare Tools are not installed or running on VM '{vm.name}'")


class PowerState(Enum):
    ON = "poweredOn"
    OFF = "poweredOff"
    SUSPENDED = "suspended"


class VmHandler(ManagedEntityHandler):
    def __str__(self):
        return f"VM '{self.name}'"

    @property
    def networks(self) -> list[NetworkHandler]:
        return list(map(NetworkHandler, self.entity.network))

    def _get_devices(self):
        return self.entity.config.hardware.device

    @property
    def vnics(self) -> list[VnicHandler]:
        return list(map(VnicHandler, filter(is_vnic, self._get_devices())))

    def get_network(self, name: str) -> NetworkHandler:
        for network in self.networks:
            if network.name == name:
                return network
        raise NetworkNotFound(name, self)

    def validate_guest_tools_installed(self):
        if self.entity.guest.toolsStatus != vim.vm.GuestInfo.ToolsStatus.toolsOk:
            raise VMWareToolsNotInstalled(self)

    @property
    def power_state(self) -> PowerState:
        return PowerState(self.entity.summary.runtime.powerState)

    def power_on(self, logger: Logger, task_waiter: VcenterTaskWaiter | None = None):
        if self.power_state is PowerState.ON:
            logger.info("VM already powered on")
        else:
            logger.info(f"Powering on VM '{self.name}'")
            task = self.entity.PowerOn()
            task_waiter = task_waiter or VcenterTaskWaiter(logger)
            task_waiter.wait_for_task(task)

    def power_off(
        self, soft: bool, logger: Logger, task_waiter: VcenterTaskWaiter | None = None
    ):
        if self.power_state is PowerState.OFF:
            logger.info("VM already powered off")
        else:
            logger.info(f"Powering off VM '{self.name}'")
            if soft:
                self.validate_guest_tools_installed()
                self.entity.ShutdownGuest()  # do not return task
            else:
                task = self.entity.PowerOff()
                task_waiter = task_waiter or VcenterTaskWaiter(logger)
                task_waiter.wait_for_task(task)

    def add_customization_spec(
        self,
        spec: CustomSpecHandler,
        logger: Logger,
        task_waiter: VcenterTaskWaiter | None = None,
    ):
        task = self.entity.CustomizeVM_Task(spec.spec.spec)
        task_waiter = task_waiter or VcenterTaskWaiter(logger)
        task_waiter.wait_for_task(task)

    def wait_for_customization_ready(
        self, vcenter_client: VCenterAPIClient, begin_time: datetime, logger: Logger
    ):
        logger.info(f"Checking for the {self} OS customization events")
        em = EventManager()
        em.wait_for_vm_os_customization_start_event(
            vcenter_client, vm=self.entity, logger=logger, event_start_time=begin_time
        )

        logger.info(f"Waiting for the {self} OS customization event to be proceeded")
        em.wait_for_vm_os_customization_end_event(
            vcenter_client, vm=self.entity, logger=logger, event_start_time=begin_time
        )
