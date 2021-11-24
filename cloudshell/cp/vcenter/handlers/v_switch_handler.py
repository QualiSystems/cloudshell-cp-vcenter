import attr
from pyVmomi import vim

from cloudshell.cp.vcenter.exceptions import BaseVCenterException
from cloudshell.cp.vcenter.handlers.dc_handler import DcHandler


class VSwitchNotFound(BaseVCenterException):
    def __init__(self, dc: DcHandler, name: str):
        self.dc = dc
        self.name = name
        super().__init__(f"vSwitch with name {name} not found in the {dc}")


@attr.s(auto_attribs=True)
class VSwitchHandler:
    _switch: vim.host.VirtualSwitch
