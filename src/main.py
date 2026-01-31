import time
import logging
from logging.handlers import RotatingFileHandler

import sounddevice as sd

from src.recorder.recorder_script import Recorder
from src import config
from src.utils import get_version

config.load()

DEVICE_NAME = config.get("device_name") or None

# =========================
# Utilidades
# =========================

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = RotatingFileHandler(
        'latest.log',
        maxBytes=5 * 1024 * 1024,
        backupCount=2,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)-8s | %(message)s'))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def find_input_device(name_hint):
    if name_hint is None:
        return None

    if isinstance(name_hint, int):
        devices = sd.query_devices()
        if 0 <= name_hint < len(devices) and devices[name_hint]["max_input_channels"] > 0:
            return name_hint
        raise RuntimeError("Dispositivo inválido")

    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0 and name_hint.lower() in dev["name"].lower():
            return idx

    raise RuntimeError("Dispositivo não encontrado")

# =========================
# Entry point
# =========================

def main():
    logger = setup_logging()
    logger.info(f"=== rolfsound {get_version()} ===")

    time.sleep(3)

    # TODOs:
    # update from git
    # delete old recordings (>90 days) if enabled
    # check size of "recordings" folder and warn if too large
    # finish setup google drive uploader/authentication

    # add logic to detect pendrive and transfer files from "recordings" to pendrive. Then delete local files after transfer.

    try:
        device_index = find_input_device(DEVICE_NAME)
    except Exception as e:
        logger.error(e)
        return

    recorder = Recorder(logger)
    recorder.run(device_index)

if __name__ == "__main__":
    main()
