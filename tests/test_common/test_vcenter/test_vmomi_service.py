import sys
import unittest
from datetime import datetime

from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim

from cloudshell.cp.vcenter.common.vcenter.vmomi_service import pyVmomiService

from tests.utils.testing_credentials import TestCredentials

if sys.version_info >= (3, 0):
    from unittest.mock import MagicMock, create_autospec
else:
    from mock import MagicMock, create_autospec


class TestVmomiService(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def integration_clone_vm_destory(self):
        """
        Checks whether clone_vm and destroy methods works
        """
        "#arrange"
        cred = TestCredentials()
        pv_service = pyVmomiService(SmartConnect, Disconnect, MagicMock(), MagicMock())
        si = pv_service.connect(cred.host, cred.username, cred.password)

        params = pv_service.CloneVmParameters(
            si=si, template_name="DC0_C0_RP0_VM20", vm_name="my_clone", vm_folder="DC0"
        )
        "#act"
        now = datetime.now()
        res = pv_service.clone_vm(clone_params=params, logger=MagicMock())

        "#assert"
        self.assertTrue(type(res.vm), vim.VirtualMachine)

        "#teardown"
        now = datetime.now()
        if res.error is None and res.vm is not None:
            destroyed = pv_service.destroy_vm(vm=res.vm, logger=MagicMock())

        print(("destroy took: {0}".format(str(datetime.now() - now))))

        self.assertIsNone(destroyed)

    def test_clone_vm_power_on_false(self):
        """
        Checks clone_vm
        """
        "#arrange"
        si = MagicMock(spec=vim.ServiceInstance)
        vim_mock = MagicMock()
        vim_mock.vm = MagicMock()
        vim_mock.vm.RelocateSpec = MagicMock()
        vim_mock.vm.CloneSpec = MagicMock()
        vim_mock.Datacenter = vim.Datacenter
        vim_mock.Datastore = vim.Datastore
        vim_mock.ServiceInstance = vim.ServiceInstance

        datacenter = MagicMock(spec=vim.Datacenter)
        template = MagicMock(spec=vim.VirtualMachine)
        template.datastore = [MagicMock()]

        pv_service = pyVmomiService(
            None, None, MagicMock(), MagicMock(), vim_import=vim_mock
        )
        pv_service.find_vm_by_name = MagicMock(return_value=template)
        pv_service.get_obj = MagicMock()
        pv_service.get_folder = MagicMock(return_value=datacenter)
        pv_service._get_datastore = MagicMock(
            return_value=MagicMock(spec=vim.Datastore)
        )
        pv_service.get_resource_pool = MagicMock(
            return_value=(MagicMock(spec=vim.ResourcePool), None)
        )

        params = pv_service.CloneVmParameters(
            si=si,
            template_name="my_temp",
            vm_name="my_name",
            vm_folder="my_folder",
            power_on=False,
        )

        "#act"
        res = pv_service.clone_vm(
            clone_params=params, logger=MagicMock(), cancellation_context=MagicMock()
        )

        "#assert"
        self.assertIsNone(res.error)
        self.assertTrue(vim_mock.vm.RelocateSpec.called)
        self.assertTrue(vim_mock.vm.CloneSpec.called)
        self.assertTrue(pv_service.get_folder.called)
        self.assertTrue(pv_service.find_vm_by_name.called)
        self.assertTrue(pv_service.task_waiter.wait_for_task.called)

    def test_clone_vm_resource_pool_is_not_empty(self):
        """
        Checks clone_vm
        """
        "#arrange"
        si = MagicMock(spec=vim.ServiceInstance)
        vim_mock = MagicMock()
        vim_mock.vm = MagicMock()
        vim_mock.vm.RelocateSpec = MagicMock()
        vim_mock.vm.CloneSpec = MagicMock()
        vim_mock.Datacenter = vim.Datacenter
        vim_mock.Datastore = vim.Datastore
        vim_mock.ServiceInstance = vim.ServiceInstance

        datacenter = MagicMock(spec=vim.Datacenter)
        template = MagicMock(spec=vim.VirtualMachine)
        template.datastore = [MagicMock()]

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock(), vim_mock)
        pv_service.find_vm_by_name = MagicMock(return_value=template)
        pv_service.get_obj = MagicMock()
        pv_service.get_folder = MagicMock(return_value=datacenter)
        pv_service._get_datastore = MagicMock(
            return_value=MagicMock(spec=vim.Datastore)
        )
        pv_service.get_resource_pool = MagicMock(
            return_value=(MagicMock(spec=vim.ResourcePool), None)
        )

        params = pv_service.CloneVmParameters(
            si=si,
            template_name="my_temp",
            vm_name="my_name",
            vm_folder="my_folder",
            resource_pool="my_resource_pool",
        )

        "#act"
        res = pv_service.clone_vm(
            clone_params=params, logger=MagicMock(), cancellation_context=MagicMock()
        )

        "#assert"
        self.assertIsNone(res.error)
        self.assertTrue(vim_mock.vm.RelocateSpec.called)
        self.assertTrue(vim_mock.vm.CloneSpec.called)
        self.assertTrue(pv_service.get_folder.called)
        self.assertTrue(pv_service.find_vm_by_name.called)
        self.assertTrue(pv_service.task_waiter.wait_for_task.called)

    def test_clone_vm_datastore_name_is_not_none(self):
        """
        Checks clone_vm
        """
        "#arrange"
        si = MagicMock(spec=vim.ServiceInstance)
        vim_mock = MagicMock()
        vim_mock.vm = MagicMock()
        vim_mock.vm.RelocateSpec = MagicMock()
        vim_mock.vm.CloneSpec = MagicMock()
        vim_mock.Datacenter = vim.Datacenter
        vim_mock.Datastore = vim.Datastore
        vim_mock.ServiceInstance = vim.ServiceInstance

        datacenter = MagicMock(spec=vim.Datacenter)
        template = MagicMock(spec=vim.VirtualMachine)
        template.datastore = [MagicMock()]

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock(), vim_mock)
        pv_service.find_vm_by_name = MagicMock(return_value=template)
        pv_service.get_obj = MagicMock()
        pv_service.get_folder = MagicMock(return_value=datacenter)
        pv_service._get_datastore = MagicMock(
            return_value=MagicMock(spec=vim.Datastore)
        )
        pv_service.get_resource_pool = MagicMock(
            return_value=(MagicMock(spec=vim.ResourcePool), None)
        )

        params = pv_service.CloneVmParameters(
            si=si,
            template_name="my_temp",
            vm_name="my_name",
            vm_folder="my_folder",
            datastore_name="my_datastore",
        )

        "#act"
        res = pv_service.clone_vm(
            clone_params=params, logger=MagicMock(), cancellation_context=MagicMock()
        )

        "#assert"
        self.assertIsNone(res.error)
        self.assertTrue(vim_mock.vm.RelocateSpec.called)
        self.assertTrue(vim_mock.vm.CloneSpec.called)
        self.assertTrue(pv_service.get_folder.called)
        self.assertTrue(pv_service.find_vm_by_name.called)
        self.assertTrue(pv_service.task_waiter.wait_for_task.called)

    def test_clone_vm_destenation_folder_is_unsupported(self):
        """
        Checks clone_vm
        """
        "#arrange"
        si = MagicMock(spec=vim.ServiceInstance)
        vim_mock = MagicMock()
        vim_mock.vm = MagicMock()
        vim_mock.vm.RelocateSpec = MagicMock()
        vim_mock.vm.CloneSpec = MagicMock()
        vim_mock.Folder = vim.Folder
        vim_mock.Datacenter = vim.Datacenter
        vim_mock.ServiceInstance = vim.ServiceInstance

        folder = MagicMock(spec=vim.VirtualMachine)
        template = MagicMock(spec=vim.VirtualMachine)
        template.datastore = [MagicMock()]

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock(), vim_mock)
        pv_service.find_vm_by_name = MagicMock(return_value=template)
        pv_service.get_obj = MagicMock()
        pv_service.get_folder = MagicMock(return_value=folder)
        pv_service._get_datastore = MagicMock(
            return_value=MagicMock(spec=vim.Datastore)
        )
        pv_service.get_resource_pool = MagicMock(
            return_value=MagicMock(spec=vim.ResourcePool)
        )

        params = pv_service.CloneVmParameters(
            si=si, template_name="my_temp", vm_name="my_name", vm_folder="my_folder"
        )

        "#assert"
        self.assertRaises(
            ValueError, pv_service.clone_vm, params, MagicMock(), MagicMock()
        )
        self.assertTrue(pv_service.get_folder.called)
        self.assertFalse(vim_mock.vm.RelocateSpec.called)
        self.assertFalse(vim_mock.vm.CloneSpec.called)
        self.assertFalse(pv_service.find_vm_by_name.called)
        self.assertFalse(pv_service.task_waiter.wait_for_task.called)

    def test_clone_vm_destenation_folder_is_folder_type(self):
        """
        Checks clone_vm
        """
        "#arrange"
        si = MagicMock(spec=vim.ServiceInstance)
        vim_mock = MagicMock()
        vim_mock.vm = MagicMock()
        vim_mock.vm.RelocateSpec = MagicMock()
        vim_mock.vm.CloneSpec = MagicMock()
        vim_mock.Folder = vim.Folder
        vim_mock.Datacenter = vim.Datacenter
        vim_mock.ServiceInstance = vim.ServiceInstance

        folder = MagicMock(spec=vim.Folder)
        template = MagicMock(spec=vim.VirtualMachine)
        template.datastore = [MagicMock()]

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock(), vim_mock)
        pv_service.find_vm_by_name = MagicMock(return_value=template)
        pv_service.get_obj = MagicMock()
        pv_service.get_folder = MagicMock(return_value=folder)
        pv_service._get_datastore = MagicMock(
            return_value=MagicMock(spec=vim.Datastore)
        )
        pv_service.get_resource_pool = MagicMock(
            return_value=(MagicMock(spec=vim.ResourcePool), None)
        )

        params = pv_service.CloneVmParameters(
            si=si, template_name="my_temp", vm_name="my_name", vm_folder="my_folder"
        )

        "#act"
        res = pv_service.clone_vm(
            clone_params=params, logger=MagicMock(), cancellation_context=MagicMock()
        )

        "#assert"
        self.assertIsNone(res.error)
        self.assertTrue(vim_mock.vm.RelocateSpec.called)
        self.assertTrue(vim_mock.vm.CloneSpec.called)
        self.assertTrue(pv_service.get_folder.called)
        self.assertTrue(pv_service.find_vm_by_name.called)
        self.assertTrue(pv_service.task_waiter.wait_for_task.called)

    def test_clone_vm_datastore_name_is_none(self):
        """
        Checks clone_vm
        """
        "#arrange"
        si = MagicMock(spec=vim.ServiceInstance)
        vim_mock = MagicMock()
        vim_mock.vm = MagicMock()
        vim_mock.vm.RelocateSpec = MagicMock()
        vim_mock.vm.CloneSpec = MagicMock()
        vim_mock.Datacenter = vim.Datacenter
        vim_mock.ServiceInstance = vim.ServiceInstance

        datacenter = MagicMock(spec=vim.Datacenter)
        template = MagicMock(spec=vim.VirtualMachine)
        template.datastore = [MagicMock()]

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock(), vim_mock)
        pv_service.find_vm_by_name = MagicMock(return_value=template)
        pv_service.get_obj = MagicMock()
        pv_service.get_folder = MagicMock(return_value=datacenter)
        pv_service._get_datastore = MagicMock(
            return_value=MagicMock(spec=vim.Datastore)
        )
        pv_service.get_resource_pool = MagicMock(
            return_value=(MagicMock(spec=vim.ResourcePool), None)
        )

        params = pv_service.CloneVmParameters(
            si=si, template_name="my_temp", vm_name="my_name", vm_folder="my_folder"
        )
        cancellation_context = object()

        "#act"
        res = pv_service.clone_vm(
            clone_params=params,
            logger=MagicMock(),
            cancellation_context=cancellation_context,
        )

        "#assert"
        self.assertIsNone(res.error)
        self.assertTrue(vim_mock.vm.RelocateSpec.called)
        self.assertTrue(vim_mock.vm.CloneSpec.called)
        self.assertTrue(pv_service.get_folder.called)
        self.assertTrue(pv_service.find_vm_by_name.called)
        self.assertTrue(pv_service.task_waiter.wait_for_task.called)

    def test_clone_vm_vm_folder_is_none(self):
        """
        Checks clone_vm
        """
        "#arrange"
        si = create_autospec(spec=vim.ServiceInstance)

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        params = pv_service.CloneVmParameters(
            si=si, template_name="my_temp", vm_name="my_name", vm_folder=None
        )

        "#act"
        res = pv_service.clone_vm(
            clone_params=params, logger=MagicMock(), cancellation_context=MagicMock()
        )

        "#assert"
        self.assertTrue(res.error is not None)

    def test_clone_vm_vm_name_is_none(self):
        """
        Checks clone_vm
        """
        "#arrange"
        si = create_autospec(spec=vim.ServiceInstance)

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        params = pv_service.CloneVmParameters(
            si=si, template_name="my_temp", vm_name=None, vm_folder=None
        )

        "#act"
        res = pv_service.clone_vm(
            clone_params=params, logger=MagicMock(), cancellation_context=MagicMock()
        )

        "#assert"
        self.assertTrue(res.error is not None)

    def test_clone_vm_template_name_is_none(self):
        """
        Checks clone_vm
        """
        "#arrange"
        si = create_autospec(spec=vim.ServiceInstance)

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        params = pv_service.CloneVmParameters(
            si=si, template_name=None, vm_name=None, vm_folder=None
        )

        "#act"
        res = pv_service.clone_vm(
            clone_params=params, logger=MagicMock(), cancellation_context=MagicMock()
        )

        "#assert"
        self.assertTrue(res.error is not None)

    def test_clone_vm_si_is_none(self):
        """
        Checks clone_vm
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        params = pv_service.CloneVmParameters(
            si=None, template_name=None, vm_name=None, vm_folder=None
        )

        "#act"
        res = pv_service.clone_vm(
            clone_params=params, logger=MagicMock(), cancellation_context=MagicMock()
        )

        "#assert"
        self.assertTrue(res.error is not None)

    def test_destroy_vm_by_name(self):
        """
        Checks whether the vm found and call to be destroy
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())
        si.content.searchIndex = MagicMock()

        pv_service.find_vm_by_name = MagicMock(return_value=MagicMock(name="vm"))
        pv_service.destroy_vm = MagicMock(return_value=True)

        "#act"
        result = pv_service.destroy_vm_by_name(
            si=si, vm_name="vm_name:name", vm_path="fake/path", logger=MagicMock()
        )

        "#assert"
        self.assertTrue(result)
        self.assertTrue(pv_service.find_vm_by_name.called)
        self.assertTrue(pv_service.destroy_vm.called)

    def test_destroy_vm_by_uuid(self):
        """
        Checks whether the vm found and call to be destroy
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())
        si.content.searchIndex = MagicMock()

        pv_service.find_by_uuid = MagicMock(return_value=MagicMock(name="vm"))
        pv_service.destroy_vm = MagicMock(return_value=True)

        "#act"
        result = pv_service.destroy_vm_by_uuid(
            si=si,
            vm_uuid="thisuni-vers-ally-uniq-ueidentifier",
            vm_path="fake/path",
            logger=MagicMock(),
        )

        "#assert"
        self.assertTrue(result)
        self.assertTrue(pv_service.find_by_uuid.called)
        self.assertTrue(pv_service.destroy_vm.called)

    def test_get_folder_path_not_found(self):
        """
        Checks when path not found
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def find_child_mock(*args):
            root = args[0]
            if hasattr(root, pv_service.ChildEntity):
                for folder in root.childEntity:
                    if folder.name == args[1]:
                        return folder
            else:
                for folder in root:
                    if folder.name == args[1]:
                        return folder
            return None

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())
        si.content.searchIndex = MagicMock()
        si.content.searchIndex.FindChild = MagicMock(side_effect=find_child_mock)

        first_folder = MagicMock(spec=[], name="first")
        first_folder.name = "first"

        second_folder = MagicMock(spec=[], name="second")
        second_folder.name = "second"

        third_folder = MagicMock(spec=[], name="third")
        third_folder.name = "third"

        fourth_folder = MagicMock(spec=[], name="fourth")
        fourth_folder.name = "fourth"

        fifth_folder = MagicMock(spec=[], name="fifth")
        fifth_folder.name = "fifth"

        sixth_folder = MagicMock(spec=[], name="sixth")
        sixth_folder.name = "sixth"

        si.content.rootFolder = MagicMock(spec=["name", "childEntity"])
        si.content.rootFolder.name = "rootFolder"
        si.content.rootFolder.childEntity = [first_folder, second_folder]
        first_folder.vmFolder = [second_folder, sixth_folder]
        second_folder.networkFolder = [fourth_folder, third_folder]
        third_folder.hostFolder = [third_folder, fourth_folder]
        fourth_folder.datacenterFolder = [fifth_folder]
        fifth_folder.datastoreFolder = [sixth_folder]

        "#act"
        result = pv_service.get_folder(si, "first/second/third/first/fifth/sixth")

        "#assert"
        self.assertIsNone(result)

    def test_get_folder_deep_and_complex_path(self):
        """
        Checks when path is deep and complex, goes through all the folder types
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def find_child_mock(*args):
            root = args[0]
            if hasattr(root, pv_service.ChildEntity):
                for folder in root.childEntity:
                    if folder.name == args[1]:
                        return folder
            else:
                for folder in root:
                    if folder.name == args[1]:
                        return folder
            return None

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())
        si.content.searchIndex = MagicMock()
        si.content.searchIndex.FindChild = MagicMock(side_effect=find_child_mock)

        first_folder = MagicMock(spec=[], name="first")
        first_folder.name = "first"

        second_folder = MagicMock(spec=[], name="second")
        second_folder.name = "second"

        third_folder = MagicMock(spec=[], name="third")
        third_folder.name = "third"

        fourth_folder = MagicMock(spec=[], name="fourth")
        fourth_folder.name = "fourth"

        fifth_folder = MagicMock(spec=[], name="fifth")
        fifth_folder.name = "fifth"

        sixth_folder = MagicMock(spec=[], name="sixth")
        sixth_folder.name = "sixth"

        si.content.rootFolder = MagicMock()
        si.content.rootFolder.name = "rootFolder"
        si.content.rootFolder.childEntity = [first_folder, second_folder]
        first_folder.vmFolder = [second_folder, sixth_folder]
        second_folder.networkFolder = [fourth_folder, third_folder]
        third_folder.hostFolder = [third_folder, fourth_folder]
        fourth_folder.datacenterFolder = [fifth_folder]
        fifth_folder.datastoreFolder = [sixth_folder]

        "#act"
        result = pv_service.get_folder(si, "first/second/third/fourth/fifth/sixth")

        "#assert"
        self.assertEqual(result, sixth_folder)

    def test_get_folder_deep_path(self):
        """
        Checks when path is deep, more then two
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def find_child_mock(*args):
            root = args[0]
            for folder in root.childEntity:
                if folder.name == args[1]:
                    return folder
            return None

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())
        si.content.searchIndex = MagicMock()
        si.content.searchIndex.FindChild = MagicMock(side_effect=find_child_mock)

        inner_folder = MagicMock()
        inner_folder.name = "inner"

        inner_decoy_folder = MagicMock()
        inner_decoy_folder.name = "decoy"

        inner_deep_folder = MagicMock()
        inner_deep_folder.name = "inner_deep_folder"

        inner_folder.childEntity = [inner_deep_folder, inner_decoy_folder]
        inner_decoy_folder.childEntity = [inner_folder]

        si.content.rootFolder = MagicMock()
        si.content.rootFolder.childEntity = [inner_decoy_folder, inner_folder]
        si.content.rootFolder.name = "rootFolder"

        "#act"
        result = pv_service.get_folder(si, "decoy/inner/inner_deep_folder/")

        "#assert"
        self.assertEqual(result, inner_deep_folder)

    def test_get_folder_one_sub_folder(self):
        """
        Checks when path is only one level deep without '/' and in child entity
        """
        "#arrange"

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def find_child_mock(*args):
            root = args[0]
            for folder in root.childEntity:
                if folder.name == args[1]:
                    return folder
            return None

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())
        si.content.searchIndex = MagicMock()
        si.content.searchIndex.FindChild = MagicMock(side_effect=find_child_mock)

        inner_folder = MagicMock()
        inner_folder.name = "inner"

        inner_decoy_folder = MagicMock()
        inner_decoy_folder.name = "decoy"

        si.content.rootFolder = MagicMock()
        si.content.rootFolder.childEntity = [inner_decoy_folder, inner_folder]
        si.content.rootFolder.name = "rootFolder"

        "#act"
        result = pv_service.get_folder(si, "inner")

        "#assert"
        self.assertEqual(result, inner_folder)

    def test_get_folder_path_empty(self):
        """
        Checks if the receiving path is empty, the function returns root folder
        """
        "#arrange"
        folder_name = "rootFolder"

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        si.content.rootFolder = MagicMock()
        si.content.rootFolder.name = folder_name

        "#act"
        result = pv_service.get_folder(si, "")

        "#assert"
        self.assertEqual(result.name, folder_name)

    def test_get_object_by_path_checks_networkFolder(self):
        """
        Checks whether the function can grab network folder
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def search_child(*args, **keys):
            if args[0].name == pv_service.Network:
                return True
            return False

        class FolderMock:
            networkFolder = None

        folder = MagicMock(spec=FolderMock())
        folder.name = "parentFolder"
        folder.networkFolder.name = pv_service.Network
        get_folder = MagicMock(return_value=folder)
        pv_service.get_folder = get_folder

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())
        si.content.searchIndex = MagicMock()
        si.content.searchIndex.FindChild = MagicMock(side_effect=search_child)

        "#act"
        result = pv_service.find_obj_by_path(si, "", "", pv_service.Network)

        "#assert"
        self.assertTrue(result)

    def test_get_object_by_path_checks_hostFolder(self):
        """
        Checks whether the function can grab host folder
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def search_child(*args, **keys):
            if args[0].name == pv_service.Host:
                return True
            return False

        class FolderMock:
            hostFolder = None

        folder = MagicMock(spec=FolderMock())
        folder.name = "parentFolder"
        folder.hostFolder.name = pv_service.Host
        get_folder = MagicMock(return_value=folder)
        pv_service.get_folder = get_folder

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())
        si.content.searchIndex = MagicMock()
        si.content.searchIndex.FindChild = MagicMock(side_effect=search_child)

        "#act"
        result = pv_service.find_obj_by_path(si, "", "", pv_service.Host)

        "#assert"
        self.assertTrue(result)

    def test_get_object_by_path_checks_datacenterFolder(self):
        """
        Checks whether the function can grab datacenter folder
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def search_child(*args, **keys):
            if args[0].name == pv_service.Datacenter:
                return True
            return False

        class FolderMock:
            datacenterFolder = None

        folder = MagicMock(spec=FolderMock())
        folder.name = "parentFolder"
        folder.datacenterFolder.name = pv_service.Datacenter
        get_folder = MagicMock(return_value=folder)
        pv_service.get_folder = get_folder

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())
        si.content.searchIndex = MagicMock()
        si.content.searchIndex.FindChild = MagicMock(side_effect=search_child)

        "#act"
        result = pv_service.find_obj_by_path(si, "", "", pv_service.Datacenter)

        "#assert"
        self.assertTrue(result)

    def test_get_object_by_path_checks_datastoreFolder(self):
        """
        Checks whether the function can grab datastore folder
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def search_child(*args, **keys):
            if args[0].name == pv_service.Datastore:
                return True
            return False

        class FolderMock:
            datastoreFolder = None

        folder = MagicMock(spec=FolderMock())
        folder.name = "parentFolder"
        folder.datastoreFolder.name = pv_service.Datastore
        get_folder = MagicMock(return_value=folder)
        pv_service.get_folder = get_folder

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())
        si.content.searchIndex = MagicMock()
        si.content.searchIndex.FindChild = MagicMock(side_effect=search_child)

        "#act"
        result = pv_service.find_obj_by_path(si, "", "", pv_service.Datastore)

        "#assert"
        self.assertTrue(result)

    def test_get_object_by_path_checks_vmFolder(self):
        """
        Checks whether the function can grab vm folder
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def search_child(*args, **keys):
            if args[0].name == pv_service.VM:
                return True
            return False

        class FolderMock:
            vmFolder = None

        folder = MagicMock(spec=FolderMock())
        folder.name = "parentFolder"
        folder.vmFolder.name = pv_service.VM
        get_folder = MagicMock(return_value=folder)
        pv_service.get_folder = get_folder

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())
        si.content.searchIndex = MagicMock()
        si.content.searchIndex.FindChild = MagicMock(side_effect=search_child)

        "#act"
        result = pv_service.find_obj_by_path(si, "", "", pv_service.VM)

        "#assert"
        self.assertTrue(result)

    def test_get_object_by_path_checks_childEntity(self):
        """
        Checks whether the function can grab from child entities
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def search_child(*args, **keys):
            if args[0].name == pv_service.ChildEntity:
                return True
            return False

        class FolderMock:
            childEntity = None

        folder = MagicMock(spec=FolderMock())
        folder.name = pv_service.ChildEntity
        get_folder = MagicMock(return_value=folder)
        pv_service.get_folder = get_folder

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())
        si.content.searchIndex = MagicMock()
        si.content.searchIndex.FindChild = MagicMock(side_effect=search_child)

        "#act"
        result = pv_service.find_obj_by_path(si, "", "", "")

        "#assert"
        self.assertTrue(result)

    def test_get_object_by_path_no_nested_objs(self):
        """
        Checks whether the function returns 'None' if it doesn't find an object
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        get_folder = MagicMock(return_value=MagicMock(spec=[]))
        pv_service.get_folder = get_folder

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        "#act"
        self.assertRaises(ValueError, pv_service.find_obj_by_path, si, "", "", "")

    def test_get_object_by_path_no_folder_found(self):
        """
        Checks if the receiving path that does not exist
        """
        "#arrange"
        folder_name = "rootFolder"

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        si.content.rootFolder = MagicMock()
        si.content.rootFolder.name = folder_name
        pv_service.get_folder = MagicMock(return_value=None)

        "#act"
        self.assertRaises(
            ValueError,
            pv_service.find_obj_by_path,
            si,
            "nothing/to/be/found",
            "fake_vm",
            pv_service.VM,
        )

        "#assert"
        self.assertTrue(pv_service.get_folder.called)

    def test_find_item_in_path_by_type_not_found(self):
        """
        Checks whether the function can grab object by uuid
        """
        "#arrange"

        class counter:
            i = 0

        def side_eff(*args, **kwargs):
            counter.i += 1
            return "not found"

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        si.content.searchIndex = MagicMock()
        si.content.rootFolder = MagicMock()
        si.content.searchIndex.FindChild = MagicMock(side_effect=side_eff)

        "#act"
        result = pv_service.find_item_in_path_by_type(
            si, "test//dc/asd", vim.Datacenter
        )

        "#assert"
        self.assertIsNone(result)
        self.assertTrue(counter.i, 2)

    def test_find_item_in_path_by_type_complex_path(self):
        """
        Checks whether the function can grab object by uuid
        """
        "#arrange"

        class counter:
            i = 0

        def side_eff(*args, **kwargs):
            if counter.i != 1:
                counter.i = counter.i + 1
                return "not yet"
            else:
                counter.i = counter.i + 1
                return MagicMock(spec=vim.Datacenter)

        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        si.content.searchIndex = MagicMock()
        si.content.rootFolder = MagicMock()
        si.content.searchIndex.FindChild = MagicMock(side_effect=side_eff)

        "#act"
        result = pv_service.find_item_in_path_by_type(
            si, "test//dc/asd", vim.Datacenter
        )

        "#assert"
        self.assertTrue(isinstance(result, vim.Datacenter))
        self.assertTrue(counter.i, 1)

    def test_find_item_in_path_by_type_type_is_None(self):
        """
        Checks whether the function can grab object by uuid
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        si.content.searchIndex = MagicMock()
        si.content.rootFolder = MagicMock()

        "#act"
        result = pv_service.find_item_in_path_by_type(si, "test", None)

        "#assert"
        self.assertIsNone(result, si.content.rootFolder)

    def test_find_item_in_path_by_type_path_None(self):
        """
        Checks whether the function can grab object by uuid
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        si.content.searchIndex = MagicMock()
        si.content.rootFolder = MagicMock()

        "#act"
        result = pv_service.find_item_in_path_by_type(si, None, "not none")

        "#assert"
        self.assertEqual(result, si.content.rootFolder)

    def test_get_vm_by_uuid_vm_with_path(self):
        """
        Checks whether the function can grab object by uuid
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        dc = MagicMock(spec=vim.Datacenter)
        pv_service.find_item_in_path_by_type = MagicMock(return_value=dc)

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        si.content.searchIndex = MagicMock()
        si.content.searchIndex.FindByUuid = MagicMock(
            return_value="b8e4da4e-a2ff-11e5-bf7f-feff819cdc9f"
        )

        "#act"
        result = pv_service.find_by_uuid(
            si, "b8e4da4e-a2ff-11e5-bf7f-feff819cdc9f", True, "path/path/path"
        )

        "#assert"
        self.assertTrue(result)
        self.assertTrue(
            pv_service.find_item_in_path_by_type.called_with(
                si, "path/path/path", vim.Datacenter
            )
        )

    def test_get_vm_by_uuid_vm_without_uuid(self):
        """
        Checks whether the function can grab object by uuid
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        "#act"
        result = pv_service.find_by_uuid(si, None)

        "#assert"
        self.assertIsNone(result)

    def test_get_vm_by_uuid_vm_without_path(self):
        """
        Checks whether the function can grab object by uuid
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        si.content.searchIndex = MagicMock()
        si.content.searchIndex.FindByUuid = MagicMock(
            return_value="b8e4da4e-a2ff-11e5-bf7f-feff819cdc9f"
        )

        "#act"
        result = pv_service.find_by_uuid(si, "b8e4da4e-a2ff-11e5-bf7f-feff819cdc9f")

        "#assert"
        self.assertTrue(result)
        self.assertTrue(si.content.searchIndex.FindByUuid.called)

    def test_get_vm_by_name_isVm_VM_type(self):
        """
        Checks whether the function can passes vm type
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def find_obj_by_path_mock(*args, **kwargs):
            return args[3] == pv_service.VM

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        pv_service.find_obj_by_path = MagicMock(side_effect=find_obj_by_path_mock)

        "#act"
        result = pv_service.find_vm_by_name(si, "", "")

        "#assert"
        self.assertTrue(result)

    def test_get_datastore_by_name_is_Datastore_type(self):
        """
        Checks whether the function can passes datastore type
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def find_obj_by_path_mock(*args, **kwargs):
            return args[3] == pv_service.Datastore

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        pv_service.find_obj_by_path = MagicMock(side_effect=find_obj_by_path_mock)

        "#act"
        result = pv_service.find_datastore_by_name(si, "", "")

        "#assert"
        self.assertTrue(result)

    def test_get_datacenter_by_name_is_Datacenter_type(self):
        """
        Checks whether the function can passes datascenter type
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def find_obj_by_path_mock(*args, **kwargs):
            return args[3] == pv_service.Datacenter

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        pv_service.find_obj_by_path = MagicMock(side_effect=find_obj_by_path_mock)

        "#act"
        result = pv_service.find_datacenter_by_name(si, "", "")

        "#assert"
        self.assertTrue(result)

    def test_get_host_by_name_is_Host_type(self):
        """
        Checks whether the function can passes host type
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def find_obj_by_path_mock(*args, **kwargs):
            return args[3] == pv_service.Host

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        pv_service.find_obj_by_path = MagicMock(side_effect=find_obj_by_path_mock)

        "#act"
        result = pv_service.find_host_by_name(si, "", "")

        "#assert"
        self.assertTrue(result)

    def test_get_network_by_name_is_network_type(self):
        """
        Checks whether the function can passes network type
        """
        "#arrange"
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())

        def find_obj_by_path_mock(*args, **kwargs):
            return args[3] == pv_service.Network

        si = create_autospec(spec=vim.ServiceInstance)
        si.RetrieveContent = MagicMock()
        si.content = create_autospec(spec=vim.ServiceInstanceContent())

        pv_service.find_obj_by_path = MagicMock(side_effect=find_obj_by_path_mock)

        "#act"
        result = pv_service.find_network_by_name(si, "", "")

        "#assert"
        self.assertTrue(result)

    def test_connect(self):
        # arrange
        pv_service = pyVmomiService(SmartConnect, Disconnect, MagicMock(), MagicMock())
        address = MagicMock()
        user = MagicMock()
        password = MagicMock()
        pv_service.pyvmomi_connect = MagicMock()

        # act
        pv_service.connect(address, user, password)

        # assert
        self.assertTrue(pv_service.pyvmomi_connect.called)

    def test_disconnect(self):
        # arrange
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        si = create_autospec(spec=vim.ServiceInstance)
        pv_service.pyvmomi_disconnect = MagicMock()

        # act
        pv_service.disconnect(si)

        # assert
        self.assertTrue(pv_service.pyvmomi_disconnect.called)

    def test_get_network_by_full_name(self):
        # arrange
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        si = create_autospec(spec=vim.ServiceInstance)
        default_network_full_name = "Root/Folder/Folder2/Name"
        pv_service.find_network_by_name = MagicMock()

        # act
        pv_service.get_network_by_full_name(si, default_network_full_name)

        # assert
        self.assertTrue(pv_service.find_network_by_name.called)

    def test_destroy_vm(self):
        # arrange
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        pv_service.wait_for_task = MagicMock()
        vm = MagicMock()
        vm.runtime = MagicMock()
        vm.runtime.powerState = "poweredOn"
        vm.PowerOffVM_Task = MagicMock()
        vm.Destroy_Task = MagicMock()

        # act
        pv_service.destroy_vm(vm=vm, logger=MagicMock())

        # assert
        self.assertTrue(vm.PowerOffVM_Task.called)
        self.assertTrue(vm.Destroy_Task.called)

    def test_vm_get_network_by_name(self):
        # Arrange
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        pv_service.wait_for_task = MagicMock()

        network = MagicMock()
        network.name = "main_network"

        backing = MagicMock()
        backing.network = network

        virtual_card = create_autospec(vim.vm.device.VirtualEthernetCard)
        virtual_card.macAddress = "AA-BB"
        virtual_card.backing = backing

        hardware = MagicMock()
        hardware.device = [virtual_card]

        config = MagicMock()
        config.hardware = hardware

        vm = MagicMock()
        vm.config = config

        # Act
        actual_network = pv_service.get_network_by_mac_address(vm, "AA-BB")

        # Assert
        self.assertEqual(actual_network.name, "main_network")

    def test_vm_get_network_by_name_1(self):
        # Arrange
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        pv_service.wait_for_task = MagicMock()

        network = MagicMock()
        network.name = "main_network"

        backing = MagicMock()
        backing.network = network

        virtual_card = create_autospec(vim.vm.device.VirtualEthernetCard)
        virtual_card.macAddress = "AA-BB"
        virtual_card.backing = backing

        hardware = MagicMock()
        hardware.device = [virtual_card]

        config = MagicMock()
        config.hardware = hardware

        vm = MagicMock()
        vm.config = config

        # Act
        actual_network = pv_service.get_network_by_mac_address(vm, "BB-CC")

        # Assert
        self.assertIsNone(actual_network)

    def test_get_snapshot_no_snapshot_param(self):
        # Arrange
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        pv_service.wait_for_task = MagicMock()

        # Act
        actual_network = pv_service._get_snapshot(MagicMock(spec=[]), MagicMock)

        # Assert
        self.assertIsNone(actual_network)

    def test_get_snapshot_snapshot_not_found(self):
        # Arrange
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        pv_service.wait_for_task = MagicMock()

        params = MagicMock()
        params.snapshot = "aa/bb/ee"

        template = MagicMock(vim.VirtualMachine)
        template.snapshot = MagicMock()
        template.snapshot.rootSnapshotList = [MagicMock()]

        # Act
        self.assertRaises(ValueError, pv_service._get_snapshot, params, template)

    def test_get_snapshot_snapshot_has_no_root(self):
        # Arrange
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        pv_service.wait_for_task = MagicMock()

        params = MagicMock()
        params.snapshot = "aa/bb/ee"

        template = MagicMock(vim.VirtualMachine)
        template.snapshot = MagicMock()
        template.snapshot.rootSnapshotList = None

        # Act
        self.assertRaises(ValueError, pv_service._get_snapshot, params, template)

    def test_get_snapshot_snapshot(self):
        # Arrange
        pv_service = pyVmomiService(None, None, MagicMock(), MagicMock())
        pv_service.wait_for_task = MagicMock()

        params = MagicMock()
        params.snapshot = "aa/bb/ee"

        template = MagicMock(vim.VirtualMachine)
        template.snapshot = MagicMock()

        aa = MagicMock(spec=[])
        bb1 = MagicMock(spec=[])
        bb2 = MagicMock(spec=[])
        cc = MagicMock(spec=[])
        dd = MagicMock(spec=[])
        ee = MagicMock(spec=[])
        aa.name = "aa"
        aa.createTime = 1

        bb1.name = "bb"
        bb1.createTime = 1

        bb2.name = "bb"
        bb2.createTime = 2

        cc.name = "cc"
        cc.createTime = 1

        dd.name = "dd"
        dd.createTime = 1

        ee.name = "ee"
        ee.createTime = 1

        ee.snapshot = MagicMock()

        aa.childSnapshotList = [dd, bb1, bb2]
        dd.childSnapshotList = [cc]
        bb2.childSnapshotList = [dd, cc, ee]

        template.snapshot.rootSnapshotList = [aa]

        # Act
        res = pv_service._get_snapshot(params, template)

        self.assertEqual(res, ee.snapshot)
