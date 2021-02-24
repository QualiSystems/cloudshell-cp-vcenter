import ssl
from urllib.parse import quote

import OpenSSL
from packaging import version

from cloudshell.cp.vcenter.common.vcenter.vmomi_service import pyVmomiService


class GetVMConsoleCommand:
    CONSOLE_PORT = 9443
    HTTPS_PORT = 443
    VCENTER_FQDN_KEY = "VirtualCenter.FQDN"

    VCENTER_V7_VERSION = "7.0.0"

    VM_WEB_CONSOLE_LINK_V6_TPL = (
        "https://{vcenter_ip}:{console_port}/vsphere-client/webconsole.html?vmId={vm_moid}&vmName={vm_name}&"
        "serverGuid={server_guid}&host={vcenter_host}:443&sessionTicket={session_ticket}&thumbprint={thumbprint}"
    )
    VM_WEB_CONSOLE_LINK_V7_TPL = (
        "https://{vcenter_ip}/ui/webconsole.html?vmId={vm_moid}&vmName={vm_name}&"
        "serverGuid={server_guid}&host={vcenter_host}:443&sessionTicket={session_ticket}&thumbprint={thumbprint}"
    )

    def __init__(self, pv_service):
        """Init command.

        :param pv_service:
        :type pv_service: pyVmomiService
        :return:
        """
        self.pv_service = pv_service

    def _get_vcenter_host(self, si_content):
        """Get vCenter host.

        :param si_content:
        :return:
        """
        for item in si_content.setting.setting:
            if item.key == self.VCENTER_FQDN_KEY:
                return item.value

        raise Exception("Unable to find vCenter host")

    def get_vm_web_console(
        self,
        si,
        logger,
        vm_uuid,
        vcenter_ip,
    ):
        """Get VM Web console.

        :param vim.ServiceInstance si: py_vmomi service instance
        :param logger: Logger
        :param vm_uuid: uuid of the virtual machine
        :param vcenter_ip:
        """
        logger.info("Get VM Web Console ...")
        vm = self.pv_service.find_by_uuid(si, vm_uuid)

        content = si.RetrieveContent()
        ssl._create_default_https_context = ssl._create_unverified_context
        vc_cert = ssl.get_server_certificate((vcenter_ip, self.HTTPS_PORT))
        vc_pem = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, vc_cert)
        thumbprint = vc_pem.digest("sha1")

        if version.parse(si.content.about.version) >= version.parse(
            self.VCENTER_V7_VERSION
        ):
            return self.VM_WEB_CONSOLE_LINK_V7_TPL.format(
                vcenter_ip=vcenter_ip,
                vm_moid=vm._moId,
                vm_name=quote(vm.name),
                server_guid=content.about.instanceUuid,
                vcenter_host=self._get_vcenter_host(si_content=content),
                https_port=self.HTTPS_PORT,
                session_ticket=quote(content.sessionManager.AcquireCloneTicket()),
                thumbprint=quote(thumbprint.decode()),
            )
        else:
            return self.VM_WEB_CONSOLE_LINK_V6_TPL.format(
                vcenter_ip=vcenter_ip,
                console_port=self.CONSOLE_PORT,
                vm_moid=vm._moId,
                vm_name=quote(vm.name),
                server_guid=content.about.instanceUuid,
                vcenter_host=self._get_vcenter_host(si_content=content),
                https_port=self.HTTPS_PORT,
                session_ticket=quote(content.sessionManager.AcquireCloneTicket()),
                thumbprint=quote(thumbprint.decode()),
            )
