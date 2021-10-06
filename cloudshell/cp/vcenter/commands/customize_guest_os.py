import json
import pkgutil

from jsonschema import ValidationError, validate

from cloudshell.cp.vcenter.common.vcenter.task_waiter import SynchronousTaskWaiter
from cloudshell.cp.vcenter.common.vcenter.vmomi_service import pyVmomiService
from cloudshell.cp.vcenter.models.custom_spec import (
    LinuxCustomizationSpecParams,
    WindowsCustomizationSpecParams,
)


class CustomizeGuestOSCommand:
    def __init__(
        self, pyvmomi_service: pyVmomiService, task_waiter: SynchronousTaskWaiter
    ):
        self.pyvmomi_service = pyvmomi_service
        self.task_waiter = task_waiter

    def customize_os(
        self,
        si,
        logger,
        session,
        vm_uuid,
        custom_spec_name,
        custom_spec_params,
        override_custom_spec,
    ):
        logger.info("Customize Guest OS command started...")
        vm = self.pyvmomi_service.find_by_uuid(si=si, uuid=vm_uuid)
        custom_spec_params = (
            json.loads(custom_spec_params) if custom_spec_params else {}
        )

        if self.pyvmomi_service.is_windows_os(vm):
            custom_spec_params_class = WindowsCustomizationSpecParams
            json_schema_file_path = "../json_schemas/windows_custom_spec.json"
        else:
            custom_spec_params_class = LinuxCustomizationSpecParams
            json_schema_file_path = "../json_schemas/linux_custom_spec.json"

        json_schema = pkgutil.get_data(__name__, json_schema_file_path)
        logger.info("Validating Customization spec JSON data...")

        try:
            validate(instance=custom_spec_params, schema=json.loads(json_schema))
        except ValidationError as e:
            raise Exception(
                f"Invalid Customization Spec JSON data. Validation error: {e.message}"
            )

        custom_spec_params = custom_spec_params_class.from_dict(custom_spec_params)

        if override_custom_spec:
            logger.info(
                "The override flag is set. Deleting the previous Customization spec if such exists..."
            )
            self.pyvmomi_service.delete_customization_spec(si=si, name=vm.name)
            existing_custom_spec = None
        else:
            existing_custom_spec = self.pyvmomi_service.get_customization_spec(
                si=si, name=vm.name
            )

        if existing_custom_spec is not None:
            logger.info(
                f"Found existing Customization spec: '{existing_custom_spec.info.name}'"
            )
            if custom_spec_name:
                raise Exception(
                    f"Unable to apply customization spec '{custom_spec_name}'. "
                    f"Customization spec for the given VM already exists. "
                    f"Specify the 'Override Customization Spec' flag to override it."
                )
            custom_spec_name = existing_custom_spec.info.name

        logger.info(
            f"Preparing Customization spec pased on '{custom_spec_name}' "
            f"spec and params: {custom_spec_params}"
        )
        self.pyvmomi_service.prepare_customization_spec(
            si=si,
            vm=vm,
            vm_name=vm.name,
            custom_spec_name=custom_spec_name,
            custom_spec_params=custom_spec_params,
        )
