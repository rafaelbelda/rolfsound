import requests
import logging

from src.utils import get_device_id
from src.settings import config

logger = logging.getLogger(__name__)

def test_internet_connection(timeout: float = 4.0) -> bool:
    try:
        requests.get("https://www.google.com", timeout=timeout)
        return True
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False
    except Exception as e:
        logger.error(f"EXCEPTION: test_internet_connection: {e}")
        return False

def check_config_for_action(fired_by: str) -> bool:
    ntfy_config = config.get("ntfy")

    if not ntfy_config["enabled"]:
        return False

    match fired_by:
        case "on_auto_record_stop":
            return ntfy_config.get("on_auto_record_stop", False)
        case "on_out_of_disk":
            return ntfy_config.get("on_out_of_disk", False)
        case "on_update":
            return ntfy_config.get("on_update", False)
        case _:
            logger.error(f"ntfy tried to fire by a non existent action: {fired_by}")
            return False

def notify(msg: str, tags: list = None, fired_by: str = None):

    if fired_by:
        enabled = check_config_for_action(fired_by)

    if not enabled:
        logger.debug(f"ntfy is disabled for this config: {fired_by}")
        return False

    ntfy_topic = "rolfsound_"+get_device_id()

    try:
        if not tags:
            tags=["studio_microphone"]
        
        headers = {"Priority": "urgent","Title": "rolfsound"}
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