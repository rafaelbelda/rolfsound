from pathlib import Path
import logging
from src import __version__
import requests

logger = logging.getLogger(__name__)

def get_root_path() -> Path:
    return Path(__file__).parent

def get_version() -> str:
    return __version__

def send_ntfy_notification(msg: str, ntfy_topic: str = "rolfsound_25565", tags: list = None):

    try:
        headers = {
            "Priority": "urgent",
            "Title": "rolfsound"
        }
        
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