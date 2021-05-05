class GenericDeployedAppResourceModel(object):
    def __init__(self):
        self.vm_uuid = ""
        self.cloud_provider = ""
        self.fullname = ""
        self.deployment_path = ""
        self.vm_custom_params = None
        self.app_request_model = None
