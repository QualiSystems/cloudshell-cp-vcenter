import re
import typing

import requests
from netaddr import IPNetwork
from pyVmomi import vim

from cloudshell.cp.vcenter.common.utilites.common_utils import str2bool
from cloudshell.cp.vcenter.common.utilites.io import get_path_and_name
from cloudshell.cp.vcenter.common.vcenter.task_waiter import SynchronousTaskWaiter
from cloudshell.cp.vcenter.common.vcenter.vm_location import VMLocation
from cloudshell.cp.vcenter.exceptions.reconfigure_vm import ReconfigureVMException
from cloudshell.cp.vcenter.exceptions.task_waiter import TaskFaultException


class VCenterAuthError(Exception):
    def __init__(self, message, original_exception):
        """
        :param str message:
        :param original_exception: The orginoal exception that was raised
        :return:
        """
        super(VCenterAuthError, self).__init__(message)
        self.original_exception = original_exception


class pyVmomiService:
    MAX_NUMBER_OF_VM_DISKS = 16
    SCSI_CONTROLLER_UNIT_NUMBER = 7
    WAIT_FOR_OS_CUSTOMIZATION_CUSTOM_FIELD = "Quali_wait_for_os_customization"
    WINDOWS_CUSTOMIZATION_SPEC_TYPE = "Windows"
    WINDOWS_CUSTOMIZATION_SPEC_ORG = "Quali"
    WINDOWS_CUSTOMIZATION_SPEC_NAME = "Quali"
    WINDOWS_CUSTOMIZATION_SPEC_WORKGROUP = "WORKGROUP"
    WINDOWS_CUSTOMIZATION_SPEC_DEFAULT_USER = "Administrator"
    LINUX_CUSTOMIZATION_SPEC_TYPE = "Linux"
    LINUX_CUSTOMIZATION_SPEC_TIMEZONE = "US/Pacific"

    # region consts
    ChildEntity = "childEntity"
    VM = "vmFolder"
    Network = "networkFolder"
    Datacenter = "datacenterFolder"
    Host = "hostFolder"
    Datastore = "datastoreFolder"
    Cluster = "cluster"
    # endregion

    def __init__(
        self,
        connect,
        disconnect,
        task_waiter,
        port_group_name_generator,
        vim_import=None,
    ):
        """
        :param SynchronousTaskWaiter task_waiter:
        :return:
        """
        self.pyvmomi_connect = connect
        self.pyvmomi_disconnect = disconnect
        self.task_waiter = task_waiter
        self.port_group_name_generator = port_group_name_generator
        if vim_import is None:
            from pyVmomi import vim

            self.vim = vim
        else:
            self.vim = vim_import

    def connect(self, address, user, password, port=443):
        """
        Connect to vCenter via SSL and return SI object

        :param address: vCenter address (host / ip address)
        :param user:    user name for authentication
        :param password:password for authentication
        :param port:    port for the SSL connection. Default = 443
        """

        "# Disabling urllib3 ssl warnings"
        requests.packages.urllib3.disable_warnings()

        "# Disabling SSL certificate verification"
        context = None
        import ssl

        ssl._create_default_https_context = ssl._create_unverified_context

        try:
            if context:
                try:
                    "#si = SmartConnect(host=address, user=user, pwd=password, port=port, sslContext=context)"
                    si = self.pyvmomi_connect(
                        host=address, user=user, pwd=password, port=port
                    )
                except (ssl.SSLEOFError, vim.fault.HostConnectFault):
                    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                    context.verify_mode = ssl.CERT_NONE
                    si = self.pyvmomi_connect(
                        host=address,
                        user=user,
                        pwd=password,
                        port=port,
                        sslContext=context,
                    )
            else:
                "#si = SmartConnect(host=address, user=user, pwd=password, port=port)"
                si = self.pyvmomi_connect(
                    host=address, user=user, pwd=password, port=port
                )
            return si
        except vim.fault.InvalidLogin as e:
            raise VCenterAuthError(e.msg, e)
        except IOError as e:
            # logger.info("I/O error({0}): {1}".format(e.errno, e.strerror))
            raise ValueError(
                "Cannot connect to vCenter, please check that the address is valid"
            )

    def disconnect(self, si):
        """ Disconnect from vCenter """
        self.pyvmomi_disconnect(si)

    def find_datacenter_by_name(self, si, path, name):
        """
        Finds datacenter in the vCenter or returns "None"

        :param si:         pyvmomi 'ServiceInstance'
        :param path:       the path to find the object ('dc' or 'dc/folder' or 'dc/folder/folder/etc...')
        :param name:       the datacenter name to return
        """
        return self.find_obj_by_path(si, path, name, self.Datacenter)

    def find_by_uuid(self, si, uuid, is_vm=True, path=None, data_center=None):
        """
        Finds vm/host by his uuid in the vCenter or returns "None"

        :param si:         pyvmomi 'ServiceInstance'
        :param uuid:       the object uuid
        :param path:       the path to find the object ('dc' or 'dc/folder' or 'dc/folder/folder/etc...')
        :param is_vm:     if true, search for virtual machines, otherwise search for hosts
        :param data_center:
        """

        if uuid is None:
            return None
        if path is not None:
            data_center = self.find_item_in_path_by_type(si, path, vim.Datacenter)

        search_index = si.content.searchIndex
        return search_index.FindByUuid(data_center, uuid, is_vm)

    def find_item_in_path_by_type(self, si, path, obj_type):
        """
        This function finds the first item of that type in path
        :param ServiceInstance si: pyvmomi ServiceInstance
        :param str path: the path to search in
        :param type obj_type: the vim type of the object
        :return: pyvmomi type instance object or None
        """
        if obj_type is None:
            return None

        search_index = si.content.searchIndex
        sub_folder = si.content.rootFolder

        if path is None or not path:
            return sub_folder
        paths = path.split("/")

        for currPath in paths:
            if currPath is None or not currPath:
                continue

            manage = search_index.FindChild(sub_folder, currPath)

            if isinstance(manage, obj_type):
                return manage
        return None

    def find_host_by_name(self, si, path, name):
        """
        Finds datastore in the vCenter or returns "None"

        :param si:         pyvmomi 'ServiceInstance'
        :param path:       the path to find the object ('dc' or 'dc/folder' or 'dc/folder/folder/etc...')
        :param name:       the datastore name to return
        """
        return self.find_obj_by_path(si, path, name, self.Host)

    def find_datastore_by_name(self, si, path, name):
        """
        Finds datastore in the vCenter or returns "None"

        :param si:         pyvmomi 'ServiceInstance'
        :param path:       the path to find the object ('dc' or 'dc/folder' or 'dc/folder/folder/etc...')
        :param name:       the datastore name to return
        """
        return self.find_obj_by_path(si, path, name, self.Datastore)

    def get_vswitch(self, host, vswitch_name):
        """

        :param host:
        :param vswitch_name:
        :return:
        """
        for vswitch in host.config.network.vswitch:
            if vswitch.name == vswitch_name:
                return vswitch

    def is_dvswitch(self, si, path, name, host):
        """

        :return:
        """
        dv_switch = self.get_folder(si, "{0}/{1}".format(path, name))

        if dv_switch:
            return True

        switch = self.get_vswitch(host=host, vswitch_name=name)

        if switch:
            return False

        raise ValueError(
            "vSwitch/Distributed vSwitch {0} not found in path {1}".format(path, name)
        )

    def find_dvswitch_portgroup(self, si, dv_switch_path, name):
        """
        Returns the portgroup on the dvSwitch
        :param name: str
        :param dv_switch_path: str
        :param si: service instance
        """
        dv_switch = self.get_folder(si, dv_switch_path)
        if dv_switch and dv_switch.portgroup:
            for port in dv_switch.portgroup:
                if port.name == name:
                    return port
        return None

    def find_network_by_name(self, si, path, name):
        """
        Finds network in the vCenter or returns "None"

        :param si:         pyvmomi 'ServiceInstance'
        :param path:       the path to find the object ('dc' or 'dc/folder' or 'dc/folder/folder/etc...')
        :param name:       the datastore name to return
        """
        return self.find_obj_by_path(si, path, name, self.Network)

    def find_vm_by_name(self, si, path, name):
        """
        Finds vm in the vCenter or returns "None"

        :param si:         pyvmomi 'ServiceInstance'
        :param path:       the path to find the object ('dc' or 'dc/folder' or 'dc/folder/folder/etc...')
        :param name:       the vm name to return
        """
        return self.find_obj_by_path(si, path, name, self.VM)

    def find_obj_by_path(self, si, path, name, type_name):
        """
        Finds object in the vCenter or returns "None"

        :param si:         pyvmomi 'ServiceInstance'
        :param path:       the path to find the object ('dc' or 'dc/folder' or 'dc/folder/folder/etc...')
        :param name:       the object name to return
        :param type_name:   the name of the type, can be (vm, network, host, datastore)
        """

        folder = self.get_folder(si, path)
        if folder is None:
            raise ValueError("vmomi managed object not found at: {0}".format(path))

        look_in = None
        if hasattr(folder, type_name):
            look_in = getattr(folder, type_name)
        if hasattr(folder, self.ChildEntity):
            look_in = folder
        if look_in is None:
            raise ValueError("vmomi managed object not found at: {0}".format(path))

        search_index = si.content.searchIndex
        "#searches for the specific vm in the folder"
        return search_index.FindChild(look_in, name)

    def find_dvs_by_path(self, si, path):
        """
        Finds vm in the vCenter or returns "None"
        :param si:         pyvmomi 'ServiceInstance'
        :param path:       the path to find the object ('dc' or 'dc/folder' or 'dc/folder/folder/etc...')
        """
        dvs = self.get_folder(si, path)

        if not dvs:
            raise ValueError("Could not find Default DvSwitch in path {0}".format(path))
        elif not isinstance(dvs, vim.dvs.VmwareDistributedVirtualSwitch):
            raise ValueError(
                "The object in path {0} is {1} and not a DvSwitch".format(
                    path, type(dvs)
                )
            )

        return dvs

    def get_folder(self, si, path, root=None):
        """
        Finds folder in the vCenter or returns "None"

        :param si:         pyvmomi 'ServiceInstance'
        :param path:       the path to find the object ('dc' or 'dc/folder' or 'dc/folder/folder/etc...')
        """

        search_index = si.content.searchIndex
        sub_folder = root if root else si.content.rootFolder

        if not path:
            return sub_folder

        paths = [p for p in path.split("/") if p]

        child = None
        try:
            new_root = search_index.FindChild(sub_folder, paths[0])
            if new_root:
                child = self.get_folder(si, "/".join(paths[1:]), new_root)
        except:
            child = None

        if child is None and hasattr(sub_folder, self.ChildEntity):
            new_root = search_index.FindChild(sub_folder, paths[0])
            if new_root:
                child = self.get_folder(si, "/".join(paths[1:]), new_root)

        if child is None and hasattr(sub_folder, self.VM):
            new_root = search_index.FindChild(sub_folder.vmFolder, paths[0])
            if new_root:
                child = self.get_folder(si, "/".join(paths[1:]), new_root)

        if child is None and hasattr(sub_folder, self.Datastore):
            new_root = search_index.FindChild(sub_folder.datastoreFolder, paths[0])
            if new_root:
                child = self.get_folder(si, "/".join(paths[1:]), new_root)

        if child is None and hasattr(sub_folder, self.Network):
            new_root = search_index.FindChild(sub_folder.networkFolder, paths[0])
            if new_root:
                child = self.get_folder(si, "/".join(paths[1:]), new_root)

        if child is None and hasattr(sub_folder, self.Host):
            new_root = search_index.FindChild(sub_folder.hostFolder, paths[0])
            if new_root:
                child = self.get_folder(si, "/".join(paths[1:]), new_root)

        if child is None and hasattr(sub_folder, self.Datacenter):
            new_root = search_index.FindChild(sub_folder.datacenterFolder, paths[0])
            if new_root:
                child = self.get_folder(si, "/".join(paths[1:]), new_root)

        if child is None and hasattr(sub_folder, "resourcePool"):
            new_root = search_index.FindChild(sub_folder.resourcePool, paths[0])
            if new_root:
                child = self.get_folder(si, "/".join(paths[1:]), new_root)

        return child

    def get_network_by_full_name(self, si, default_network_full_name):
        """
        Find network by a Full Name
        :param default_network_full_name: <str> Full Network Name - likes 'Root/Folder/Network'
        :return:
        """
        path, name = get_path_and_name(default_network_full_name)
        return self.find_network_by_name(si, path, name) if name else None

    def get_obj(self, content, vimtypes, name):
        """
        Return an object by name for a specific type, if name is None the
        first found object is returned

        :param content:    pyvmomi content object
        :param vimtypes:    the types of object to search
        :param name:       the object name to return
        """
        obj = None

        for vim_type in vimtypes:
            container = self._get_all_objects_by_type(content, vim_type)

            # If no name was given will return the first object from list of a objects matching the given vimtype type
            for c in container.view:
                if name:
                    if c.name == name:
                        obj = c
                        break
                else:
                    obj = c
                    break

        return obj

    @staticmethod
    def _get_all_objects_by_type(content, vimtype):
        container = content.viewManager.CreateContainerView(
            content.rootFolder, vimtype, True
        )
        return container

    @staticmethod
    def get_default_from_vcenter_by_type(si, vimtype, accept_multi):
        arr_items = pyVmomiService.get_all_items_in_vcenter(si, vimtype)
        if arr_items:
            if accept_multi or len(arr_items) == 1:
                return arr_items[0]
            raise Exception("There is more the one items of the given type")
        raise KeyError("Could not find item of the given type")

    @staticmethod
    def get_all_items_in_vcenter(si, type_filter, root=None):
        root = root if root else si.content.rootFolder
        container = si.content.viewManager.CreateContainerView(
            container=root, recursive=True
        )
        return [
            item
            for item in container.view
            if not type_filter or isinstance(item, type_filter)
        ]

    def get_or_create_custom_field(self, si, field_name, mo_type=vim.VirtualMachine):
        """

        :param si:
        :param field_name:
        :param mo_type:
        :return:
        """
        try:
            return next(
                filter(
                    lambda field: field.name == field_name,
                    si.content.customFieldsManager.field,
                )
            )
        except StopIteration:
            return si.content.customFieldsManager.AddCustomFieldDef(
                name=field_name, moType=mo_type
            )

    def set_vm_custom_field(self, si, vm, custom_field, custom_field_value):
        """

        :param si:
        :param vm:
        :param custom_field:
        :param custom_field_value:
        :return:
        """
        si.content.customFieldsManager.SetField(
            entity=vm, key=custom_field.key, value=custom_field_value
        )

    def unset_vm_custom_field(self, si, vm, custom_field):
        """

        :param si:
        :param vm:
        :param custom_field:
        :return:
        """
        si.content.customFieldsManager.SetField(
            entity=vm, key=custom_field.key, value=""
        )

    def need_to_wait_for_os_customization(self, vm):
        """

        :param vm:
        :return:
        """
        return bool(
            next(
                filter(
                    lambda field: field.value
                    == self.WAIT_FOR_OS_CUSTOMIZATION_CUSTOM_FIELD,
                    vm.customValue,
                ),
                False,
            )
        )

    class CloneVmParameters:
        """
        This is clone_vm method params object
        """

        def __init__(
            self,
            si,
            template_name,
            vm_name,
            vm_folder,
            datastore_name=None,
            cluster_name=None,
            resource_pool=None,
            power_on=True,
            snapshot="",
            customization_spec="",
            hostname="",
            password="",
            private_ip="",
            cpu="",
            ram="",
            hdd="",
        ):
            """
            Constructor of CloneVmParameters
            :param si:                  pyvmomi 'ServiceInstance'
            :param template_name:       str: the name of the template/vm to clone
            :param vm_name:             str: the name that will be given to the cloned vm
            :param vm_folder:           str: the path to the location of the template/vm to clone
            :param datastore_name:      str: the name of the datastore
            :param cluster_name:        str: the name of the dcluster
            :param resource_pool:       str: the name of the resource pool
            :param power_on:            bool: turn on the cloned vm
            :param snapshot:            str: the name of the snapshot to clone from
            :param customization_spec:  str: the name of the customization specification
            :param hostname:            str: host name that will be added to the VM
            :param password:            str: password that will be added to the Windows VM
            :param private_ip:          str: static IP that will be added to the VM
            :param cpu:                 str: the amount of CPUs
            :param ram:                 str: the amount of RAM
            :param hdd:                 str: the amount of disks
            """
            self.si = si
            self.template_name = template_name
            self.vm_name = vm_name
            self.vm_folder = vm_folder
            self.datastore_name = datastore_name
            self.cluster_name = cluster_name
            self.resource_pool = resource_pool
            self.power_on = str2bool(power_on)
            self.snapshot = snapshot
            self.customization_spec = customization_spec
            self.hostname = hostname
            self.password = password
            self.private_ip = private_ip
            self.cpu = cpu
            self.ram = ram
            self.hdd = hdd

    class CloneVmResult:
        """
        Clone vm result object, will contain the cloned vm or error message
        """

        def __init__(self, vm=None, error=None):
            """
            Constructor receives the cloned vm or the error message

            :param vm:    cloned vm
            :param error: will contain the error message if there is one
            """
            self.vm = vm
            self.error = error

    def clone_vm(self, clone_params, logger, cancellation_context):
        """
        Clone a VM from a template/VM and return the vm oject or throws argument is not valid

        :param cancellation_context:
        :param CloneVmParameters clone_params:
        :param logger:
        """

        result = self.CloneVmResult()

        if not isinstance(clone_params.si, self.vim.ServiceInstance):
            result.error = "si must be init as ServiceInstance"
            return result

        if clone_params.template_name is None:
            result.error = "template_name param cannot be None"
            return result

        if clone_params.vm_name is None:
            result.error = "vm_name param cannot be None"
            return result

        if clone_params.vm_folder is None:
            result.error = "vm_folder param cannot be None"
            return result

        datacenter = self.get_datacenter(clone_params)

        dest_folder = self._get_destination_folder(clone_params)

        vm_location = VMLocation.create_from_full_path(clone_params.template_name)

        template = self._get_template(clone_params, vm_location)

        snapshot = self._get_snapshot(clone_params, template)

        resource_pool, host = self.get_resource_pool(datacenter.name, clone_params)

        customization_spec, created_new_spec = self._prepare_customization_spec(
            clone_params=clone_params, vm_template=template
        )

        if not resource_pool and not host:
            raise ValueError(
                "The specifed host, cluster or resource pool could not be found"
            )

        "# set relo_spec"
        placement = self.vim.vm.RelocateSpec()
        if resource_pool:
            placement.pool = resource_pool
        if host:
            placement.host = host

        config_spec = self._prepare_vm_config_spec(
            vm=template,
            cpu=clone_params.cpu,
            ram=clone_params.ram,
            hdd=clone_params.hdd,
        )

        clone_spec = self.vim.vm.CloneSpec()
        clone_spec.config = config_spec

        if snapshot:
            clone_spec.snapshot = snapshot
            clone_spec.template = False
            placement.diskMoveType = "createNewChildDiskBacking"

        if customization_spec:
            clone_spec.customization = customization_spec.spec
            wait_for_os_customization_custom_field = self.get_or_create_custom_field(
                si=clone_params.si,
                field_name=self.WAIT_FOR_OS_CUSTOMIZATION_CUSTOM_FIELD,
            )
        else:
            wait_for_os_customization_custom_field = None

        placement.datastore = self._get_datastore(clone_params)

        # after deployment the vm must be powered off and will be powered on if needed by orchestration driver
        clone_spec.location = placement
        # clone_params.power_on
        # due to hotfix 1 for release 1.0,
        clone_spec.powerOn = False

        logger.info("cloning VM...")
        try:
            task = template.Clone(
                folder=dest_folder,
                name=clone_params.vm_name,
                spec=clone_spec,
            )
            vm = self.task_waiter.wait_for_task(
                task=task,
                logger=logger,
                action_name="Clone VM",
                cancellation_context=cancellation_context,
            )
        except TaskFaultException:
            for vm in dest_folder.childEntity:
                if vm.name == clone_params.vm_name:
                    self.destroy_vm(vm=vm, logger=logger)
            raise
        except vim.fault.NoPermission as error:
            logger.error("vcenter returned - no permission: {0}".format(error))
            raise Exception(
                "Permissions is not set correctly, please check the log for more info."
            )
        except Exception as e:
            logger.error("error deploying: {0}".format(e))
            raise Exception(
                "Error has occurred while deploying, please look at the log for more info."
            )

        if wait_for_os_customization_custom_field:
            self.set_vm_custom_field(
                si=clone_params.si,
                vm=vm,
                custom_field=wait_for_os_customization_custom_field,
                custom_field_value=self.WAIT_FOR_OS_CUSTOMIZATION_CUSTOM_FIELD,
            )

        result.customization_spec = (
            customization_spec.info.name if created_new_spec else None
        )

        result.vm = vm

        if all(
            [
                clone_params.password,
                customization_spec
                and customization_spec.info.type
                == self.WINDOWS_CUSTOMIZATION_SPEC_TYPE,
            ]
        ):
            result.user = self.WINDOWS_CUSTOMIZATION_SPEC_DEFAULT_USER
            result.password = clone_params.password
        else:
            result.user = None
            result.password = None

        return result

    def _get_device_unit_number_generator(self, vm):
        """Get generator for the next available device unit number."""
        unit_numbers = list(range(self.MAX_NUMBER_OF_VM_DISKS))
        unit_numbers.remove(self.SCSI_CONTROLLER_UNIT_NUMBER)

        for dev in vm.config.hardware.device:
            if hasattr(dev.backing, "fileName"):
                if dev.unitNumber in unit_numbers:
                    unit_numbers.remove(dev.unitNumber)

        for unit_number in unit_numbers:
            yield unit_number

        raise ReconfigureVMException(
            f"Unable to create a new disk device. {self.MAX_NUMBER_OF_VM_DISKS} disks limit has been exceeded"
        )

    def _get_disk_device_key_generator(self, vm):
        """Get generator for the next available disk key number."""
        all_devices_keys = [device.key for device in vm.config.hardware.device]
        last_disk_key = max(
            [
                device.key
                for device in vm.config.hardware.device
                if isinstance(device, vim.vm.device.VirtualDisk)
            ]
        )

        while True:
            last_disk_key += 1
            if last_disk_key not in all_devices_keys:
                yield last_disk_key

    def reconfigure_vm(self, vm, cpu, ram, hdd, logger):
        """

        :param vm:
        :param cpu:
        :param ram:
        :param hdd:
        :param logger:
        :return:
        """
        config_spec = self._prepare_vm_config_spec(vm=vm, cpu=cpu, ram=ram, hdd=hdd)

        task = vm.ReconfigVM_Task(spec=config_spec)

        try:
            return self.task_waiter.wait_for_task(
                task=task, logger=logger, action_name="Reconfigure VM"
            )
        except TaskFaultException as err:
            logger.error("Error during VM Reconfiguration: {}".format(err))

            raise ReconfigureVMException(f"Error during VM Reconfiguration. {err}")

    def _get_device_controller_key(self, vm):
        """Get SCSI Controller device key for the new VM disk creation.

        :param vm:
        :return:
        """
        controller_key = next(
            (
                device.key
                for device in vm.config.hardware.device
                if isinstance(device, vim.vm.device.VirtualSCSIController)
            ),
            None,
        )

        if controller_key is None:
            raise ReconfigureVMException(
                f"Unable to find Controller for the new VM Disk creation"
            )

        return controller_key

    def _prepare_vm_config_spec(self, vm, cpu, ram, hdd):
        """Prepare VM Config Spec.

        :param vm:
        :param cpu:
        :param ram:
        :param hdd:
        :return:
        """
        config_spec = vim.vm.ConfigSpec(
            cpuHotAddEnabled=True, cpuHotRemoveEnabled=True, memoryHotAddEnabled=True
        )
        cpu = int(cpu) if cpu else 0
        ram = float(ram) if ram else 0.0

        if cpu:
            config_spec.numCPUs = cpu

        if ram:
            config_spec.memoryMB = int(ram * 1024)

        if hdd:
            disks = {}

            for disk_data in [
                disk_data for disk_data in hdd.split(";") if ":" in disk_data
            ]:
                disk_name, disk_size = disk_data.split(":")
                disks[int(re.search(r"\d+", disk_name).group())] = float(disk_size)

            existing_disks = {
                int(re.search(r"\d+", device.deviceInfo.label).group()): device
                for device in vm.config.hardware.device
                if isinstance(device, vim.vm.device.VirtualDisk)
            }

            last_disk_number = max(existing_disks.keys()) if existing_disks else 0
            unit_number_generator = self._get_device_unit_number_generator(vm=vm)
            device_key_generator = self._get_disk_device_key_generator(vm=vm)

            for disk_number, disk_size in sorted(disks.items()):
                disk_size_kb = int(disk_size * 2 ** 20)

                if disk_number in existing_disks:
                    disk = existing_disks[disk_number]

                    if disk.capacityInKB == disk_size_kb:
                        continue

                    elif disk.capacityInKB > disk_size_kb:
                        raise ReconfigureVMException(
                            f"Invalid new size of 'Hard disk {disk_number}'."
                            f" Current disk size {disk.capacityInKB}KB cannot be reduced to {disk_size_kb}KB"
                        )

                    disk.capacityInKB = disk_size_kb

                    disk_spec = vim.vm.device.VirtualDeviceSpec(
                        device=disk,
                        operation=vim.vm.device.VirtualDeviceSpec.Operation.edit,
                    )
                    config_spec.deviceChange.append(disk_spec)
                else:
                    if disk_number != last_disk_number + 1:
                        raise ReconfigureVMException(
                            f"Invalid new hard disk number '{disk_number}'."
                            f" Disk must have name 'Hard disk {last_disk_number + 1}'"
                        )

                    last_disk_number += 1
                    new_disk = vim.vm.device.VirtualDisk()
                    new_disk.key = next(device_key_generator)
                    new_disk.controllerKey = self._get_device_controller_key(vm)
                    new_disk.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
                    new_disk.backing.diskMode = "persistent"
                    new_disk.unitNumber = next(unit_number_generator)
                    new_disk.capacityInKB = disk_size_kb

                    disk_spec = vim.vm.device.VirtualDeviceSpec(
                        fileOperation=vim.vm.device.VirtualDeviceSpec.FileOperation.create,
                        operation=vim.vm.device.VirtualDeviceSpec.Operation.add,
                        device=new_disk,
                    )
                    config_spec.deviceChange.append(disk_spec)

        return config_spec

    def get_datacenter(self, clone_params):
        splited = clone_params.vm_folder.split("/")
        root_path = splited[0]
        datacenter = self.get_folder(clone_params.si, root_path)
        return datacenter

    def _get_destination_folder(self, clone_params):
        managed_object = self.get_folder(clone_params.si, clone_params.vm_folder)
        dest_folder = ""
        if isinstance(managed_object, self.vim.Datacenter):
            dest_folder = managed_object.vmFolder
        elif isinstance(managed_object, self.vim.Folder):
            dest_folder = managed_object
        if not dest_folder:
            raise ValueError(
                "Failed to find folder: {0}".format(clone_params.vm_folder)
            )
        return dest_folder

    def _get_template(self, clone_params, vm_location):
        template = self.find_vm_by_name(
            clone_params.si, vm_location.path, vm_location.name
        )
        if not template:
            raise ValueError(
                "Virtual Machine Template with name {0} was not found under folder {1}".format(
                    vm_location.name, vm_location.path
                )
            )
        return template

    def _get_datastore(self, clone_params):
        datastore = ""
        parts = clone_params.datastore_name.split("/")
        if not parts:
            raise ValueError("Datastore could not be empty")
        name = parts[len(parts) - 1]
        if name:
            datastore = self.get_obj(
                clone_params.si.content, [[self.vim.Datastore]], name
            )
        if not datastore:
            datastore = self.get_obj(
                clone_params.si.content, [[self.vim.StoragePod]], name
            )
            if datastore:
                datastore = sorted(
                    datastore.childEntity,
                    key=lambda data: data.summary.freeSpace,
                    reverse=True,
                )[0]

        if not datastore:
            raise ValueError(
                'Could not find Datastore: "{0}"'.format(clone_params.datastore_name)
            )
        return datastore

    def get_resource_pool(self, datacenter_name, clone_params):

        obj_name = (
            "{0}/{1}/{2}".format(
                datacenter_name, clone_params.cluster_name, clone_params.resource_pool
            )
            .rstrip("/")
            .split("/")[-1]
        )
        # obj = self.get_folder(clone_params.si, resource_full_path)
        accepted_types = [
            [vim.ResourcePool],
            [vim.ClusterComputeResource],
            [vim.HostSystem],
        ]
        obj = self.get_obj(clone_params.si.content, accepted_types, obj_name)

        resource_pool = None
        host = None
        if isinstance(obj, self.vim.HostSystem):
            host = obj
            resource_pool = obj.parent.resourcePool

        elif isinstance(obj, self.vim.ResourcePool):
            resource_pool = obj

        elif isinstance(obj, self.vim.ClusterComputeResource):
            resource_pool = obj.resourcePool

        return resource_pool, host

    def destroy_vm(self, vm, logger):
        """
        destroy the given vm
        :param vm: virutal machine pyvmomi object
        :param logger:
        """

        self.power_off_before_destroy(logger, vm)

        logger.info(("Destroying VM {0}".format(vm.name)))

        task = vm.Destroy_Task()
        return self.task_waiter.wait_for_task(
            task=task, logger=logger, action_name="Destroy VM"
        )

    def power_off_before_destroy(self, logger, vm):
        if vm.runtime.powerState == "poweredOn":
            logger.info(
                (
                    "The current powerState is: {0}. Attempting to power off {1}".format(
                        vm.runtime.powerState, vm.name
                    )
                )
            )
            task = vm.PowerOffVM_Task()
            self.task_waiter.wait_for_task(
                task=task, logger=logger, action_name="Power Off Before Destroy"
            )

    def destroy_vm_by_name(self, si, vm_name, vm_path, logger):
        """
        destroy the given vm
        :param si:      pyvmomi 'ServiceInstance'
        :param vm_name: str name of the vm to destroyed
        :param vm_path: str path to the vm that will be destroyed
        :param logger:
        """
        if vm_name is not None:
            vm = self.find_vm_by_name(si, vm_path, vm_name)
            if vm:
                return self.destroy_vm(vm, logger)
        raise ValueError("vm not found")

    def destroy_vm_by_uuid(self, si, vm_uuid, vm_path, logger):
        """
        destroy the given vm
        :param si:      pyvmomi 'ServiceInstance'
        :param vm_uuid: str uuid of the vm to destroyed
        :param vm_path: str path to the vm that will be destroyed
        :param logger:
        """
        if vm_uuid is not None:
            vm = self.find_by_uuid(si, vm_uuid, vm_path)
            if vm:
                return self.destroy_vm(vm, logger)
        # return 'vm not found'
        # for apply the same Interface as for 'destroy_vm_by_name'
        raise ValueError("vm not found")

    def get_vm_by_uuid(self, si, vm_uuid):
        return self.find_by_uuid(si, vm_uuid, True)

    def get_network_by_name_from_vm(self, vm, network_name):
        for network in vm.network:
            if network_name == network.name:
                return network
        return None

    def get_network_by_key_from_vm(self, vm, network_key):
        for network in vm.network:
            if hasattr(network, "key") and network_key == network.key:
                return network
        return

    def get_network_by_mac_address(self, vm, mac_address):
        backing = [
            device.backing
            for device in vm.config.hardware.device
            if isinstance(device, vim.vm.device.VirtualEthernetCard)
            and hasattr(device, "macAddress")
            and device.macAddress == mac_address
        ]

        if backing:
            back = backing[0]
            if hasattr(back, "network"):
                return back.network
            if hasattr(back, "port"):
                return back.port
        return None

    def get_vnic_by_mac_address(self, vm, mac_address):
        for device in vm.config.hardware.device:
            if (
                isinstance(device, vim.vm.device.VirtualEthernetCard)
                and hasattr(device, "macAddress")
                and device.macAddress == mac_address
            ):
                # mac address is unique
                return device
        return None

    @staticmethod
    def vm_reconfig_task(vm, device_change):
        """
        Create Task for VM re-configure
        :param vm: <vim.vm obj> VM which will be re-configure
        :param device_change:
        :return: Task
        """
        config_spec = vim.vm.ConfigSpec(deviceChange=device_change)
        task = vm.ReconfigVM_Task(config_spec)
        return task

    @staticmethod
    def vm_get_network_by_name(vm, network_name):
        """
        Try to find Network scanning all attached to VM networks
        :param vm: <vim.vm>
        :param network_name: <str> name of network
        :return: <vim.vm.Network or None>
        """
        # return None
        for network in vm.network:
            if hasattr(network, "name") and network_name == network.name:
                return network
        return None

    @staticmethod
    def _get_snapshot(clone_params, template):
        snapshot_name = getattr(clone_params, "snapshot", None)
        if not snapshot_name:
            return None

        if not hasattr(template, "snapshot") and hasattr(
            template.snapshot, "rootSnapshotList"
        ):
            raise ValueError("The given vm does not have any snapshots")

        paths = snapshot_name.split("/")
        temp_snap = template.snapshot
        for path in paths:
            if path:
                root = getattr(
                    temp_snap,
                    "rootSnapshotList",
                    getattr(temp_snap, "childSnapshotList", None),
                )
                if not root:
                    temp_snap = None
                    break

                temp = pyVmomiService._get_snapshot_from_root_snapshot(path, root)

                if not temp:
                    temp_snap = None
                    break
                else:
                    temp_snap = temp

        if temp_snap:
            return temp_snap.snapshot

        raise ValueError("Could not find snapshot in vm")

    @staticmethod
    def _get_snapshot_from_root_snapshot(name, root_snapshot):
        sorted_by_creation = sorted(
            root_snapshot, key=lambda x: x.createTime, reverse=True
        )
        for snapshot_header in sorted_by_creation:
            if snapshot_header.name == name:
                return snapshot_header
        return None

    def get_folder_contents(self, folder, recursive=False):
        vms = []
        folders = []

        for item in folder.childEntity:
            if isinstance(item, self.vim.VirtualMachine):
                vms.append(item)
            elif isinstance(item, self.vim.Folder):
                folders.append(item)
                if recursive:
                    v, f = self.get_folder_contents(item, recursive)
                    vms.extend(v)
                    folders.extend(f)
        return vms, folders

    def get_vm_full_path(self, si, vm):
        """
        :param vm: vim.VirtualMachine
        :return:
        """
        folder_name = None
        folder = vm.parent

        if folder:
            folder_name = folder.name
            folder_parent = folder.parent

            while (
                folder_parent
                and folder_parent.name
                and folder_parent != si.content.rootFolder
                and not isinstance(folder_parent, vim.Datacenter)
            ):
                folder_name = folder_parent.name + "/" + folder_name
                try:
                    folder_parent = folder_parent.parent
                except Exception:
                    break
            # at this stage we receive a path like this: vm/FOLDER1/FOLDER2;
            # we're not interested in the "vm" part, so we throw that away
            folder_name = "/".join(folder_name.split("/")[1:])
        # ok, now we're adding the vm name; btw, if there is no folder, that's cool, just return vm.name
        return VMLocation.combine([folder_name, vm.name]) if folder_name else vm.name

    def _get_customization_spec_os_type(self, vm):
        if "windows" in vm.config.guestId.lower():
            return self.WINDOWS_CUSTOMIZATION_SPEC_TYPE
        elif "other" in vm.config.guestId.lower():
            raise Exception(
                f"Customization specification is not supported for the OS '{vm.config.guestId}'"
            )

        return self.LINUX_CUSTOMIZATION_SPEC_TYPE

    def _create_windows_customization_spec(self, name, password=None):
        password = (
            vim.vm.customization.Password(value=password, plainText=True)
            if password
            else None
        )

        customization_spec = vim.CustomizationSpecItem(
            info=vim.CustomizationSpecInfo(
                type=self.WINDOWS_CUSTOMIZATION_SPEC_TYPE,
                name=name,
            ),
            spec=vim.vm.customization.Specification(
                identity=vim.vm.customization.Sysprep(
                    guiUnattended=vim.vm.customization.GuiUnattended(password=password),
                    userData=vim.vm.customization.UserData(
                        computerName=vim.vm.customization.VirtualMachineNameGenerator(),
                        fullName=self.WINDOWS_CUSTOMIZATION_SPEC_NAME,
                        orgName=self.WINDOWS_CUSTOMIZATION_SPEC_ORG,
                    ),
                    identification=vim.vm.customization.Identification(
                        joinWorkgroup=self.WINDOWS_CUSTOMIZATION_SPEC_WORKGROUP
                    ),
                ),
                globalIPSettings=vim.vm.customization.GlobalIPSettings(),
                nicSettingMap=[],
                options=vim.vm.customization.WinOptions(
                    changeSID=True,
                ),
            ),
        )

        customization_spec.spec.nicSettingMap.append(
            vim.vm.customization.AdapterMapping(
                adapter=vim.vm.customization.IPSettings(
                    ip=vim.vm.customization.DhcpIpGenerator()
                )
            )
        )

        return customization_spec

    def _create_linux_customization_spec(self, name):
        customization_spec = vim.CustomizationSpecItem(
            info=vim.CustomizationSpecInfo(
                type=self.LINUX_CUSTOMIZATION_SPEC_TYPE,
                name=name,
            ),
            spec=vim.vm.customization.Specification(
                identity=vim.vm.customization.LinuxPrep(
                    hostName=vim.vm.customization.VirtualMachineNameGenerator(),
                    timeZone=self.LINUX_CUSTOMIZATION_SPEC_TIMEZONE,
                    hwClockUTC=True,
                ),
                globalIPSettings=vim.vm.customization.GlobalIPSettings(),
                nicSettingMap=[],
                options=vim.vm.customization.LinuxOptions(),
            ),
        )

        customization_spec.spec.nicSettingMap.append(
            vim.vm.customization.AdapterMapping(
                adapter=vim.vm.customization.IPSettings(
                    ip=vim.vm.customization.DhcpIpGenerator()
                )
            )
        )

        return customization_spec

    def delete_customization_spec(self, si, name):
        si.content.customizationSpecManager.DeleteCustomizationSpec(name=name)

    def _get_vm_vnics(self, vm):
        return [
            device
            for device in vm.config.hardware.device
            if isinstance(device, vim.vm.device.VirtualEthernetCard)
        ]

    def _set_customization_spec_params(
        self, customization_spec, clone_params, vm_template
    ):
        if clone_params.hostname:
            if customization_spec.info.type == self.WINDOWS_CUSTOMIZATION_SPEC_TYPE:
                customization_spec.spec.identity.userData.computerName = (
                    vim.vm.customization.FixedName(name=clone_params.hostname)
                )
            else:
                if "." in clone_params.hostname:  # check if hostname is in FQDN format
                    hostname, domain = clone_params.hostname.split(".", 1)
                    customization_spec.spec.identity.hostName = (
                        vim.vm.customization.FixedName(name=hostname)
                    )
                    customization_spec.spec.identity.domain = domain
                else:
                    customization_spec.spec.identity.hostName = (
                        vim.vm.customization.FixedName(name=clone_params.hostname)
                    )

        if clone_params.private_ip:
            vm_vnics = self._get_vm_vnics(vm_template)
            # customization spec IP configurations should be equal to the VM interfaces
            while len(customization_spec.spec.nicSettingMap) < len(vm_vnics):
                customization_spec.spec.nicSettingMap.append(
                    vim.vm.customization.AdapterMapping(
                        adapter=vim.vm.customization.IPSettings(
                            ip=vim.vm.customization.DhcpIpGenerator()
                        )
                    )
                )

            if ":" in clone_params.private_ip:
                private_ip, gateway = clone_params.private_ip.split(":")
            else:
                private_ip, gateway = clone_params.private_ip, None

            private_ip = IPNetwork(private_ip)

            if gateway is None:
                # presume Gateway is the .1 of the same subnet as the IP
                ip_octets = str(private_ip.ip).split(".")
                ip_octets[-1] = "1"
                gateway = ".".join(ip_octets)

            network_adapter = customization_spec.spec.nicSettingMap[0].adapter
            network_adapter.ip = vim.vm.customization.FixedIp(
                ipAddress=str(private_ip.ip)
            )
            network_adapter.subnetMask = str(private_ip.netmask)
            network_adapter.gateway = gateway

    def _prepare_customization_spec(self, clone_params, vm_template):
        si = clone_params.si
        created_new = False
        customization_spec = None
        need_to_add_vm_spec = any([clone_params.hostname, clone_params.private_ip])

        if need_to_add_vm_spec and clone_params.customization_spec:
            si.content.customizationSpecManager.DuplicateCustomizationSpec(
                name=clone_params.customization_spec, newName=clone_params.vm_name
            )

            customization_spec = (
                si.content.customizationSpecManager.GetCustomizationSpec(
                    name=clone_params.vm_name
                )
            )

            self._set_customization_spec_params(
                customization_spec=customization_spec,
                clone_params=clone_params,
                vm_template=vm_template,
            )

            si.content.customizationSpecManager.OverwriteCustomizationSpec(
                customization_spec
            )
            created_new = True

        elif need_to_add_vm_spec:
            os_type = self._get_customization_spec_os_type(vm_template)

            if os_type == self.WINDOWS_CUSTOMIZATION_SPEC_TYPE:
                customization_spec = self._create_windows_customization_spec(
                    name=clone_params.vm_name, password=clone_params.password
                )
            else:
                customization_spec = self._create_linux_customization_spec(
                    name=clone_params.vm_name
                )

            self._set_customization_spec_params(
                customization_spec=customization_spec,
                clone_params=clone_params,
                vm_template=vm_template,
            )

            si.content.customizationSpecManager.CreateCustomizationSpec(
                customization_spec
            )
            created_new = True

        elif clone_params.customization_spec:
            customization_spec = (
                si.content.customizationSpecManager.GetCustomizationSpec(
                    name=clone_params.customization_spec
                )
            )

        return customization_spec, created_new

    def get_available_vnics(self, vm, reserved_networks):
        """Get VM vNICs that can be used for the new connections."""
        return [
            device
            for device in vm.config.hardware.device
            if isinstance(device, vim.vm.device.VirtualEthernetCard)
            and hasattr(device, "macAddress")
            and not self.port_group_name_generator.is_generated_name(
                device.deviceInfo.summary
            )
            and device.deviceInfo.summary not in reserved_networks
        ]

    def prepare_new_vnic_type(self, vm) -> vim.vm.device.VirtualEthernetCard:
        """Prepare vNIC type for the new VM interfaces."""
        vnics = [
            device
            for device in vm.config.hardware.device
            if isinstance(device, vim.vm.device.VirtualEthernetCard)
            and hasattr(device, "macAddress")
        ]
        if vnics:
            return type(vnics[-1])

        return vim.vm.device.VirtualVmxnet3

    def prepare_vnic_spec(
        self, network, vnic_type: vim.vm.device.VirtualEthernetCard
    ) -> vim.vm.device.VirtualDeviceSpec:
        """Prepare new vNIC Specification for the connection."""
        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add

        nic_spec.device = vnic_type()
        nic_spec.device.deviceInfo = vim.Description()
        nic_spec.device.deviceInfo.summary = ""
        nic_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic_spec.device.backing.useAutoDetect = False
        nic_spec.device.backing.deviceName = network.name
        nic_spec.device.backing.network = network
        nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic_spec.device.connectable.startConnected = True
        nic_spec.device.connectable.allowGuestControl = True
        nic_spec.device.connectable.connected = False
        nic_spec.device.connectable.status = "untried"
        nic_spec.device.wakeOnLanEnabled = True
        nic_spec.device.addressType = "assigned"

        return nic_spec

    def add_vnics_to_vm(
        self, vm, vnics: typing.List[vim.vm.device.VirtualDeviceSpec], logger
    ):
        spec = vim.vm.ConfigSpec()
        spec.deviceChange = vnics
        task = vm.ReconfigVM_Task(spec=spec)

        try:
            self.task_waiter.wait_for_task(
                task=task, logger=logger, action_name="Add vNICs to the VM"
            )
        except TaskFaultException as err:
            logger.error("Error during adding vNICs to the VM: {}".format(err))
            raise ReconfigureVMException(
                "Error during adding vNICs to the VM. See logs for the details."
            )
