def test_uuid_and_bios_uuid(vm):
    vc_vm = vm._entity
    # check that VM Handler returns correct UUIDs
    assert vm.uuid == vc_vm.config.instanceUuid
    assert vm.bios_uuid == vc_vm.config.uuid
