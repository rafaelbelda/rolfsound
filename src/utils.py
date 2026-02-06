from pathlib import Path
import logging
from src import __version__, __device_id__
import requests

logger = logging.getLogger(__name__)

def get_root_path() -> Path:
    return Path(__file__).parent

def get_version() -> str:
    return __version__

def get_device_id() -> str:
    return str(__device_id__)