import attr
from pyVmomi import vim


@attr.s(auto_attribs=True)
class ManagedEntityHandler:
    _entity: vim.ManagedEntity

    @property
    def name(self) -> str:
        return self._entity.name
