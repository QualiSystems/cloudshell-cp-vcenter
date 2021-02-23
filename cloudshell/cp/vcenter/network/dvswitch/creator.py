# -*- coding: utf-8 -*-
from threading import Lock

from pyVmomi import vim


class DvPortGroupCreator(object):
    def __init__(self, pyvmomi_service, synchronous_task_waiter):
        """

        :param pyvmomi_service:
        :param synchronous_task_waiter:
        :type synchronous_task_waiter: cloudshell.cp.vcenter.common.vcenter.task_waiter.SynchronousTaskWaiter
        :return:
        """
        self.pyvmomi_service = pyvmomi_service
        self.synchronous_task_waiter = synchronous_task_waiter
        self._lock = Lock()

    def _get_dvswitch_portgroup(
        self, si, dv_switch_path, dv_switch_name, dv_port_name, logger
    ):
        try:
            return self.pyvmomi_service.find_dvswitch_portgroup(
                si,
                "{0}/{1}".format(dv_switch_path, dv_switch_name),
                dv_port_name,
            )
        except KeyError:
            logger.debug(
                "Failed to find DV port group for {}".format(dv_port_name),
                exc_info=True,
            )

    def get_or_create_network(
        self,
        si,
        vm,
        dv_port_name,
        dv_switch_name,
        dv_switch_path,
        vlan_id,
        vlan_spec,
        logger,
        promiscuous_mode,
    ):
        network = None
        error = None
        self._lock.acquire()
        try:
            # check if the network is attached to the vm and gets it, the function doesn't goes to the vcenter
            network = self.pyvmomi_service.get_network_by_name_from_vm(vm, dv_port_name)

            # if we didn't found the network on the vm
            if network is None:
                is_dvswitch = self.pyvmomi_service.is_dvswitch(
                    si=si,
                    path=dv_switch_path,
                    name=dv_switch_name,
                    host=vm.runtime.host,
                )

                if is_dvswitch:
                    network = self._get_dvswitch_portgroup(
                        si=si,
                        dv_switch_path=dv_switch_path,
                        dv_switch_name=dv_switch_name,
                        dv_port_name=dv_port_name,
                        logger=logger,
                    )
                else:
                    network = self.pyvmomi_service.find_network_by_name(
                        si=si, path=dv_switch_path, name=dv_port_name
                    )

                # if we still couldn't get the network ---> create it(can't find it, play god!)
                if network is None:
                    if is_dvswitch:
                        self._create_dv_port_group(
                            dv_port_name,
                            dv_switch_name,
                            dv_switch_path,
                            si,
                            vlan_spec,
                            vlan_id,
                            logger,
                            promiscuous_mode,
                        )
                    else:
                        self._create_port_group(
                            dv_port_name,
                            dv_switch_name,
                            vlan_id,
                            logger,
                            promiscuous_mode,
                            vm.runtime.host,
                        )

                    network = self.pyvmomi_service.find_network_by_name(
                        si, dv_switch_path, dv_port_name
                    )

            if not network:
                raise ValueError(
                    "Could not get or create vlan named: {0}".format(dv_port_name)
                )
        except ValueError as e:
            logger.debug("Failed to find network", exc_info=True)
            error = e
        finally:
            self._lock.release()
            if error:
                raise error
            return network

    def _create_port_group(
        self,
        port_name,
        vswitch_name,
        vlan_id,
        logger,
        promiscuous_mode,
        host,
    ):
        portgroup_spec = vim.host.PortGroup.Specification()
        portgroup_spec.vswitchName = vswitch_name
        portgroup_spec.name = port_name
        portgroup_spec.vlanId = int(vlan_id)
        network_policy = vim.host.NetworkPolicy()
        network_policy.security = vim.host.NetworkPolicy.SecurityPolicy()
        network_policy.security.allowPromiscuous = promiscuous_mode.lower() == "true"
        network_policy.security.macChanges = False
        network_policy.security.forgedTransmits = True
        portgroup_spec.policy = network_policy

        host.configManager.networkSystem.AddPortGroup(portgroup_spec)

    def _create_dv_port_group(
        self,
        dv_port_name,
        dv_switch_name,
        dv_switch_path,
        si,
        spec,
        vlan_id,
        logger,
        promiscuous_mode,
    ):
        dv_switch = self.pyvmomi_service.get_folder(
            si, "{0}/{1}".format(dv_switch_path, dv_switch_name)
        )

        task = DvPortGroupCreator.dv_port_group_create_task(
            dv_port_name, dv_switch, spec, vlan_id, logger, promiscuous_mode
        )
        self.synchronous_task_waiter.wait_for_task(
            task=task,
            logger=logger,
            action_name="Create dv port group",
            hide_result=False,
        )

    @staticmethod
    def dv_port_group_create_task(
        dv_port_name, dv_switch, spec, vlan_id, logger, promiscuous_mode, num_ports=32
    ):
        """
        Create ' Distributed Virtual Portgroup' Task
        :param dv_port_name: <str>  Distributed Virtual Portgroup Name
        :param dv_switch: <vim.dvs.VmwareDistributedVirtualSwitch> Switch this Portgroup will be belong to
        :param spec:
        :param vlan_id: <int>
        :param logger:
        :param num_ports: <int> number of ports in this Group
        :param promiscuous_mode <str> 'True' or 'False' turn on/off promiscuous mode for the port group
        :return: <vim.Task> Task which really provides update
        """

        dv_pg_spec = vim.dvs.DistributedVirtualPortgroup.ConfigSpec()
        dv_pg_spec.name = dv_port_name
        dv_pg_spec.numPorts = num_ports
        dv_pg_spec.type = vim.dvs.DistributedVirtualPortgroup.PortgroupType.earlyBinding

        dv_pg_spec.defaultPortConfig = (
            vim.dvs.VmwareDistributedVirtualSwitch.VmwarePortConfigPolicy()
        )
        dv_pg_spec.defaultPortConfig.securityPolicy = (
            vim.dvs.VmwareDistributedVirtualSwitch.SecurityPolicy()
        )

        dv_pg_spec.defaultPortConfig.vlan = spec
        dv_pg_spec.defaultPortConfig.vlan.vlanId = vlan_id

        promiscuous_mode = promiscuous_mode.lower() == "true"
        dv_pg_spec.defaultPortConfig.securityPolicy.allowPromiscuous = vim.BoolPolicy(
            value=promiscuous_mode
        )
        dv_pg_spec.defaultPortConfig.securityPolicy.forgedTransmits = vim.BoolPolicy(
            value=True
        )

        dv_pg_spec.defaultPortConfig.vlan.inherited = False
        dv_pg_spec.defaultPortConfig.securityPolicy.macChanges = vim.BoolPolicy(
            value=False
        )
        dv_pg_spec.defaultPortConfig.securityPolicy.inherited = False

        task = dv_switch.AddDVPortgroup_Task([dv_pg_spec])

        logger.info("DV Port Group '{}' CREATE Task ...".format(dv_port_name))
        return task

    @staticmethod
    def dv_port_group_destroy_task(port_group):
        """
        Creates 'Destroy Distributed Virtual Portgroup' Task
        The current Portgoriup should be 'Unused' if you wanted this task will be successfully performed
        :param port_group: <vim.dvs.DistributedVirtualPortgroup>
        :return: <vim.Task> Task which really provides update
        """
        return port_group.Destroy()
