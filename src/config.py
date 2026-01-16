import json
import os
from copy import deepcopy

# ---------- defaults ----------
def _get_default_config():

    return {
        "device_name": None, # Device name (USB Interface) or index for audio input
        "monitor": {
            "channel_index": 1,
            "sample_rate": 44100,
            "block_size": 1024,
        },
        "google_drive": {
            "credentials_file": "credentials.json",
            "token_file": "token.json",
            "folder_id": "",
        },
        "recorder": {
            "output_dir": "recordings",
            "stop_seconds": 5,
            "min_threshold": 0.001,
            "max_threshold": 0.1,   
            "threshold": 0.015,
            "trigger_duration": 0.3,
            "enconder_step": 0.005, # KY-040 encoder step
            "files":{
                "delete_old_files": False,
                "days_to_keep": 90,
                "max_file_size_gb": 10,
                "upload_after_record": True,
                "delete_after_upload": False,
            },
        }
    }

# ---------- internal state ----------

from src.utils import get_root_path

_config: dict | None = None
_config_path = get_root_path().parent / "config.json"

# ---------- helpers ----------

def _deep_merge(defaults: dict, override: dict) -> dict:
    result = deepcopy(defaults)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result

# ---------- API ----------

def load() -> None:
    global _config
    
    # Get fresh defaults based on current env vars
    default_config = _get_default_config()
    
    if _config_path.exists():
        with _config_path.open("r", encoding="utf-8") as f:
            file_config = json.load(f)
        _config = _deep_merge(default_config, file_config)
    else:
        _config = deepcopy(default_config)
        # Don't auto-save in Docker - env vars are the source of truth

def reload() -> None:
    load()

def save() -> None:
    if _config is None:
        return
    with _config_path.open("w", encoding="utf-8") as f:
        json.dump(_config, f, indent=4)

def to_dict() -> dict:
    if _config is None:
        load()
    return deepcopy(_config)

def get(key: str | None = None, default=None):
    if _config is None:
        load()

    if key is None:
        return _config

    parts = key.split(".")
    value = _config

    for part in parts:
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]

    return value

def set(key: str, value) -> None:
    if _config is None:
        load()

    parts = key.split(".")
    target = _config

    for part in parts[:-1]:
        if part not in target or not isinstance(target[part], dict):
            target[part] = {}
        target = target[part]

    target[parts[-1]] = value
    save()