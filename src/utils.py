from pathlib import Path
from src import __version__
import requests

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
        
        request = requests.post(
            f"https://ntfy.sh/{ntfy_topic}",
            data=msg.encode('utf-8'),
            headers=headers,
            timeout=5
        )

        return request.ok

    except Exception as e:
        print(f"EXCEPTION: Failed to send ntfy notification: {e}")
