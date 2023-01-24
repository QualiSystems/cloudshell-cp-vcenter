from unittest.mock import call


def test_find_vm_by_uuid(si, dc):
    vc_si = si._vc_obj

    def find_by_uuid(container, uuid, vmSearch=False, instanceUuid=False):
        if instanceUuid:
            return None  # cannot find by VM UUID
        else:
            return "vm"  # but find by VM BIOS UUID

    vc_si.content.searchIndex.FindByUuid.side_effect = find_by_uuid

    result = si.find_by_uuid(dc, "uuid", vm_search=True)

    assert result == "vm"
    assert vc_si.mock_calls == [
        call.content.searchIndex.FindByUuid(dc, "uuid", True, True),
        call.content.searchIndex.FindByUuid(dc, "uuid", True),
    ]


def test_find_by_uuid(si, dc):
    vc_si = si._vc_obj

    result = si.find_by_uuid(dc, "uuid", vm_search=False)

    assert vc_si.mock_calls == [call.content.searchIndex.FindByUuid(dc, "uuid")]
    assert result == vc_si.content.searchIndex.FindByUuid()
