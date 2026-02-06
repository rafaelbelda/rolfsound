import sys
import time
import logging
from logging.handlers import RotatingFileHandler

import RPi.GPIO as GPIO
import sounddevice as sd

from src.hardware import gpio_manager
import src.hardware.led_recording as led_recording
from src.settings import config

config.load()

from src.recorder.rec import Recorder
from src.utils import get_version

DEVICE_NAME = config.get("general")["interface_name"] or None
CHECK_UPDATE = config.get("general")["check_update_on_start"] or False

# =========================
# Utilidades
# =========================

def setup_logging():
    logger = logging.getLogger()
    if not logger.handlers:
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
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter('%(levelname)-8s | %(message)s'))

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
    
def find_input_device(name_hint):
    if name_hint is None:
        # use default input device
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

def main():
    logger = setup_logging()

    # update (later)
    if not CHECK_UPDATE:
        logger.info("O update automático está desabilitado. Habilite em config.json")

    # initialize GPIO once for entire app
    try:
        gpio_manager.init_gpio()
    except Exception as e:
        logger.critical(f"Exception while setting up GPIO: {e}")
        sys.exit(1)

    logger.info(f"=== rolfsound {get_version()} ===")

    #logger.info("Aguardando estabilização do sistema de áudio...")
    #time.sleep(0.5)

    # TODOs:
    # update from git
    # delete old recordings (>90 days) if enabled
    # check size of "recordings" folder and warn if too large
    # finish setup google drive uploader/authentication
    # add logic to detect pendrive and transfer files from "recordings" to pendrive. Then delete local files after transfer.
    # enable local download by exposing a python http server serving the "recordings" folder
    # add proper shutdown handling (SIGTERM, SIGINT) with physical button

    # option 1:
        # long-press enconder to switch "screen modes".
        # screen modes:
            # normal: show status, uptime, recording status
            # config: show current config values, allow changing with encoder (left, right and click to select, edit; click again to save)
            # info: show system info (CPU load, memory, disk space, network status)

    # option 2:
        # long-press encoder to save current "threshold" as default in config file
        # normal push button for "screen modes".

    try:
        device_index = find_input_device(DEVICE_NAME)
    except Exception as e:
        logger.error(f"Erro ao encontrar dispositivo de entrada: {e}")
        sys.exit(1)

    recorder = Recorder(logger)

    try:
        recorder.run(device_index)
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        try:
            led_recording.stop_blinking()
            if led_recording._blink_thread:
                led_recording._blink_thread.join()
        
            gpio_manager.cleanup_gpio()
            
        except Exception:
            logger.exception("Erro ao limpar GPIOs do dispositivo.")

if __name__ == "__main__":
    main()
