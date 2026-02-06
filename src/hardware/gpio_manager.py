# src/hardware/gpio_manager.py
import RPi.GPIO as GPIO

_initialized = False

def init_gpio():
    """Call once at startup - sets up GPIO mode"""
    global _initialized
    if not _initialized:
        # Clean up any leftover state from crashed sessions
        try:
            GPIO.setwarnings(False)
            GPIO.cleanup()
        except:
            pass
        
        # Now set up fresh
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        _initialized = True

def cleanup_gpio():
    """Call on shutdown"""
    GPIO.cleanup()