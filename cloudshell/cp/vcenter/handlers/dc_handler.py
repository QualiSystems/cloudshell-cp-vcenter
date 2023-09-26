from __future__ import annotations

import logging
from collections.abc import Generator

from attrs import define
from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.cluster_handler import (
    BasicComputeEntityHandler,
    ClusterHandler,
    ClusterNotFound,
)
from cloudshell.cp.vcenter.handlers.datastore_handler import (
    DatastoreHandler,
    DatastoreNotFound,
)
from cloudshell.cp.vcenter.handlers.folder_handler import FolderHandler
from cloudshell.cp.vcenter.handlers.managed_entity_handler import ManagedEntityHandler
from cloudshell.cp.vcenter.handlers.network_handler import (
    DVPortGroupHandler,
    NetworkHandler,
    get_network_handler,
)
from cloudshell.cp.vcenter.handlers.resource_pool import (
    ResourcePoolHandler,
    ResourcePoolNotFound,
)
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.storage_pod_handler import (
    StoragePodHandler,
    StoragePodNotFound,
)
from cloudshell.cp.vcenter.handlers.switch_handler import (
    DvSwitchHandler,
    DvSwitchNotFound,
)
from cloudshell.cp.vcenter.handlers.vcenter_path import VcenterPath
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler, VmNotFound
from cloudshell.cp.vcenter.utils.network_watcher import NetworkWatcher

logger = logging.getLogger(__name__)


class DcNotFound(BaseVCenterException):
    def __init__(self, dc_name: str):
        self.dc_name = dc_name
        super().__init__(f"Datacenter with name '{dc_name}' not found.")


@define(str=False)
class DcHandler(ManagedEntityHandler):
    @classmethod
    def get_dc(cls, name: str, si: SiHandler) -> DcHandler:
        logger.debug(f"Searching for datacenter {name}")
        for vc_dc in si.find_items(vim.Datacenter):
            if vc_dc.name == name:
                return DcHandler(vc_dc, si)
        raise DcNotFound(name)

    @property
    def datastores(self) -> list[DatastoreHandler]:
        return [DatastoreHandler(store, self.si) for store in self._vc_obj.datastore]

    @property
    def dc(self) -> DcHandler:
        return self

    @property
    def clusters(self) -> list[ClusterHandler]:
        vc_clusters = self.si.find_items(
            [vim.ComputeResource, vim.ClusterComputeResource],
            container=self._vc_obj.hostFolder,
        )
        return [ClusterHandler(vc_cluster, self.si) for vc_cluster in vc_clusters]

    def get_network(self, name: str) -> NetworkHandler | DVPortGroupHandler:
        """Collecting all networks is not quick for many networks.

        If you need to get a network several times in the flow use NetworkWatcher
        separately.
        """
        network_folder = self.get_network_folder()
        if not (net := network_folder.find_child(name)):
            with NetworkWatcher(self.si, network_folder) as networks:
                network = networks.get_network(name)
        else:
            network = get_network_handler(net, self.si)
        return network

    @property
    def _class_name(self) -> str:
        return "Datacenter"

    def get_vm_by_uuid(self, uuid: str) -> VmHandler:
        vm = self.si.find_by_uuid(self._vc_obj, uuid, vm_search=True)
        if not vm:
            raise VmNotFound(self, uuid=uuid)
        return VmHandler(vm, self.si)

    def get_vm_by_path(self, path: str | VcenterPath) -> VmHandler:
        if not isinstance(path, VcenterPath):
            path = VcenterPath(path)
        vm_name = path.pop()
        folder = self.get_vm_folder(path)
        vc_vm = folder.find_child(vm_name)
        if not vc_vm:
            raise VmNotFound(self, name=vm_name)
        return VmHandler(vc_vm, self.si)

    def get_all_vms(self) -> list[VmHandler]:
        return [
            VmHandler(vm, self.si) for vm in self.find_items(vim.VirtualMachine, True)
        ]

    def get_vms(self, name: str) -> Generator[VmHandler, None, None]:
        for vm in self.find_items(vim.VirtualMachine, True):
            if vm.name == name:
                yield VmHandler(vm, self.si)

    def get_vm_folder(self, path: str | VcenterPath) -> FolderHandler:
        vm_folder = FolderHandler(self._vc_obj.vmFolder, self.si)
        if path:
            vm_folder = vm_folder.get_folder(path)
        return vm_folder

    def get_or_create_vm_folder(self, path: str | VcenterPath) -> FolderHandler:
        vm_folder = FolderHandler(self._vc_obj.vmFolder, self.si)
        if path:
            vm_folder = vm_folder.get_or_create_folder(path)
        return vm_folder

    def get_network_folder(
        self, path: str | VcenterPath | None = None
    ) -> FolderHandler:
        network_folder = FolderHandler(self._vc_obj.networkFolder, self.si)
        if path:
            network_folder = network_folder.get_folder(path)
        return network_folder

    def get_or_create_network_folder(self, path: str | VcenterPath) -> FolderHandler:
        network_folder = FolderHandler(self._vc_obj.networkFolder, self.si)
        if path:
            network_folder = network_folder.get_or_create_folder(path)
        return network_folder

    def get_cluster(self, name: str) -> ClusterHandler:
        for vc_cluster in self.si.find_items(
            [vim.ComputeResource, vim.ClusterComputeResource],
            container=self._vc_obj.hostFolder,
        ):
            if vc_cluster.name == name:
                return ClusterHandler(vc_cluster, self.si)
        raise ClusterNotFound(self, name)

    def get_compute_entity(self, path: str | VcenterPath) -> BasicComputeEntityHandler:
        logger.debug(f"Getting compute entity by path {path}")
        if not isinstance(path, VcenterPath):
            path = VcenterPath(path)
        cluster_name = path.pop_head()
        compute_entity = self.get_cluster(cluster_name)
        if path:
            compute_entity = compute_entity.get_host(str(path))
        return compute_entity

    def get_datastore(self, path: str | VcenterPath) -> DatastoreHandler:
        if not isinstance(path, VcenterPath):
            path = VcenterPath(path)
        # we ignore datastore parents for now
        datastore_name = path.pop()

        try:
            datastore = self.get_datastore_by_name(datastore_name)
        except DatastoreNotFound as exc:
            try:
                storage_pod = self.get_storage_pod(datastore_name)
                datastore = storage_pod.get_datastore_with_max_free_space()
            except StoragePodNotFound:
                raise exc

        return datastore

    def get_dv_switch(self, path: VcenterPath | str) -> DvSwitchHandler:
        if not isinstance(path, VcenterPath):
            path = VcenterPath(path)
        dvs_name = path.pop()
        if path:
            entity = FolderHandler.get_folder_from_parent(
                self._vc_obj.networkFolder, path, self.si
            )
        else:
            entity = FolderHandler(self._vc_obj.networkFolder, self.si)

        for vc_dvs in entity.find_items(vim.dvs.VmwareDistributedVirtualSwitch):
            if vc_dvs.name == dvs_name:
                return DvSwitchHandler(vc_dvs, self.si)
        raise DvSwitchNotFound(self, dvs_name)

    def get_resource_pool(self, name: str) -> ResourcePoolHandler:
        for r_pool in self.si.find_items(
            vim.ResourcePool, container=self._vc_obj.hostFolder
        ):
            if r_pool.name == name:
                return ResourcePoolHandler(r_pool, self.si)
        raise ResourcePoolNotFound(self, name)

    def get_datastore_by_name(self, name: str) -> DatastoreHandler:
        for datastore in self.datastores:
            if datastore.name == name:
                return datastore
        raise DatastoreNotFound(self, name)

    def get_storage_pod(self, name: str) -> StoragePodHandler:
        for storage in self.si.find_items(
            vim.StoragePod, container=self._vc_obj, recursive=True
        ):
            if storage.name == name:
                return StoragePodHandler(storage, self.si)
        raise StoragePodNotFound(self, name)
