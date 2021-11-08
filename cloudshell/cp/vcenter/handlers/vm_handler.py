from __future__ import annotations

from datetime import datetime
from enum import Enum
from logging import Logger

from pyVmomi import vim

from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.common.vcenter.event_manager import EventManager
from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.config_spec_handler import ConfigSpecHandler
from cloudshell.cp.vcenter.handlers.custom_spec_handler import CustomSpecHandler
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler
from cloudshell.cp.vcenter.handlers.network_handler import (
    NetworkHandler,
    NetworkNotFound,
)
from cloudshell.cp.vcenter.handlers.snapshot_handler import (
    SnapshotHandler,
    SnapshotPath,
)
from cloudshell.cp.vcenter.handlers.virtual_device_handler import is_vnic
from cloudshell.cp.vcenter.handlers.vnic_handler import VnicHandler
from cloudshell.cp.vcenter.utils.task_waiter import VcenterTaskWaiter


class VMWareToolsNotInstalled(BaseVCenterException):
    def __init__(self, vm: VmHandler):
        self.vm = vm
        super().__init__(f"VMWare Tools are not installed or running on VM '{vm.name}'")


class DuplicatedSnapshotName(BaseVCenterException):
    def __init__(self, snapshot_name: str):
        self.snapshot_name = snapshot_name
        super().__init__(f"Snapshot with name '{snapshot_name}' already exists")


class PowerState(Enum):
    ON = "poweredOn"
    OFF = "poweredOff"
    SUSPENDED = "suspended"


class VmHandler(ManagedEntityHandler):
    def __str__(self):
        return f"VM '{self.name}'"

    @property
    def uuid(self) -> str:
        return self._entity.config.uuid

    @property
    def networks(self) -> list[NetworkHandler]:
        return list(map(NetworkHandler, self._entity.network))

    def _get_devices(self):
        return self._entity.config.hardware.device

    @property
    def vnics(self) -> list[VnicHandler]:
        return list(map(VnicHandler, filter(is_vnic, self._get_devices())))

    @property
    def current_snapshot(self) -> SnapshotHandler | None:
        if not self._entity.snapshot:
            return None
        return SnapshotHandler(self._entity.snapshot.currentSnapshot)

    def get_network(self, name: str) -> NetworkHandler:
        for network in self.networks:
            if network.name == name:
                return network
        raise NetworkNotFound(name, self)

    def validate_guest_tools_installed(self):
        if self._entity.guest.toolsStatus != vim.vm.GuestInfo.ToolsStatus.toolsOk:
            raise VMWareToolsNotInstalled(self)

    @property
    def power_state(self) -> PowerState:
        return PowerState(self._entity.summary.runtime.powerState)

    def power_on(self, logger: Logger, task_waiter: VcenterTaskWaiter | None = None):
        if self.power_state is PowerState.ON:
            logger.info("VM already powered on")
        else:
            logger.info(f"Powering on VM '{self.name}'")
            task = self._entity.PowerOn()
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
                self._entity.ShutdownGuest()  # do not return task
            else:
                task = self._entity.PowerOff()
                task_waiter = task_waiter or VcenterTaskWaiter(logger)
                task_waiter.wait_for_task(task)

    def add_customization_spec(
        self,
        spec: CustomSpecHandler,
        logger: Logger,
        task_waiter: VcenterTaskWaiter | None = None,
    ):
        task = self._entity.CustomizeVM_Task(spec.spec.spec)
        task_waiter = task_waiter or VcenterTaskWaiter(logger)
        task_waiter.wait_for_task(task)

    def wait_for_customization_ready(
        self, vcenter_client: VCenterAPIClient, begin_time: datetime, logger: Logger
    ):
        logger.info(f"Checking for the {self} OS customization events")
        em = EventManager()
        em.wait_for_vm_os_customization_start_event(
            vcenter_client, vm=self._entity, logger=logger, event_start_time=begin_time
        )

        logger.info(f"Waiting for the {self} OS customization event to be proceeded")
        em.wait_for_vm_os_customization_end_event(
            vcenter_client, vm=self._entity, logger=logger, event_start_time=begin_time
        )

    def reconfigure_vm(
        self,
        config_spec: ConfigSpecHandler,
        logger: Logger,
        task_waiter: VcenterTaskWaiter | None = None,
    ):
        task = config_spec.get_spec_for_vm(self._entity)
        task_waiter = task_waiter or VcenterTaskWaiter(logger)
        task_waiter.wait_for_task(task)

    def create_snapshot(
        self,
        snapshot_name: str,
        dump_memory: bool,
        logger: Logger,
        task_waiter: VcenterTaskWaiter | None = None,
    ) -> str:
        try:
            new_snapshot_path = self.current_snapshot.path + snapshot_name
        except AttributeError:
            new_snapshot_path = SnapshotPath(snapshot_name)

        snapshot = self.current_snapshot.get_snapshot_by_path(new_snapshot_path)
        if snapshot:
            raise DuplicatedSnapshotName(snapshot_name)

        logger.info(f"Creating a new snapshot for {self} with path {new_snapshot_path}")
        quiesce = True
        task = self._entity.CreateSnapshot(
            snapshot_name, "Created by CloudShell vCenterShell", dump_memory, quiesce
        )
        task_waiter = task_waiter or VcenterTaskWaiter(logger)
        task_waiter.wait_for_task(task)

        return str(new_snapshot_path)
