class AppResourceModel:
    def __init__(self, user=None, password=None):
        self.user = user
        self.password = password

    @classmethod
    def from_dict(cls, data):
        return cls(user=data.get("User"), password=data.get("Password"))
