from pathlib import Path
from src import __version__

def get_root_path() -> Path:
    return Path(__file__).parent

def get_version() -> str:
    return __version__