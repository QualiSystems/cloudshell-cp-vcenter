from cloudshell.cp.vcenter.common.utilites.savers.linked_clone_artifact_saver import (
    LinkedCloneArtifactHandler,
)


class ArtifactHandler(object):
    # ALLOWED_DEPLOYMENT_PATHS = [
    #     "VCenter Deploy VM From Linked Clone",
    #     "VMware vCenter Cloud Provider 2G." "vCenter VM From Linked Clone 2G",
    # ]

    @staticmethod
    def factory(
        saveDeploymentModel,
        pv_service,
        vcenter_data_model,
        si,
        logger,
        deployer,
        reservation_id,
        resource_model_parser,
        snapshot_saver,
        task_waiter,
        folder_manager,
        port_configurer,
        cancellation_service,
    ):
        # if saveDeploymentModel in ArtifactHandler.ALLOWED_DEPLOYMENT_PATHS:
        return LinkedCloneArtifactHandler(
            pv_service,
            vcenter_data_model,
            si,
            logger,
            deployer,
            reservation_id,
            resource_model_parser,
            snapshot_saver,
            task_waiter,
            folder_manager,
            port_configurer,
            cancellation_service,
        )
        # return UnsupportedArtifactHandler(saveDeploymentModel)


class UnsupportedArtifactHandler(object):
    def __init__(self, saveDeploymentModel):
        self.unsupported_save_type = saveDeploymentModel
