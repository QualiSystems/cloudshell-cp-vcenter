from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING

from attrs import define, field
from pyVmomi import vim, vmodl

from cloudshell.cp.vcenter.handlers.network_handler import (
    DVPortGroupHandler,
    NetworkHandler,
    NetworkNotFound,
    get_network_handler,
)

if TYPE_CHECKING:
    from typing_extensions import Self

    from cloudshell.cp.vcenter.handlers.managed_entity_handler import (
        ManagedEntityHandler,
    )
    from cloudshell.cp.vcenter.handlers.si_handler import SiHandler


logger = logging.getLogger(__name__)


@define
class NetworkWatcher:
    _si: SiHandler
    _container: ManagedEntityHandler
    _recursive: bool = True
    _networks: dict[str, vim.Network] = field(init=False, factory=dict)
    _network_to_name: dict[vim.Network, str] = field(init=False, factory=dict)
    _collector: vmodl.query.PropertyCollector = field(init=False)
    _version: str = field(init=False, default="")
    _lock: threading.Lock = field(init=False, factory=threading.Lock)

    def __attrs_post_init__(self):
        logger.info("Creating Property Collector of Networking Watcher")
        vc_si = self._si.get_vc_obj()
        vc_container = self._container.get_vc_obj()
        view_ref = vc_si.content.viewManager.CreateContainerView(
            container=vc_container, type=[vim.Network], recursive=self._recursive
        )
        # noinspection PyUnresolvedReferences
        traversal_spec = vmodl.query.PropertyCollector.TraversalSpec()
        traversal_spec.name = "traverseEntries"
        traversal_spec.path = "view"
        traversal_spec.skip = False
        traversal_spec.type = type(view_ref)
        traversal_spec.selectSet = []

        # noinspection PyUnresolvedReferences
        obj_spec = vmodl.query.PropertyCollector.ObjectSpec()
        obj_spec.obj = view_ref
        obj_spec.skip = True
        obj_spec.selectSet = [traversal_spec]

        # noinspection PyUnresolvedReferences
        prop_spec = vmodl.query.PropertyCollector.PropertySpec()
        prop_spec.type = vim.Network  # DVPortGroup is a subclass of Network
        prop_spec.pathSet = ["name"]

        # noinspection PyUnresolvedReferences
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = [obj_spec]
        filter_spec.propSet = [prop_spec]

        collector = vc_si.content.propertyCollector.CreatePropertyCollector()
        collector.CreateFilter(filter_spec, partialUpdates=True)
        self._collector = collector

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.destroy()

    def populate_in_bg(self) -> None:
        th = threading.Thread(target=self.update_networks, kwargs={"wait": 0})
        th.start()

    def destroy(self) -> None:
        logger.info("Destroying Property Collector of Networking Watcher")
        self._collector.Destroy()

    def exists(self, name: str) -> bool:
        self.update_networks(wait=0)
        return name in self._networks

    def get_network(self, name: str) -> NetworkHandler | DVPortGroupHandler:
        self.update_networks(wait=0)
        if not (vc_net := self._networks.get(name)):
            raise NetworkNotFound(self._container, name)
        return get_network_handler(vc_net, self._si)

    def find_networks(
        self, key: Callable[[str], bool]
    ) -> Generator[NetworkHandler | DVPortGroupHandler, None, None]:
        self.update_networks(wait=0)
        for name in self.find_network_names(key):
            yield get_network_handler(self._networks[name], self._si)

    def find_network_names(
        self, key: Callable[[str], bool]
    ) -> Generator[str, None, None]:
        self.update_networks(wait=0)
        logger.debug(f"Finding networks by key={key}")
        yield from filter(key, self._networks.copy())

    def wait_appears(
        self, name: str, wait: int = 5 * 60
    ) -> NetworkHandler | DVPortGroupHandler:
        end_time = time.time() + wait
        self.update_networks(wait=0)
        while name not in self._networks and time.time() < end_time:
            self.update_networks(wait=2)
        return self.get_network(name)

    def update_networks(self, wait: int) -> None:
        with self._lock:
            self._update_networks(wait)

    def _update_networks(self, wait: int) -> None:
        options = vmodl.query.PropertyCollector.WaitOptions(maxWaitSeconds=wait)
        wait_fn = self._collector.WaitForUpdatesEx
        while update_set := wait_fn(version=self._version, options=options):
            self._version = update_set.version

            for obj_set in update_set.filterSet[0].objectSet:
                params = {c.name: c.val for c in obj_set.changeSet}
                if obj_set.kind == "enter":
                    self._networks[params["name"]] = obj_set.obj
                    self._network_to_name[obj_set.obj] = params["name"]
                elif obj_set.kind == "leave":
                    name = self._network_to_name.get(obj_set.obj)
                    if name:
                        del self._networks[name]
                        del self._network_to_name[obj_set.obj]
