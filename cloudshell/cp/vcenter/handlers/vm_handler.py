from __future__ import annotations

from contextlib import suppress
from datetime import datetime
from enum import Enum
from functools import cached_property
from threading import Lock

import attr
from pyVmomi import vim

from cloudshell.cp.vcenter.common.vcenter.event_manager import EventManager
from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.cluster_handler import HostHandler
from cloudshell.cp.vcenter.handlers.config_spec_handler import ConfigSpecHandler
from cloudshell.cp.vcenter.handlers.custom_spec_handler import CustomSpecHandler
from cloudshell.cp.vcenter.handlers.datastore_handler import DatastoreHandler
from cloudshell.cp.vcenter.handlers.folder_handler import FolderHandler
from cloudshell.cp.vcenter.handlers.managed_entity_handler import (
    ManagedEntityHandler,
    ManagedEntityNotFound,
)
from cloudshell.cp.vcenter.handlers.network_handler import (
    DVPortGroupHandler,
    HostPortGroupNotFound,
    NetworkHandler,
    get_network_handler,
)
from cloudshell.cp.vcenter.handlers.resource_pool import ResourcePoolHandler
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.snapshot_handler import (
    SnapshotHandler,
    SnapshotNotFoundInSnapshotTree,
)
from cloudshell.cp.vcenter.handlers.switch_handler import VSwitchHandler
from cloudshell.cp.vcenter.handlers.task import ON_TASK_PROGRESS_TYPE, Task
from cloudshell.cp.vcenter.handlers.vcenter_path import VcenterPath
from cloudshell.cp.vcenter.handlers.virtual_device_handler import (
    is_virtual_disk,
    is_vnic,
)
from cloudshell.cp.vcenter.handlers.virtual_disk_handler import (
    VirtualDisk as _VirtualDisk,
)
from cloudshell.cp.vcenter.handlers.vnic_handler import Vnic as _Vnic
from cloudshell.cp.vcenter.handlers.vnic_handler import (
    VnicNotFound,
    VnicWithMacNotFound,
)
from cloudshell.cp.vcenter.utils.connectivity_helpers import is_correct_vnic, is_ipv4
from cloudshell.cp.vcenter.utils.units_converter import BASE_10


class VmNotFound(BaseVCenterException):
    def __init__(
        self,
        entity: ManagedEntityHandler,
        uuid: str | None = None,
        name: str | None = None,
    ):
        self.entity = entity
        self.uuid = uuid
        self.name = name

        if not uuid and not name:
            raise ValueError("You should specify uuid or name")
        if uuid:
            msg = f"VM with the uuid '{uuid}' in the {entity} not found"
        else:
            msg = f"VM with the name '{name}' in the {entity} not found"
        super().__init__(msg)


class VMWareToolsNotInstalled(BaseVCenterException):
    def __init__(self, vm: VmHandler):
        self.vm = vm
        super().__init__(f"VMWare Tools are not installed or running on VM '{vm.name}'")


class DuplicatedSnapshotName(BaseVCenterException):
    def __init__(self, snapshot_name: str):
        self.snapshot_name = snapshot_name
        super().__init__(f"Snapshot with name '{snapshot_name}' already exists")


class SnapshotNotFoundByPath(BaseVCenterException):
    def __init__(self, snapshot_path: VcenterPath, vm: VmHandler):
        self.snapshot_path = snapshot_path
        self.vm = vm
        super().__init__(f"Snapshot with path '{snapshot_path}' not found for the {vm}")


class VmIsNotPowered(BaseVCenterException):
    def __init__(self, vm: VmHandler):
        self.vm = vm
        super().__init__(f"The {vm} is not powered On")


class PowerState(Enum):
    ON = "poweredOn"
    OFF = "poweredOff"
    SUSPENDED = "suspended"


_vm_locks: dict[str, Lock] = {}


def _get_vm_lock(vm: VmHandler) -> Lock:
    if vm.uuid not in _vm_locks:
        _vm_locks[vm.uuid] = Lock()
    return _vm_locks[vm.uuid]


@attr.s(auto_attribs=True, repr=False)
class VmHandler(ManagedEntityHandler):
    _vc_obj: vim.VirtualMachine
    si: SiHandler

    @cached_property
    def vnic_class(self) -> type[_Vnic]:
        class Vnic(_Vnic):
            vm = self

        return Vnic

    @cached_property
    def disk_class(self) -> type[_VirtualDisk]:
        class VirtualDisk(_VirtualDisk):
            vm = self

        return VirtualDisk

    @property
    def uuid(self) -> str:
        return self._vc_obj.config.instanceUuid

    @property
    def bios_uuid(self) -> str:
        return self._vc_obj.config.uuid

    @property
    def primary_ipv4(self) -> str | None:
        ip = self._vc_obj.guest.ipAddress
        return ip if is_ipv4(ip) else None

    @property
    def networks(self) -> list[NetworkHandler | DVPortGroupHandler]:
        return [get_network_handler(net, self.si) for net in self._vc_obj.network]

    @property
    def dv_port_groups(self) -> list[DVPortGroupHandler]:
        return list(filter(lambda x: isinstance(x, DVPortGroupHandler), self.networks))

    @property
    def vnics(self) -> list[_Vnic]:
        return list(map(self.vnic_class, filter(is_vnic, self._get_devices())))

    @property
    def disks(self) -> list[_VirtualDisk]:
        return list(map(self.disk_class, filter(is_virtual_disk, self._get_devices())))

    @property
    def host(self) -> HostHandler:
        return HostHandler(self._vc_obj.runtime.host, self.si)

    @property
    def disks_size(self) -> int:
        return sum(d.capacity_in_bytes for d in self.disks)

    @property
    def num_cpu(self) -> int:
        return self._vc_obj.summary.config.numCpu

    @property
    def memory_size(self) -> int:
        return self._vc_obj.summary.config.memorySizeMB * BASE_10 * BASE_10

    @property
    def guest_os(self) -> str:
        return self._vc_obj.summary.config.guestFullName

    @property
    def guest_id(self) -> str | None:
        return self._vc_obj.guest.guestId or self._vc_obj.config.guestId

    @property
    def current_snapshot(self) -> SnapshotHandler | None:
        if not self._vc_obj.snapshot:
            return None
        return SnapshotHandler(self._vc_obj.snapshot.currentSnapshot)

    @property
    def path(self) -> VcenterPath:
        """Path from DC.vmFolder."""
        vm_folder = self.dc.get_vm_folder("")
        path = VcenterPath(self.name)
        folder = FolderHandler(self._vc_obj.parent, self.si)
        while folder != vm_folder:
            path = VcenterPath(folder.name) + path
            folder = folder.parent
        return path

    @property
    def power_state(self) -> PowerState:
        return PowerState(self._vc_obj.summary.runtime.powerState)

    @property
    def _class_name(self) -> str:
        return "VM"

    @property
    def _moId(self) -> str:
        # avoid using this property
        return self._vc_obj._moId

    @property
    def _wsdl_name(self) -> str:
        return self._vc_obj._wsdlName

    @property
    def _reconfig_vm_lock(self) -> Lock:
        return _get_vm_lock(self)

    def _get_devices(self):
        return self._vc_obj.config.hardware.device

    def _reconfigure(
        self,
        config_spec: vim.vm.ConfigSpec,
        on_task_progress: ON_TASK_PROGRESS_TYPE | None = None,
    ) -> None:
        with self._reconfig_vm_lock:
            vc_task = self._vc_obj.ReconfigVM_Task(config_spec)
            task = Task(vc_task, self.logger)
            task.wait(on_progress=on_task_progress)

    def get_vnic(self, name_or_id: str) -> _Vnic:
        for vnic in self.vnics:
            if is_correct_vnic(name_or_id, vnic):
                return vnic
        raise VnicNotFound(name_or_id, self)

    def get_vnic_by_mac(self, mac_address: str) -> _Vnic:
        self.logger.info(f"Searching for vNIC of the {self} with mac {mac_address}")
        for vnic in self.vnics:
            if vnic.mac_address == mac_address.upper():
                return vnic
        raise VnicWithMacNotFound(mac_address, self)

    def get_ip_addresses_by_vnic(self, vnic: _Vnic) -> list[str]:
        assert vnic.vm is self
        for nic_info in self._vc_obj.guest.net:
            if nic_info.deviceConfigId == vnic.key:
                ips = [ip.ipAddress for ip in nic_info.ipConfig.ipAddress]
                break
        else:
            ips = []
        return ips

    def get_network_vlan_id(self, network: NetworkHandler | DVPortGroupHandler) -> int:
        if isinstance(network, DVPortGroupHandler):
            pg = network
        else:
            for pg in self.host.port_groups:
                if pg.name == network.name:
                    break
            else:
                raise HostPortGroupNotFound(self, network.name)
        return pg.vlan_id

    def get_v_switch(self, name: str) -> VSwitchHandler:
        return self.host.get_v_switch(name)

    def validate_guest_tools_installed(self):
        if self._vc_obj.guest.toolsStatus != vim.vm.GuestInfo.ToolsStatus.toolsOk:
            raise VMWareToolsNotInstalled(self)

    def power_on(
        self, on_task_progress: ON_TASK_PROGRESS_TYPE | None = None
    ) -> datetime:
        if self.power_state is PowerState.ON:
            self.logger.info("VM already powered on")
            return datetime.now()
        else:
            self.logger.info(f"Powering on the {self}")
            vc_task = self._vc_obj.PowerOn()
            task = Task(vc_task, self.logger)
            task.wait(on_progress=on_task_progress)
            return task.complete_time

    def power_off(
        self, soft: bool, on_task_progress: ON_TASK_PROGRESS_TYPE | None = None
    ) -> None:
        if self.power_state is PowerState.OFF:
            self.logger.info("VM already powered off")
        else:
            self.logger.info(f"Powering off the {self}")
            if soft:
                self.validate_guest_tools_installed()
                self._vc_obj.ShutdownGuest()  # do not return task
            else:
                vc_task = self._vc_obj.PowerOff()
                task = Task(vc_task, self.logger)
                task.wait(on_progress=on_task_progress)

    def add_customization_spec(self, spec: CustomSpecHandler) -> None:
        vc_task = self._vc_obj.CustomizeVM_Task(spec.spec.spec)
        task = Task(vc_task, self.logger)
        task.wait()

    def wait_for_customization_ready(self, begin_time: datetime) -> None:
        self.logger.info(f"Checking for the {self} OS customization events")
        em = EventManager()
        em.wait_for_vm_os_customization_start_event(
            self.si, self._vc_obj, logger=self.logger, event_start_time=begin_time
        )

        self.logger.info(
            f"Waiting for the {self} OS customization event to be proceeded"
        )
        em.wait_for_vm_os_customization_end_event(
            self.si, self._vc_obj, logger=self.logger, event_start_time=begin_time
        )

    def reconfigure_vm(
        self,
        config_spec: ConfigSpecHandler,
        on_task_progress: ON_TASK_PROGRESS_TYPE | None = None,
    ) -> None:
        spec = config_spec.get_spec_for_vm(self)
        self._reconfigure(spec, on_task_progress)

    def create_snapshot(
        self,
        snapshot_name: str,
        dump_memory: bool,
        on_task_progress: ON_TASK_PROGRESS_TYPE | None = None,
    ) -> str:
        if self.current_snapshot:
            new_snapshot_path = self.current_snapshot.path + snapshot_name
            try:
                SnapshotHandler.get_vm_snapshot_by_path(self._vc_obj, new_snapshot_path)
            except SnapshotNotFoundInSnapshotTree:
                pass
            else:
                raise DuplicatedSnapshotName(snapshot_name)
        else:
            new_snapshot_path = VcenterPath(snapshot_name)

        self.logger.info(
            f"Creating a new snapshot for {self} with path {new_snapshot_path}"
        )
        quiesce = True
        vc_task = self._vc_obj.CreateSnapshot(
            snapshot_name, "Created by CloudShell vCenterShell", dump_memory, quiesce
        )
        task = Task(vc_task, self.logger)
        task.wait(on_progress=on_task_progress)

        return str(new_snapshot_path)

    def restore_from_snapshot(self, snapshot_path: str | VcenterPath) -> None:
        self.logger.info(f"Restore {self} from the snapshot '{snapshot_path}'")
        snapshot = self.get_snapshot_by_path(snapshot_path)
        vc_task = snapshot.revert_to_snapshot_task()
        task = Task(vc_task, self.logger)
        task.wait()

    def remove_snapshot(
        self,
        snapshot_path: str | VcenterPath,
        remove_child: bool,
    ) -> None:
        self.logger.info(f"Removing snapshot '{snapshot_path}' from the {self}")
        snapshot = self.get_snapshot_by_path(snapshot_path)
        vc_task = snapshot.remove_snapshot_task(remove_child)
        task = Task(vc_task, self.logger)
        task.wait()

    def get_snapshot_by_path(self, snapshot_path: str | VcenterPath) -> SnapshotHandler:
        if not isinstance(snapshot_path, VcenterPath):
            snapshot_path = VcenterPath(snapshot_path)

        try:
            snapshot = SnapshotHandler.get_vm_snapshot_by_path(
                self._vc_obj, snapshot_path
            )
        except SnapshotNotFoundInSnapshotTree:
            raise SnapshotNotFoundByPath(snapshot_path, self)
        return snapshot

    def get_snapshot_paths(self) -> list[str]:
        self.logger.info(f"Getting snapshots for the {self}")
        return [str(s.path) for s in SnapshotHandler.yield_vm_snapshots(self._vc_obj)]

    def delete(self, on_task_progress: ON_TASK_PROGRESS_TYPE | None = None) -> None:
        self.logger.info(f"Deleting the {self}")
        with suppress(ManagedEntityNotFound):
            vc_task = self._vc_obj.Destroy_Task()
            task = Task(vc_task, self.logger)
            task.wait(on_progress=on_task_progress)

    def clone_vm(
        self,
        vm_name: str,
        vm_storage: DatastoreHandler,
        vm_folder: FolderHandler,
        vm_resource_pool: ResourcePoolHandler | None = None,
        snapshot: SnapshotHandler | None = None,
        config_spec: ConfigSpecHandler | None = None,
        on_task_progress: ON_TASK_PROGRESS_TYPE | None = None,
    ) -> VmHandler:
        self.logger.info(f"Cloning the {self} to the new VM '{vm_name}'")
        clone_spec = vim.vm.CloneSpec(powerOn=False)
        placement = vim.vm.RelocateSpec()
        placement.datastore = vm_storage.get_vc_obj()
        if vm_resource_pool:
            placement.pool = vm_resource_pool.get_vc_obj()
        if snapshot:
            clone_spec.snapshot = snapshot.get_vc_obj()
            clone_spec.template = False
            placement.diskMoveType = "createNewChildDiskBacking"
        clone_spec.location = placement

        vc_task = self._vc_obj.Clone(
            folder=vm_folder.get_vc_obj(), name=vm_name, spec=clone_spec
        )
        task = Task(vc_task, self.logger)
        new_vc_vm = task.wait(on_progress=on_task_progress)
        new_vm = VmHandler(new_vc_vm, self.si)

        if config_spec:
            try:
                new_vm.reconfigure_vm(config_spec, on_task_progress)
            except Exception:
                new_vm.delete()
                raise
        return new_vm
