from __future__ import annotations

import re

import attr

from cloudshell.cp.core.request_actions.models import DeployApp
from cloudshell.shell.standards.core.resource_config_entities import (
    ResourceAttrRO,
    ResourceBoolAttrRO,
    ResourceListAttrRO,
)

from cloudshell.cp.vcenter import constants
from cloudshell.cp.vcenter.exceptions import BaseVCenterException


class IncorrectHddSpecFormat(BaseVCenterException):
    def __init__(self, text: str):
        self.text = text
        super().__init__(
            f"'{text}' is not a valid HDD format. Should be "
            f"Hard Disk Label: Disk Size (GB)"
        )


class ResourceAttrRODeploymentPath(ResourceAttrRO):
    def __init__(self, name, namespace="DEPLOYMENT_PATH"):
        super().__init__(name, namespace)


class ResourceBoolAttrRODeploymentPath(ResourceBoolAttrRO):
    def __init__(self, name, namespace="DEPLOYMENT_PATH", *args, **kwargs):
        super().__init__(name, namespace, *args, **kwargs)


class ResourceListAttrRODeploymentPath(ResourceListAttrRO):
    def __init__(self, name, namespace="DEPLOYMENT_PATH", *args, **kwargs):
        super().__init__(name, namespace, *args, **kwargs)


# todo move to shell standards
class ResourceIntAttrRO(ResourceAttrRO):
    def __init__(self, name, namespace, default=0):
        super().__init__(name, namespace, default)

    def __get__(self, instance, owner) -> int:
        val = super().__get__(instance, owner)
        if val is self or val is self.default:
            return val
        return int(val)


class ResourceFloatAttrRO(ResourceAttrRO):
    def __init__(self, name, namespace, default=0.0):
        super().__init__(name, namespace, default)

    def __get__(self, instance, owner) -> float:
        val = super().__get__(instance, owner)
        if val is self or val is self.default:
            return val
        return float(val)


class ResourceIntAttrRODeploymentPath(ResourceIntAttrRO):
    def __init__(self, name, namespace="DEPLOYMENT_PATH", *args, **kwargs):
        super().__init__(name, namespace, *args, **kwargs)


class ResourceFloatAttrRODeploymentPath(ResourceFloatAttrRO):
    def __init__(self, name, namespace="DEPLOYMENT_PATH", *args, **kwargs):
        super().__init__(name, namespace, *args, **kwargs)


class HddSpecsAttrRO(ResourceListAttrRODeploymentPath):
    def __get__(self, instance, owner) -> list[HddSpec]:
        val = super().__get__(instance, owner)
        if isinstance(val, list):
            val = list(map(HddSpec.from_str, val))
        return val


@attr.s(auto_attribs=True)
class HddSpec:
    num: int
    size: float = attr.ib(..., cmp=False)

    @classmethod
    def from_str(cls, text: str) -> HddSpec:
        try:
            num, size = text.split(":")
            num = int(re.search(r"\d+", num).group())
            size = float(size)
        except ValueError:
            raise IncorrectHddSpecFormat(text)
        return cls(num, size)

    @property
    def size_in_kb(self) -> int:
        return int(self.size * 2 ** 20)


class VCenterDeployAppAttributeNames:
    vm_cluster = "VM Cluster"
    vm_storage = "VM Storage"
    vm_resource_pool = "VM Resource Pool"
    vm_location = "VM Location"
    behavior_during_save = "Behavior during save"
    auto_power_on = "Auto Power On"
    auto_power_off = "Auto Power Off"
    wait_for_ip = "Wait for IP"
    auto_delete = "Auto Delete"
    autoload = "Autoload"
    ip_regex = "IP Regex"
    refresh_ip_timeout = "Refresh IP Timeout"
    customization_spec = "Customization Spec"
    hostname = "Hostname"
    private_ip = "Private IP"
    cpu_num = "CPU"
    ram_amount = "RAM"
    hdd_specs = "HDD"


class VCenterVMFromVMDeployAppAttributeNames(VCenterDeployAppAttributeNames):
    vcenter_vm = "vCenter VM"


class VCenterVMFromTemplateDeployAppAttributeNames(VCenterDeployAppAttributeNames):
    vcenter_template = "vCenter Template"


class VCenterVMFromCloneDeployAppAttributeNames(VCenterVMFromVMDeployAppAttributeNames):
    vcenter_vm_snapshot = "vCenter VM Snapshot"


class VCenterVMFromImageDeployAppAttributeNames(VCenterDeployAppAttributeNames):
    vcenter_image = "vCenter Image"
    vcenter_image_arguments = "vCenter Image Arguments"


class BaseVCenterDeployApp(DeployApp):
    ATTR_NAMES = VCenterDeployAppAttributeNames

    vm_cluster = ResourceAttrRODeploymentPath(ATTR_NAMES.vm_cluster)
    vm_storage = ResourceAttrRODeploymentPath(ATTR_NAMES.vm_storage)
    vm_resource_pool = ResourceAttrRODeploymentPath(ATTR_NAMES.vm_resource_pool)
    vm_location = ResourceAttrRODeploymentPath(ATTR_NAMES.vm_location)
    behavior_during_save = ResourceAttrRODeploymentPath(ATTR_NAMES.behavior_during_save)
    auto_power_on = ResourceBoolAttrRODeploymentPath(ATTR_NAMES.auto_power_on)
    auto_power_off = ResourceBoolAttrRODeploymentPath(ATTR_NAMES.auto_power_off)
    wait_for_ip = ResourceBoolAttrRODeploymentPath(ATTR_NAMES.wait_for_ip)
    auto_delete = ResourceBoolAttrRODeploymentPath(ATTR_NAMES.auto_delete)
    autoload = ResourceBoolAttrRODeploymentPath(ATTR_NAMES.autoload)
    ip_regex = ResourceAttrRODeploymentPath(ATTR_NAMES.ip_regex)
    refresh_ip_timeout = ResourceAttrRODeploymentPath(ATTR_NAMES.refresh_ip_timeout)
    customization_spec = ResourceAttrRODeploymentPath(ATTR_NAMES.customization_spec)
    hostname = ResourceAttrRODeploymentPath(ATTR_NAMES.hostname)
    private_ip = ResourceAttrRODeploymentPath(ATTR_NAMES.private_ip)
    cpu_num = ResourceIntAttrRODeploymentPath(ATTR_NAMES.cpu_num)
    ram_amount = ResourceFloatAttrRODeploymentPath(ATTR_NAMES.ram_amount)
    hdd_specs = HddSpecsAttrRO(ATTR_NAMES.hdd_specs)


class VMFromTemplateDeployApp(BaseVCenterDeployApp):
    ATTR_NAMES = VCenterVMFromTemplateDeployAppAttributeNames

    DEPLOYMENT_PATH = constants.VM_FROM_TEMPLATE_DEPLOYMENT_PATH
    vcenter_template = ResourceAttrRODeploymentPath(ATTR_NAMES.vcenter_template)


class VMFromImageDeployApp(BaseVCenterDeployApp):
    ATTR_NAMES = VCenterVMFromImageDeployAppAttributeNames

    DEPLOYMENT_PATH = constants.VM_FROM_IMAGE_DEPLOYMENT_PATH
    vcenter_image = ResourceAttrRODeploymentPath(ATTR_NAMES.vcenter_image)
    vcenter_image_arguments = ResourceListAttrRODeploymentPath(
        ATTR_NAMES.vcenter_image_arguments
    )


class VMFromVMDeployApp(BaseVCenterDeployApp):
    ATTR_NAMES = VCenterVMFromVMDeployAppAttributeNames

    DEPLOYMENT_PATH = constants.VM_FROM_VM_DEPLOYMENT_PATH
    vcenter_vm = ResourceAttrRODeploymentPath(ATTR_NAMES.vcenter_vm)


class VMFromLinkedCloneDeployApp(VMFromVMDeployApp):
    ATTR_NAMES = VCenterVMFromCloneDeployAppAttributeNames

    DEPLOYMENT_PATH = constants.VM_FROM_LINKED_CLONE_DEPLOYMENT_PATH
    vcenter_vm_snapshot = ResourceAttrRODeploymentPath(ATTR_NAMES.vcenter_vm_snapshot)
