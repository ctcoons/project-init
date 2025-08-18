

class FileReaderProjectData:

    def __init__(self, name: str, owner: str, description: str, groups: list):
        self.name = name
        self. owner = owner
        self.description = description
        self.groups = groups

    def get_name(self) -> str:
        return self.name

    def get_owner(self) -> str:
        return self.owner

    def get_description(self) -> str:
        return self.description

    def get_groups(self) -> list:
        return self.groups

    def set_name(self, new_name: str):
        assert new_name is str
        self.name = new_name

    def set_owner(self, new_owner: str):
        assert new_owner is str
        self.owner = new_owner

    def set_groups(self, groups: list):
        assert groups is list
        self.groups = groups

    def __str__(self):
        return f"ProjectData(name='{self.name}', owner='{self.owner}', groups={self.groups})"


