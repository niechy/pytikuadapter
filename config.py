from pathlib import Path

import rtoml


class Configs:
    def __init__(self, file_path):
        self.config = rtoml.load(Path(file_path))
