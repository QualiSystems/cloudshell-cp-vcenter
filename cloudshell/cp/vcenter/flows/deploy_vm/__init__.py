from __future__ import annotations

from .from_image import VCenterDeployVMFromImageFlow
from .from_linked_clone import VCenterDeployVMFromLinkedCloneFlow
from .from_template import VCenterDeployVMFromTemplateFlow
from .from_vm import VCenterDeployVMFromVMFlow

from cloudshell.cp.vcenter.models import deploy_app

MAP_DEPLOY_APP_TO_FLOW = {
    deploy_app.VMFromVMDeployApp: VCenterDeployVMFromVMFlow,
    deploy_app.VMFromImageDeployApp: VCenterDeployVMFromImageFlow,
    deploy_app.VMFromTemplateDeployApp: VCenterDeployVMFromTemplateFlow,
    deploy_app.VMFromLinkedCloneDeployApp: VCenterDeployVMFromLinkedCloneFlow,
}


def get_deploy_flow(
    request_action,
) -> type[
    VCenterDeployVMFromVMFlow
    | VCenterDeployVMFromImageFlow
    | VCenterDeployVMFromTemplateFlow
    | VCenterDeployVMFromLinkedCloneFlow
]:
    da = request_action.da
    return MAP_DEPLOY_APP_TO_FLOW[da]


__all__ = (
    VCenterDeployVMFromVMFlow,
    VCenterDeployVMFromImageFlow,
    VCenterDeployVMFromTemplateFlow,
    VCenterDeployVMFromLinkedCloneFlow,
    get_deploy_flow,
)
