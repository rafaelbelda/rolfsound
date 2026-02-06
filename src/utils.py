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

def test_internet_connection(timeout: float = 3.0) -> bool:
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return True
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False
    except Exception as e:
        logger.error(f"EXCEPTION: test_internet_connection: {e}")
        return False

def send_ntfy_notification(msg: str, tags: list = None):

    from src import config

    NTFY_ENABLED = config.get("ntfy")["enabled"]
    ntfy_topic = config.get("ntfy")["topic"]

    if not NTFY_ENABLED:
        logger.debug("ntfy notifications are disabled in config.")
        return False

    if ntfy_topic is None or ntfy_topic.strip() == "":
        logger.warning("ntfy is enabled but topic is null or empty. Using expected 'rolfsound_<device_id>'.")
        ntfy_topic = f"rolfsound_{get_device_id()}"

    try:
        headers = {"Priority": "urgent","Title": "rolfsound"}
        
        if tags:
            headers["Tags"] = ",".join(tags)
        try:
            request = requests.post(
                f"https://ntfy.sh/{ntfy_topic}",
                data=msg.encode('utf-8'),
                headers=headers,
                timeout=5
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            logger.warning("No internet connection. Cannot send ntfy notification.")
            return False

        logger.debug(f"ntfy notification sent, response code: {request.status_code}")
        return request.ok

    except Exception as e:
        logger.error(f"EXCEPTION: Failed to send ntfy notification: {e}")