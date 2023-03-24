from __future__ import annotations

import re
from collections.abc import Iterator

COLLECTION_SEPARATOR_PATTERN = re.compile(r"[,;]")


def split_list_of_values(string: str) -> Iterator[str, None, None]:
    # todo use it from standards v2
    return filter(bool, map(str.strip, COLLECTION_SEPARATOR_PATTERN.split(string)))
