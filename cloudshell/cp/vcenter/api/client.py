import time
from logging import Logger

from pyVmomi import vim  # noqa

from cloudshell.cp.vcenter.exceptions import (
    LoginException,
    ObjectNotFoundException,
    TaskFaultException,
    VMWareToolsNotInstalled,
)
from cloudshell.cp.vcenter.utils.cached_property import cached_property
from cloudshell.cp.vcenter.utils.client_helpers import get_si


class VCenterAPIClient:
    def __init__(
        self, host: str, user: str, password: str, logger: Logger, port: int = 443
    ):
        self._host = host
        self._user = user
        self._password = password
        self._port = port
        self._logger = logger

    # todo: check id we need this
    # def back_slash_to_front_converter(string):
    #     """
    #     Replacing all \ in the str to /
    #     :param string: single string to modify
    #     :type string: str
    #     """
    #     pass

    def _get_si(self):
        self._logger.info("Initializing vCenter API client SI...")
        try:
            si = get_si(self._host, self._user, self._password, self._port)
        except vim.fault.InvalidLogin:
            self._logger.exception("Unable to login to the vCenter")
            raise LoginException("Can't connect to the vCenter. Invalid user/password")
        return si

    @cached_property
    def _si(self):
        return self._get_si()

    @property
    def root_container(self):
        return self._si.content.rootFolder

    def _get_items_from_view(self, container, vim_type, recursive=False):
        if not isinstance(vim_type, list):
            vim_type = [vim_type]
        view = self._si.content.viewManager.CreateContainerView(
            container, vim_type, recursive
        )
        items = view.view
        view.DestroyView()
        return items

    def get_dc(self, name: str):
        for dc in self._get_items_from_view(self.root_container, vim.Datacenter):
            if dc.name == name:
                return dc
        raise ObjectNotFoundException(f"Datacenter '{name}' not found")

    def get_folder(self, path: str, parent):
        dir_name, *sub_dirs = path.split("/")
        emsg = f"Folder '{path}' not found in parent '{parent.name}'"
        for folder in self._get_items_from_view(parent, vim.Folder):
            if folder.name == dir_name:
                if not sub_dirs:
                    return folder
                else:
                    try:
                        new_path = "/".join(sub_dirs)
                        return self.get_folder(new_path, folder)
                    except ObjectNotFoundException:
                        raise ObjectNotFoundException(emsg)
        raise ObjectNotFoundException(emsg)

    @staticmethod
    def get_network(name: str, dc):
        for network in dc.network:
            if network.name == name:
                return network
        emsg = f"Network '{name}' not found in datacenter '{dc.name}'"
        raise ObjectNotFoundException(emsg)

    def get_cluster(self, name: str, dc):
        for cluster in self._get_items_from_view(
            dc.hostFolder, [vim.ComputeResource, vim.ClusterComputeResource]
        ):
            if cluster.name == name:
                return cluster
        emsg = f"Cluster '{name}' not found in datacenter '{dc.name}'"
        raise ObjectNotFoundException(emsg)

    def get_storage(self, path: str, dc):
        if "/" in path:
            cluster_name, storage_name = path.split("/", 1)
            parent = self.get_cluster(cluster_name, dc)
        else:
            parent, storage_name = dc, path

        for storage in parent.datastore:
            if storage.name == storage_name:
                return storage
        emsg = f"Storage '{storage_name}' not found in parent '{parent.name}'"
        raise ObjectNotFoundException(emsg)

    def get_dv_switch(self, name: str, dc):
        for dvs in self._get_items_from_view(
            dc.networkFolder, vim.dvs.VmwareDistributedVirtualSwitch
        ):
            if dvs.name == name:
                return dvs
        emsg = f"DVSwitch '{name}' not found in datacenter '{dc.name}'"
        raise ObjectNotFoundException(emsg)

    def get_vm(self, uuid: str, dc):
        search_index = self._si.content.searchIndex
        return search_index.FindByUuid(dc, uuid, vmSearch=True)

    def power_on_vm(self, vm):
        if vm.summary.runtime.powerState == vim.VirtualMachine.PowerState.poweredOn:
            self._logger.info("VM already powered on")
            return

        self._logger.info(f"Powering on VM '{vm.name}'")
        task = vm.PowerOn()
        self._wait_for_task(task)

    def power_off_vm(self, vm, soft: bool):
        if vm.summary.runtime.powerState == vim.VirtualMachine.PowerState.poweredOff:
            self._logger.info("VM already powered off")
            return

        self._logger.info(f"Powering off VM '{vm.name}'")
        if not soft:
            task = vm.PowerOff()
            self._wait_for_task(task)
        else:
            if vm.guest.toolsStatus != vim.vm.GuestInfo.ToolsStatus.toolsOk:
                emsg = f"VMWare Tools are not installed or running on VM '{vm.name}'"
                raise VMWareToolsNotInstalled(emsg)
            vm.ShutdownGuest()  # do not return task

    @staticmethod
    def _wait_for_task(task):
        while task.info.state in (
            vim.TaskInfo.State.running,
            vim.TaskInfo.State.queued,
        ):
            time.sleep(1)

        if task.info.state == vim.TaskInfo.State.success:
            return task.info.result
        else:
            emsg = ""
            if task.info.error.faultMessage:
                emsg = "; ".join([err.message for err in task.info.error.faultMessage])
            elif task.info.error.msg:
                emsg = task.info.error.msg
            raise TaskFaultException(emsg)
