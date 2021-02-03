import time
from datetime import datetime, timedelta

from pyVmomi import vim


class EventManager:
    class VMOSCustomization:
        START_EVENT = "CustomizationStartedEvent"
        SUCCESS_END_EVENT = "CustomizationSucceeded"
        FAILED_END_EVENT = "CustomizationFailed"
        START_EVENT_TIMEOUT = 5 * 60
        END_EVENT_TIMEOUT = 20 * 60
        START_EVENT_WAIT_TIME = 10
        END_EVENT_WAIT_TIME = 30

    def __init__(self, pv_service):
        self.pv_service = pv_service

    def _get_vm_events(
        self, si, vm, event_type_id_list, event_start_time=None, event_end_time=None
    ):
        """

        :param si:
        :param vm:
        :param event_type_id_list:
        :param event_start_time:
        :param event_end_time:
        :return:
        """
        time_filter = vim.event.EventFilterSpec.ByTime()
        time_filter.beginTime = event_start_time
        time_filter.endTime = event_end_time

        vm_events = vim.event.EventFilterSpec.ByEntity(entity=vm, recursion="self")
        filter_spec = vim.event.EventFilterSpec(
            entity=vm_events, eventTypeId=event_type_id_list, time=time_filter
        )

        return si.content.eventManager.QueryEvent(filter_spec)

    def _wait_for_event(
        self,
        si,
        vm,
        event_type_id_list,
        timeout,
        wait_time,
        logger,
        event_start_time=None,
        event_end_time=None,
    ):
        """

        :param si:
        :param vm:
        :param event_type_id_list:
        :param timeout:
        :param wait_time:
        :param logger:
        :param event_start_time:
        :param event_end_time:
        :return:
        """
        timeout_time = datetime.now() + timedelta(seconds=timeout)

        while True:
            logger.info(f"Getting VM '{vm.name}' events {event_type_id_list}...")
            events = self._get_vm_events(
                si=si,
                vm=vm,
                event_type_id_list=event_type_id_list,
                event_start_time=event_start_time,
                event_end_time=event_end_time,
            )

            if events:
                logger.info(f"Found VM '{vm.name}' events: {events}")
                return next(iter(events))

            time.sleep(wait_time)

            if datetime.now() > timeout_time:
                logger.info(
                    f"Timeout for VM '{vm.name}' events {event_type_id_list} reached"
                )
                return

    def wait_for_vm_os_customization_start_event(
        self,
        si,
        vm,
        logger,
        event_start_time=None,
        event_end_time=None,
        timeout=None,
        wait_time=None,
    ):
        """

        :param si:
        :param vm:
        :param logger:
        :param event_start_time:
        :param event_end_time:
        :param timeout:
        :param wait_time:
        :return:
        """
        timeout = timeout or self.VMOSCustomization.START_EVENT_TIMEOUT
        wait_time = wait_time or self.VMOSCustomization.START_EVENT_WAIT_TIME

        return self._wait_for_event(
            si=si,
            vm=vm,
            logger=logger,
            event_type_id_list=[self.VMOSCustomization.START_EVENT],
            timeout=timeout,
            wait_time=wait_time,
            event_start_time=event_start_time,
            event_end_time=event_end_time,
        )

    def wait_for_vm_os_customization_end_event(
        self,
        si,
        vm,
        logger,
        event_start_time=None,
        event_end_time=None,
        timeout=None,
        wait_time=None,
    ):
        """

        :param si:
        :param vm:
        :param event_start_time:
        :param event_end_time:
        :param timeout:
        :param wait_time:
        :return:
        """
        timeout = timeout or self.VMOSCustomization.END_EVENT_TIMEOUT
        wait_time = wait_time or self.VMOSCustomization.END_EVENT_WAIT_TIME

        return self._wait_for_event(
            si=si,
            vm=vm,
            logger=logger,
            event_type_id_list=[
                self.VMOSCustomization.SUCCESS_END_EVENT,
                self.VMOSCustomization.FAILED_END_EVENT,
            ],
            timeout=timeout,
            wait_time=wait_time,
            event_start_time=event_start_time,
            event_end_time=event_end_time,
        )
