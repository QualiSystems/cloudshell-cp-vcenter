from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection

from attrs import define, field


@define
class TagsCache:
    _category_name_to_id: dict[str:str] = field(factory=dict)
    _category_id_to_name: dict[str:str] = field(factory=dict)
    # {category_id: {tag_name: tag_id}}  noqa: E800
    _tag_name_to_id: dict[str, dict[str:str]] = field(factory=lambda: defaultdict(dict))
    # {tag_id: (tag_name, category_id)}  noqa: E800
    _tag_id_to_name: dict[str, tuple[str, str]] = field(factory=dict)

    def add_category(self, name: str, category_id: str) -> None:
        self._category_name_to_id[name] = category_id
        self._category_id_to_name[category_id] = name

    def get_category_id(self, name: str) -> str | None:
        return self._category_name_to_id.get(name)

    def get_category_name(self, category_id: str) -> str | None:
        return self._category_id_to_name.get(category_id)

    def delete_not_existing_categories(self, ids: Collection[str]) -> None:
        for id_ in self._category_id_to_name.keys() - ids:
            self.delete_category(id_)

    def delete_category(self, id_: str) -> None:
        try:
            name = self._category_id_to_name.pop(id_)
        except KeyError:
            pass
        else:
            del self._category_name_to_id[name]

    def add_tag(self, category_id: str, name: str, tag_id: str) -> None:
        self._tag_name_to_id[category_id][name] = tag_id
        self._tag_id_to_name[tag_id] = (name, category_id)

    def get_tag_id(self, category_id: str, name: str) -> str | None:
        return self._tag_name_to_id[category_id].get(name)

    def get_tag_name(self, tag_id: str) -> str | None:
        name, cid = self._tag_id_to_name.get(tag_id, (None, None))
        return name

    def get_tag_name_and_category_id(self, tag_id: str) -> tuple[str, str] | None:
        return self._tag_id_to_name.get(tag_id)

    def delete_not_existing_tags(self, ids: Collection[str]) -> None:
        for id_ in self._tag_id_to_name.keys() - ids:
            self.delete_tag(id_)

    def delete_tag(self, id_: str) -> None:
        try:
            name, cid = self._tag_id_to_name.pop(id_)
        except KeyError:
            pass
        else:
            del self._tag_name_to_id[cid][name]


tags_caches: dict[tuple[str, str], TagsCache] = {}  # {(address, username): TagsCache}


def get_tags_cache(address: str, user: str) -> TagsCache:
    if not (tags_cache := tags_caches.get((address, user))):
        tags_cache = TagsCache()
        tags_caches[(address, user)] = tags_cache
    return tags_cache
