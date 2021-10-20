from logging import Logger

from pyVmomi import vim  # noqa

from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ConnectionModeEnum,
)

from cloudshell.cp.vcenter.exceptions import (
    LoginException,
    ObjectNotFoundException,
    VMWareToolsNotInstalled,
)
from cloudshell.cp.vcenter.utils.cached_property import cached_property
from cloudshell.cp.vcenter.utils.client_helpers import get_si
from cloudshell.cp.vcenter.utils.task_waiter import VcenterTaskWaiter

# from cloudshell.cp.vcenter.utils.connectivity_helpers import get_vlan_spec  #  noqa


class VCenterAPIClient:
    def __init__(
        self, host: str, user: str, password: str, logger: Logger, port: int = 443
    ):
        self._host = host
        self._user = user
        self._password = password
        self._port = port
        self._logger = logger
        self._default_task_waiter = VcenterTaskWaiter(logger=logger)

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

    def get_or_create_folder(self, path: str, parent):
        folder = parent
        for folder_name in path.split("/"):
            try:
                folder = self.get_folder(folder_name, parent)
            except ObjectNotFoundException:
                folder = parent.CreateFolder(folder_name)
            parent = folder

        return folder

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

    def get_dv_switch(self, path: str, dc):
        try:
            folder_path, dv_name = path.rsplit("/", 1)
            folder = self.get_folder(folder_path, dc)
        except ValueError:
            folder, dv_name = dc.networkFolder, path

        for dvs in self._get_items_from_view(
            folder, vim.dvs.VmwareDistributedVirtualSwitch
        ):
            if dvs.name == dv_name:
                return dvs
        emsg = f"DVSwitch '{path}' not found in datacenter '{dc.name}'"
        raise ObjectNotFoundException(emsg)

    def get_vm(self, uuid: str, dc):
        search_index = self._si.content.searchIndex
        return search_index.FindByUuid(dc, uuid, vmSearch=True)

    def get_vm_by_name(self, name: str, dc):
        if "/" in name:
            path, name = name.rsplit("/", 1)
            folder = self.get_folder(path, dc.vmFolder)
        else:
            folder = dc.vmFolder

        search_index = self._si.content.searchIndex
        vm = search_index.FindChild(folder, name)

        if vm:
            return vm

        raise ObjectNotFoundException(
            f"VM '{name}' not found in datacenter '{dc.name}'"
        )

    def power_on_vm(self, vm, task_waiter=None):
        if vm.summary.runtime.powerState == vim.VirtualMachine.PowerState.poweredOn:
            self._logger.info("VM already powered on")
            return

        self._logger.info(f"Powering on VM '{vm.name}'")
        task = vm.PowerOn()
        task_waiter = task_waiter or self._default_task_waiter
        task_waiter.wait_for_task(task)

    def power_off_vm(self, vm, soft: bool, task_waiter=None):
        if vm.summary.runtime.powerState == vim.VirtualMachine.PowerState.poweredOff:
            self._logger.info("VM already powered off")
            return

        self._logger.info(f"Powering off VM '{vm.name}'")
        if not soft:
            task = vm.PowerOff()
            task_waiter = task_waiter or self._default_task_waiter
            task_waiter.wait_for_task(task)
        else:
            # todo: move to the separate method
            if vm.guest.toolsStatus != vim.vm.GuestInfo.ToolsStatus.toolsOk:
                emsg = f"VMWare Tools are not installed or running on VM '{vm.name}'"
                raise VMWareToolsNotInstalled(emsg)
            vm.ShutdownGuest()  # do not return task

    def create_dv_port_group(
        self,
        dv_switch,
        dv_port_name: str,
        vlan_range: str,
        port_mode: ConnectionModeEnum,
        promiscuous_mode: bool,
        num_ports: int = 32,
        task_waiter=None,
    ):
        port_conf_policy = (
            vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy(
                securityPolicy=vim.dvs.VmwareDistributedVirtualSwitch.SecurityPolicy(
                    allowPromiscuous=vim.BoolPolicy(value=promiscuous_mode),
                    forgedTransmits=vim.BoolPolicy(value=True),
                    macChanges=vim.BoolPolicy(value=False),
                    inherited=False,
                ),
                vlan=get_vlan_spec(port_mode, vlan_range),  # noqa
            )
        )
        dv_pg_spec = vim.dvs.DistributedVirtualPortgroup.ConfigSpec(
            name=dv_port_name,
            numPorts=num_ports,
            type=vim.dvs.DistributedVirtualPortgroup.PortgroupType.earlyBinding,
            defaultPortConfig=port_conf_policy,
        )

        task = dv_switch.AddDVPortgroup_Task([dv_pg_spec])
        self._logger.info(f"DV Port Group '{dv_port_name}' CREATE Task ...")
        task_waiter = task_waiter or self._default_task_waiter
        task_waiter.wait_for_task(task)

    def connect_vnic_to_port_group(self, vnic, port_group, vm):
        vnic.backing = (
            vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo(
                port=vim.dvs.PortConnection(
                    portgroupKey=port_group.key,
                    switchUuid=port_group.config.distributedVirtualSwitch.uuid,
                )
            )
        )
        vnic.connectable = vim.vm.device.VirtualDevice.ConnectInfo(
            connected=True,
            startConnected=True,
        )

        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        nic_spec.device = vnic
        config_spec = vim.vm.ConfigSpec(deviceChange=[nic_spec])
        task = vm.ReconfigVM_Task(config_spec)
        self._default_task_waiter.wait_for_task(task)

    def connect_vnic_to_network(self, vnic, network, vm):
        vnic.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo(
            network=network, deviceName=network.name
        )
        vnic.wakeOnLanEnabled = True
        vnic.deviceInfo = vim.Description()
        vnic.connectable = vim.vm.device.VirtualDevice.ConnectInfo(
            connected=False,
            startConnected=False,
        )
        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        nic_spec.device = vnic
        config_spec = vim.vm.ConfigSpec(deviceChange=[nic_spec])
        task = vm.ReconfigVM_Task(config_spec)
        self._default_task_waiter.wait_for_task(task)

    def get_customization_spec(self, name: str):
        return self._si.content.customizationSpecManager.GetCustomizationSpec(name)

    def clone_vm(
        self,
        vm_template,
        vm_name,
        vm_storage,
        vm_folder,
        vm_resource_pool=None,
        snapshot=None,
        customization_spec=None,
        task_waiter=None,
    ):
        """Clone VM from the given template."""
        clone_spec = vim.vm.CloneSpec(powerOn=False)
        placement = vim.vm.RelocateSpec()
        placement.datastore = vm_storage

        if vm_resource_pool:
            placement.pool = vm_resource_pool

        if snapshot:
            clone_spec.snapshot = snapshot
            placement.diskMoveType = "createNewChildDiskBacking"

        if customization_spec:
            clone_spec.customization = customization_spec.spec

        clone_spec.location = placement

        task = vm_template.Clone(folder=vm_folder, name=vm_name, spec=clone_spec)

        task_waiter = task_waiter or self._default_task_waiter
        return task_waiter.wait_for_task(task)

    def destroy_vm(self, vm, task_waiter=None):
        # todo: check if this work or we need to use commented code:

        # def destroy_vm(self, vm, logger):
        #     """
        #     destroy the given vm
        #     :param vm: virutal machine pyvmomi object
        #     :param logger:
        #     """
        #
        #     self.power_off_before_destroy(logger, vm)  # noqa
        #
        #     logger.info(("Destroying VM {0}".format(vm.name)))  # noqa
        #
        #     task = vm.Destroy_Task()  # noqa
        #     return self.task_waiter.wait_for_task(task=task, logger=logger, action_name="Destroy VM")  # noqa
        #
        # def power_off_before_destroy(self, logger, vm):
        #     if vm.runtime.powerState == 'poweredOn':
        #         logger.info(("The current powerState is: {0}. Attempting to power off {1}"  # noqa
        #                      .format(vm.runtime.powerState, vm.name)))
        #         task = vm.PowerOffVM_Task()  # noqa
        #         self.task_waiter.wait_for_task(task=task, logger=logger, action_name="Power Off Before Destroy")  # noqa

        task_waiter = task_waiter or self._default_task_waiter
        self.power_off_vm(vm, soft=True, task_waiter=task_waiter)
        task = vm.Destroy_Task()

        return task_waiter.wait_for_task(task)

    def get_vm_snapshot(self, snapshot_name, vm):
        root_snapshot = vm.snapshot
        error_msg = f"Unable to find snapshot '{snapshot_name}' under the VM: {vm.name}"

        if not root_snapshot:
            raise ObjectNotFoundException(error_msg)

        snapshots_list = root_snapshot.rootSnapshotList
        snapshot = None

        for snapshot_part in snapshot_name.split("/"):
            try:
                snapshot = next(
                    snapshot
                    for snapshot in snapshots_list
                    if snapshot.name == snapshot_part
                )
            except StopIteration:
                raise ObjectNotFoundException(error_msg)

            snapshots_list = snapshot.childSnapshotList

        if snapshot is None:
            raise ObjectNotFoundException(error_msg)

        return snapshot.snapshot
