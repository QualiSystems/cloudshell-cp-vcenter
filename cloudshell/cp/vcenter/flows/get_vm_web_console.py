import ssl
from logging import Logger
from urllib.parse import quote

import OpenSSL
from packaging import version

from cloudshell.cp.vcenter.api_client import VCenterAPIClient
from cloudshell.cp.vcenter.models.deployed_app import BaseVCenterDeployedApp
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig

CONSOLE_PORT = 9443
HTTPS_PORT = 443
VCENTER_FQDN_KEY = "VirtualCenter.FQDN"

VCENTER_NEW_CONSOLE_LINK_VERSION = "6.7.0"

VM_WEB_CONSOLE_OLD_LINK_TPL = (
    "https://{vcenter_ip}:9443/vsphere-client/webconsole.html?"
    "vmId={vm_moid}"
    "&vmName={vm_name}"
    "&serverGuid={server_guid}"
    "&host={vcenter_host}:443"
    "&sessionTicket={session_ticket}"
    "&thumbprint={thumbprint}"
)
VM_WEB_CONSOLE_NEW_LINK_TPL = (
    "https://{vcenter_ip}/ui/webconsole.html?"
    "vmId={vm_moid}"
    "&vmName={vm_name}"
    "&serverGuid={server_guid}"
    "&host={vcenter_host}:443"
    "&sessionTicket={session_ticket}"
    "&thumbprint={thumbprint}"
)


def get_vm_web_console(
    vcenter_client: VCenterAPIClient,
    resource_conf: VCenterResourceConfig,
    deployed_app: BaseVCenterDeployedApp,
    logger: Logger,
) -> str:
    logger.info("Get VM Web Console ...")
    dc = vcenter_client.get_dc(resource_conf.default_datacenter)
    vm = vcenter_client.get_vm(deployed_app.vmdetails.uid, dc)

    ssl._create_default_https_context = ssl._create_unverified_context
    vc_cert = ssl.get_server_certificate((resource_conf.address, HTTPS_PORT))
    vc_pem = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, vc_cert)
    thumbprint = vc_pem.digest("sha1")

    if version.parse(vcenter_client.version) >= version.parse(
        VCENTER_NEW_CONSOLE_LINK_VERSION
    ):
        format_str = VM_WEB_CONSOLE_NEW_LINK_TPL
    else:
        format_str = VM_WEB_CONSOLE_OLD_LINK_TPL

    return format_str.format(
        vcenter_ip=resource_conf.address,
        vm_moid=vm._moId,
        vm_name=quote(vm.name),
        server_guid=vcenter_client.instance_uuid,
        vcenter_host=vcenter_client.vcenter_host,
        https_port=HTTPS_PORT,
        session_ticket=quote(vcenter_client.acquire_session_ticket()),
        thumbprint=quote(thumbprint.decode()),
    )
