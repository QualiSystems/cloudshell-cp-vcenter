import sys
from unittest import TestCase

from cloudshell.cp.vcenter.common.model_factory import ResourceModelParser
from cloudshell.cp.vcenter.models.DeployDataHolder import DeployDataHolder
from cloudshell.cp.vcenter.models.DeployFromTemplateDetails import (
    DeployFromTemplateDetails,
)
from cloudshell.cp.vcenter.models.vCenterCloneVMFromVMResourceModel import (
    vCenterCloneVMFromVMResourceModel,
)
from cloudshell.cp.vcenter.models.VCenterDeployVMFromLinkedCloneResourceModel import (
    VCenterDeployVMFromLinkedCloneResourceModel,
)
from cloudshell.cp.vcenter.models.vCenterVMFromTemplateResourceModel import (
    vCenterVMFromTemplateResourceModel,
)
from cloudshell.cp.vcenter.models.VMwarevCenterResourceModel import (
    VMwarevCenterResourceModel,
)
from cloudshell.cp.vcenter.vm.deploy import VirtualMachineDeployer

if sys.version_info >= (3, 0):
    from unittest.mock import MagicMock
else:
    from mock import MagicMock


class TestVirtualMachineDeployer(TestCase):
    def setUp(self):
        self.name = "name"
        self.uuid = "uuid"
        self.name_gen = MagicMock(return_value=self.name)
        self.pv_service = MagicMock()
        self.si = MagicMock()
        self.clone_parmas = MagicMock()
        self.clone_res = MagicMock()
        self.clone_res.error = None
        self.clone_res.vm = MagicMock()
        self.clone_res.vm.summary = MagicMock()
        self.clone_res.vm.summary.config = MagicMock()
        self.clone_res.vm.summary.config.uuid = self.uuid
        self.pv_service.CloneVmParameters = MagicMock(return_value=self.clone_parmas)
        self.pv_service.clone_vm = MagicMock(return_value=self.clone_res)
        self.image_deployer = MagicMock()
        self.image_deployer.deploy_image = MagicMock(return_value=True)
        self.vm = MagicMock()
        self.vm.config = MagicMock()
        self.vm.config.uuid = self.uuid
        self.pv_service.find_vm_by_name = MagicMock(return_value=self.vm)
        self.model_parser = ResourceModelParser()
        self.vm_details_provider = MagicMock()
        self.folder_manager = MagicMock()
        self.deployer = VirtualMachineDeployer(
            pv_service=self.pv_service,
            name_generator=self.name_gen,
            ovf_service=self.image_deployer,
            resource_model_parser=self.model_parser,
            vm_details_provider=self.vm_details_provider,
            folder_manager=self.folder_manager,
        )

    def test_vm_deployer(self):
        deploy_from_template_details = DeployFromTemplateDetails(
            vCenterVMFromTemplateResourceModel(), "VM Deployment"
        )
        deploy_from_template_details.template_resource_model.vcenter_name = (
            "vcenter_resource_name"
        )

        resource_context = self._create_vcenter_resource_context()
        cancellation_context = MagicMock()
        cancellation_context.is_cancelled = False

        res = self.deployer.deploy_from_template(
            si=self.si,
            data_holder=deploy_from_template_details,
            vcenter_data_model=resource_context,
            app_resource_model=MagicMock(),
            logger=MagicMock(),
            session=MagicMock(),
            reservation_id=MagicMock(),
            cancellation_context=cancellation_context,
        )

        self.assertEqual(res.vmName, self.name)
        self.assertEqual(res.vmUuid, self.uuid)
        self.pv_service.CloneVmParameters.assert_called()

    def test_clone_deployer(self):
        deploy_from_template_details = DeployFromTemplateDetails(
            vCenterCloneVMFromVMResourceModel(), "VM Deployment"
        )
        deploy_from_template_details.template_resource_model.vcenter_name = (
            "vcenter_resource_name"
        )
        deploy_from_template_details.vcenter_vm = "name"
        resource_context = self._create_vcenter_resource_context()
        reservation_id = MagicMock()
        cancellation_context = MagicMock()
        cancellation_context.is_cancelled = False

        res = self.deployer.deploy_clone_from_vm(
            si=self.si,
            data_holder=deploy_from_template_details,
            app_resource_model=MagicMock(),
            vcenter_data_model=resource_context,
            logger=MagicMock(),
            session=MagicMock(),
            reservation_id=reservation_id,
            cancellation_context=cancellation_context,
        )

        self.assertEqual(res.vmName, self.name)
        self.assertEqual(res.vmUuid, self.uuid)
        self.pv_service.CloneVmParameters.assert_called()

    def test_snapshot_deployer(self):
        deploy_from_template_details = DeployFromTemplateDetails(
            VCenterDeployVMFromLinkedCloneResourceModel(), "VM Deployment"
        )
        deploy_from_template_details.template_resource_model.vcenter_name = (
            "vcenter_resource_name"
        )
        deploy_from_template_details.vcenter_vm_snapshot = "name/shanpshot"
        resource_context = self._create_vcenter_resource_context()
        cancellation_context = MagicMock()
        cancellation_context.is_cancelled = False

        res = self.deployer.deploy_from_linked_clone(
            si=self.si,
            data_holder=deploy_from_template_details,
            app_resource_model=MagicMock(),
            vcenter_data_model=resource_context,
            logger=MagicMock(),
            session=MagicMock(),
            reservation_id=MagicMock(),
            cancellation_context=cancellation_context,
        )

        self.assertEqual(res.vmName, self.name)
        self.assertEqual(res.vmUuid, self.uuid)
        self.pv_service.CloneVmParameters.assert_called()

    def _create_vcenter_resource_context(self):
        vc = VMwarevCenterResourceModel()
        vc.user = "user"
        vc.password = "123"
        vc.default_dvswitch = "switch1"
        vc.holding_network = "anetwork"
        vc.vm_cluster = "Quali"
        vc.vm_location = "Quali"
        vc.vm_resource_pool = "Quali"
        vc.vm_storage = "Quali"
        vc.shutdown_method = "hard"
        vc.ovf_tool_path = "C\\program files\ovf"
        vc.execution_server_selector = ""
        vc.reserved_networks = "vlan65"
        vc.default_datacenter = "QualiSB"

        return vc

    def test_vm_deployer_error(self):
        self.clone_res.error = MagicMock()

        self.pv_service.CloneVmParameters = MagicMock(return_value=self.clone_parmas)
        self.pv_service.clone_vm = MagicMock(return_value=self.clone_res)
        deploy_from_template_details = DeployFromTemplateDetails(
            vCenterVMFromTemplateResourceModel(), "VM Deployment"
        )
        deploy_from_template_details.template_resource_model.vcenter_name = (
            "vcenter_resource_name"
        )

        vcenter_data_model = self._create_vcenter_resource_context()

        self.assertRaises(
            Exception,
            self.deployer.deploy_from_template,
            self.si,
            MagicMock(),
            MagicMock(),
            deploy_from_template_details,
            MagicMock(),
            vcenter_data_model,
            MagicMock(),
            MagicMock(),
        )
        self.pv_service.CloneVmParameters.assert_called()

    def test_vm_deployer_image(self):
        params = DeployDataHolder(
            {
                "app_name": "appName",
                "vcenter_name": "vCenter",
                "image_params": {
                    "vcenter_image": "c:\image.ovf",
                    "vm_cluster": "QualiSB Cluster",
                    "vm_resource_pool": "LiverPool",
                    "vm_storage": "eric ds cluster",
                    "default_datacenter": "QualiSB",
                    "vm_location": "vm_location",
                    "auto_power_on": "False",
                    "_vcenter_name": "vCenter",
                    "vcenter_image_arguments": "--compress=9,--schemaValidate,--etc",
                    "ip_regex": "",
                    "refresh_ip_timeout": "10",
                    "auto_power_off": "True",
                    "auto_delete": "True",
                    "cpu": "",
                    "ram": "",
                    "hdd": "",
                },
            }
        )

        connectivity = MagicMock()
        connectivity.address = "vcenter ip or name"
        connectivity.user = "user"
        connectivity.password = "password"
        session = MagicMock()
        vcenter_data_model = MagicMock()
        vcenter_data_model.default_datacenter = "qualisb"
        resource_context = MagicMock()
        cancellation_context = MagicMock()
        cancellation_context.is_cancelled = False

        res = self.deployer.deploy_from_image(
            si=self.si,
            logger=MagicMock(),
            session=session,
            vcenter_data_model=vcenter_data_model,
            data_holder=params,
            resource_context=resource_context,
            reservation_id=MagicMock(),
            cancellation_context=cancellation_context,
        )

        self.assertEqual(res.vmName, self.name)
        self.assertEqual(res.vmUuid, self.uuid)

    def test_vm_deployer_image_no_res(self):
        self.image_deployer.deploy_image = MagicMock(return_value=None)
        params = DeployDataHolder(
            {
                "image_url": "c:\image.ovf",
                "cluster_name": "QualiSB Cluster",
                "resource_pool": "LiverPool",
                "datastore_name": "eric ds cluster",
                "datacenter_name": "QualiSB",
                "power_on": False,
                "app_name": "appName",
                "user_arguments": ["--compress=9", "--schemaValidate", "--etc"],
            }
        )

        connectivity = MagicMock()
        connectivity.address = "vcenter ip or name"
        connectivity.user = "user"
        connectivity.password = "password"

        self.assertRaises(
            Exception, self.deployer.deploy_from_image, self.si, params, connectivity
        )

    def test_vm_deployer_image_no_vm(self):
        self.pv_service.find_vm_by_name = MagicMock(return_value=None)
        params = DeployDataHolder(
            {
                "image_url": "c:\image.ovf",
                "cluster_name": "QualiSB Cluster",
                "resource_pool": "LiverPool",
                "datastore_name": "eric ds cluster",
                "datacenter_name": "QualiSB",
                "power_on": False,
                "app_name": "appName",
                "user_arguments": ["--compress=9", "--schemaValidate", "--etc"],
            }
        )

        connectivity = MagicMock()
        connectivity.address = "vcenter ip or name"
        connectivity.user = "user"
        connectivity.password = "password"

        self.assertRaises(
            Exception, self.deployer.deploy_from_image, self.si, params, connectivity
        )
