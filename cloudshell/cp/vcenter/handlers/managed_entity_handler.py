import attr
from pyVmomi import vim


@attr.s(auto_attribs=True)
class ManagedEntityHandler:
    entity: vim.ManagedEntity

    @property
    def name(self) -> str:
        return self.entity.name
