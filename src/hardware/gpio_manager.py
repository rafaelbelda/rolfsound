# src/hardware/gpio_manager.py
import RPi.GPIO as GPIO

_initialized = False


def init_gpio():
    """Call once at startup - sets up GPIO mode"""
    global _initialized
    if _initialized:
        return

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    _initialized = True


def cleanup_gpio():
    """Call on shutdown"""
    try:
        GPIO.cleanup()
    except Exception:
        pass
