# * Configuration and path resolution

import os
import pathlib
import platform

# * Data directory

def get_data_dir() -> pathlib.Path:
    ...

def get_db_path() -> pathlib.Path:
    ...
