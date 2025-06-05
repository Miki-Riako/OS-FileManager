class FileData:
    """ Represents a file or directory in the simulated file system """
    def __init__(
        self,
        name: str,
        uid: str,
        owner: str,
        access: str,
        creation_time: str,
        modified_time: str
    ):
        self.name = name
        self.uid = uid
        self.owner = owner
        self.access = access # This is the full access string, e.g., 'drwxrwxrwx' or 'frwxrw-r--'
        self.creation_time = creation_time
        self.modified_time = modified_time