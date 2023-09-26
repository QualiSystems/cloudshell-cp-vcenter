from __future__ import annotations

import logging
import time
from collections.abc import Collection
from typing import Union

from attrs import define, field
from packaging import version
from retrying import retry
from typing_extensions import Self

from cloudshell.cp.core.reservation_info import ReservationInfo

from cloudshell.cp.vcenter.handlers.folder_handler import FolderHandler
from cloudshell.cp.vcenter.handlers.network_handler import (
    DVPortGroupHandler,
    NetworkHandler,
)
from cloudshell.cp.vcenter.handlers.si_handler import SiHandler
from cloudshell.cp.vcenter.handlers.tag_cache import TagsCache, get_tags_cache
from cloudshell.cp.vcenter.handlers.vcenter_tag_handler import VCenterTagsManager
from cloudshell.cp.vcenter.handlers.vm_handler import VmHandler
from cloudshell.cp.vcenter.handlers.vsphere_api_handler import (
    CategoryAlreadyExists,
    CategoryIdDoesntExists,
    CategoryNameDoesntExists,
    TagAlreadyExists,
    TagApiException,
    TagIdDoesntExists,
    TagNameDoesntExists,
    VSphereAutomationAPI,
)
from cloudshell.cp.vcenter.resource_config import VCenterResourceConfig

logger = logging.getLogger(__name__)

OBJECTS_WITH_TAGS = Union[VmHandler, FolderHandler, NetworkHandler, DVPortGroupHandler]


@define
class VSphereSDKHandler:
    _vsphere_client: VSphereAutomationAPI
    _tags_manager: VCenterTagsManager | None
    _cache: TagsCache = field(init=False)

    # From this version vCenter has vSphere Automation API that allows to work with tags
    VCENTER_VERSION = "6.5.0"

    POSSIBLE_TYPES = [
        "Network",
        "HostNetwork",
        "OpaqueNetwork",
        "DistributedVirtualPortgroup",
        "VirtualMachine",
        "Folder",
    ]

    def __attrs_post_init__(self):
        self._cache = get_tags_cache(
            self._vsphere_client.address, self._vsphere_client.username
        )

    @classmethod
    def from_config(
        cls,
        si: SiHandler,
        resource_config: VCenterResourceConfig,
        reservation_info: ReservationInfo | None,
    ) -> VSphereSDKHandler | None:
        if not resource_config.enable_tags:
            return None

        if version.parse(si.vc_version) >= version.parse(cls.VCENTER_VERSION):
            logger.info("Initializing vSphere API client.")
            vsphere_client = VSphereAutomationAPI(
                address=resource_config.address,
                username=resource_config.user,
                password=resource_config.password,
            )
            vsphere_client.connect()
            if reservation_info is not None:
                tags_manager = VCenterTagsManager(
                    resource_config=resource_config, reservation_info=reservation_info
                )
            else:
                tags_manager = None
            return cls(vsphere_client, tags_manager)
        else:
            logger.warning(f"Tags available only from vCenter {cls.VCENTER_VERSION}")
            return None

    @classmethod
    def connect(cls, address: str, user: str, password: str) -> Self:
        vsphere_client = VSphereAutomationAPI(
            address=address,
            username=user,
            password=password,
        )
        vsphere_client.connect()
        return cls(vsphere_client, None)

    def _get_all_categories(self) -> dict[str:str]:
        """Get all existing categories."""
        logger.debug("List of all existing categories user has access to...")
        result: dict[str, str] = {}  # {name: id}
        categories = self._vsphere_client.get_category_list()
        for category_id in categories:
            if name := self.get_category_name(category_id):
                logger.debug(f"CategoryName: {name}, CategoryID: {category_id}")
                result[name] = category_id
        else:
            logger.info("No Tag Category Found...")
        self._cache.delete_not_existing_categories(result.values())
        return result

    def _get_category_id(self, name: str) -> str:
        if not (category_id := self._cache.get_category_id(name)):
            for category_id in self._vsphere_client.get_category_list():
                if (
                    n := self.get_category_name(category_id)
                ) and n.lower() == name.lower():
                    break
            else:
                raise CategoryNameDoesntExists(name)
        return category_id

    def get_category_name(self, id_: str) -> str | None:
        if not (name := self._cache.get_category_name(id_)):
            try:
                category_info = self._vsphere_client.get_category_info(id_)
            except CategoryIdDoesntExists:
                name = None
            else:
                name = category_info["name"]
                self._cache.add_category(name, id_)
        return name

    def _get_or_create_tag_category(self, name: str) -> str:
        """Create a category or return an existing one.

        Note: User who invokes this needs create category privilege
        """
        try:
            category_id = self._vsphere_client.create_category(name)
        except CategoryAlreadyExists:
            logger.debug(f"Tag Category {name} already exists.")
            category_id = self._get_category_id(name)
        else:
            self._cache.add_category(name, category_id)
        return category_id

    def create_categories(self, custom_categories: list | None = None):
        """Create all Default and Custom Tag Categories."""
        for tag_category in vars(VCenterTagsManager.DefaultTagNames):
            if not tag_category.startswith("__"):
                self._get_or_create_tag_category(
                    name=getattr(VCenterTagsManager.DefaultTagNames, tag_category)
                )

        if custom_categories:
            for custom_category in custom_categories:
                self._get_or_create_tag_category(name=custom_category)

    def _get_all_tags(self, category_id: str) -> dict[str:str]:
        """Get all existing tags for the given category."""
        logger.debug("List of all existing tags user has access to...")
        result: dict[str, str] = {}  # {name: id}
        tags = self._vsphere_client.get_all_category_tags(category_id=category_id)
        for tag_id in tags:
            if name := self.get_tag_name(tag_id):
                logger.debug(f"TagName: {name}, TagID: {tag_id}")
                result[name] = tag_id
        else:
            logger.info("No Tag Found...")
        self._cache.delete_not_existing_tags(result.values())
        return result

    def _get_tag_id(self, name: str, category_id: str) -> str:
        if not (tag_id := self._cache.get_tag_id(category_id, name)):
            for tag_id in self._vsphere_client.get_all_category_tags(category_id):
                if (n := self.get_tag_name(tag_id)) and n.lower() == name.lower():
                    break
            else:
                raise TagNameDoesntExists(name, category_id)
        return tag_id

    def get_tag_name(self, id_: str) -> str | None:
        if not (name := self._cache.get_tag_name(id_)):
            try:
                tag_info = self._vsphere_client.get_tag_info(id_)
            except TagIdDoesntExists:
                name = None  # tag already removed
            else:
                name = tag_info["name"]
                self._cache.add_tag(tag_info["category_id"], name, id_)
        return name

    @retry(
        stop_max_attempt_number=5,
        retry_on_exception=lambda e: isinstance(e, TagNameDoesntExists),
    )  # there is small chance that tag can be deleted while we're finding it by name
    def _get_or_create_tag(self, name: str, category_id: str) -> str:
        """Create a Tag."""
        try:
            tag_id = self._vsphere_client.create_tag(name=name, category_id=category_id)
            if tag_id is None:
                raise TagApiException("Error during tag creation.")
        except TagAlreadyExists as err:
            logger.debug(err)
            tag_id = self._get_tag_id(name, category_id=category_id)
        else:
            self._cache.add_tag(category_id, name, tag_id)
        return tag_id

    def _create_multiple_tag_association(
        self, obj: OBJECTS_WITH_TAGS, tag_ids: list[str]
    ) -> None:
        """Attach tags."""
        object_id, object_type = self._get_object_id_and_type(obj)
        self._vsphere_client.attach_multiple_tags_to_object(
            tag_ids=tag_ids, obj_id=object_id, obj_type=object_type
        )

    def assign_tags(
        self, obj: OBJECTS_WITH_TAGS, tags: dict[str:str] | None = None
    ) -> None:
        """Get/Create tags and assign to provided vCenter object."""
        if not tags:
            tags = self._tags_manager.get_default_tags()
        tags = _normalize_tags(tags)

        tag_ids = []
        for category_name, tag in tags.items():
            category_id = self._get_or_create_tag_category(name=category_name)
            tag_id = self._get_or_create_tag(name=tag, category_id=category_id)
            tag_ids.append(tag_id)

        self._create_multiple_tag_association(obj=obj, tag_ids=tag_ids)

    def get_attached_tags(self, obj: OBJECTS_WITH_TAGS) -> list[str]:
        """Determine all tags attached to vCenter object."""
        object_id, object_type = self._get_object_id_and_type(obj)
        tag_ids = self._vsphere_client.list_attached_tags(
            obj_id=object_id, obj_type=object_type
        )
        return tag_ids

    def delete_unused_tags(self, tags: Collection[str], wait: float = 15) -> list[str]:
        """Remove tags that are not used in any vCenter object."""
        remained_tags = list(tags)
        exit_time = time.time() + wait
        time_remains = True
        while remained_tags and time_remains:
            for tag in remained_tags[:]:
                try:
                    if not self._vsphere_client.list_attached_objects(tag):
                        self._delete_tag(tag)
                        remained_tags.remove(tag)
                except TagIdDoesntExists:
                    remained_tags.remove(tag)
            time_remains = time.time() < exit_time
        return remained_tags

    def _delete_tag(self, tag_id: str) -> None:
        """Delete an existing tag.

        User who invokes this API needs delete privilege on the tag.
        """
        try:
            self._vsphere_client.delete_tag(tag_id)
        except TagIdDoesntExists as err:
            logger.debug(err)
        self._cache.delete_tag(tag_id)

    def _get_object_id_and_type(self, obj: OBJECTS_WITH_TAGS) -> tuple[str, str]:
        object_id = obj._moId
        object_type = obj._wsdl_name
        logger.debug(f"Object type: {object_type}, Object ID: {object_id}")
        return object_id, object_type


def _normalize_tags(tags: dict[str, str]) -> dict[str, str]:
    """Normalize tags.

    vCenter automatically removes whitespaces from tag names.
    """
    return {key: value.strip() for key, value in tags.items()}
