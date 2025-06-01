import os

class API:
    def __init__(self):
        ...

    def get_executable_path(self, executable_name):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # if os.name == 'nt':  # Windows
        #     executable_name += ".exe"
        return os.path.join(os.path.join(root_dir, "bin"), executable_name)