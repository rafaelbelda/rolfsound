import json
from copy import deepcopy
import logging

from src.utils import get_device_id

logger = logging.getLogger(__name__)

# ---------- defaults ----------
def _get_default_config():

# later: add cloud capability
    #"upload_after_recording": True,
    #"delete_after_upload": False,

    return {
        "general": {
        "interface_name": None, # Device name (USB Interface) or index for audio input
        "device_id": get_device_id(),
        "check_update_on_start": True,
        "debug_mode": False,
        "run_time_minutes": 0
        },
        "ntfy": {
            "enabled": True,
            "on_auto_record_stop": True,
            "on_uptade": True,
            "on_out_of_disk": True
        },
        "monitor": {
            "monitor_all_channels": True,
            "channel_index": 1,
            "sample_rate": 48000,
            "block_size": 1024
        },
        "recorder": {
            "auto_record": True,
            "output_dir": "recordings",
            "stop_seconds": 3.5,
            "min_threshold": 0.001,
            "max_threshold": 0.1,
            "threshold": 0.05,
            "trigger_duration": 0.5,
            "encoder_step": 0.001,
            "files": {
                "delete_old_files": False,
                "days_to_keep": 90,
                "max_file_size_gb": 12
            }
        }
    }

# ---------- internal state ----------

from src.utils import get_root_path

_config: dict | None = None
_config_path = get_root_path() / "config.json"

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
        save()
        
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
            # try to find missing key in defaults
            default_config = _get_default_config()
            default_value = default_config.get(part, default)
            logger.warning(f"Key '{key}' not found in config.json. Returning default value: {default_value}")
            return default_value
        
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