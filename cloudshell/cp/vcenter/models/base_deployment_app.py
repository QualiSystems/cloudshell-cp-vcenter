from __future__ import annotations

import re

import attr

from cloudshell.shell.standards.core.resource_config_entities import (
    ResourceAttrRO,
    ResourceBoolAttrRO,
    ResourceListAttrRO,
)

from cloudshell.cp.vcenter.exceptions import BaseVCenterException


class VCenterDeploymentAppAttributeNames:
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


class VCenterVMFromVMDeploymentAppAttributeNames(VCenterDeploymentAppAttributeNames):
    vcenter_vm = "vCenter VM"


class VCenterVMFromTemplateDeploymentAppAttributeNames(
    VCenterDeploymentAppAttributeNames
):
    vcenter_template = "vCenter Template"


class VCenterVMFromCloneDeployAppAttributeNames(
    VCenterVMFromVMDeploymentAppAttributeNames
):
    vcenter_vm_snapshot = "vCenter VM Snapshot"


class VCenterVMFromImageDeploymentAppAttributeNames(VCenterDeploymentAppAttributeNames):
    vcenter_image = "vCenter Image"
    vcenter_image_arguments = "vCenter Image Arguments"


class ResourceAttrRODeploymentPath(ResourceAttrRO):
    def __init__(self, name, namespace="DEPLOYMENT_PATH"):
        super().__init__(name, namespace)


class ResourceBoolAttrRODeploymentPath(ResourceBoolAttrRO):
    def __init__(self, name, namespace="DEPLOYMENT_PATH", *args, **kwargs):
        super().__init__(name, namespace, *args, **kwargs)


class ResourceListAttrRODeploymentPath(ResourceListAttrRO):
    def __init__(self, name, namespace="DEPLOYMENT_PATH", *args, **kwargs):
        super().__init__(name, namespace, *args, **kwargs)


class IncorrectHddSpecFormat(BaseVCenterException):
    def __init__(self, text: str):
        self.text = text
        super().__init__(
            f"'{text}' is not a valid HDD format. Should be "
            f"Hard Disk Label: Disk Size (GB)"
        )


# todo move to shell standards
class ResourceIntAttrRO(ResourceAttrRO):
    def __init__(self, name, namespace, default=0):
        super().__init__(name, namespace, default)

    def __get__(self, instance, owner) -> int:
        val = super().__get__(instance, owner)
        if val is self or val is self.default:
            return val
        return int(val) if val else None


class ResourceFloatAttrRO(ResourceAttrRO):
    def __init__(self, name, namespace, default=0.0):
        super().__init__(name, namespace, default)

    def __get__(self, instance, owner) -> float:
        val = super().__get__(instance, owner)
        if val is self or val is self.default:
            return val
        return float(val) if val else None


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
