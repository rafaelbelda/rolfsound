import RPi.GPIO as GPIO
import time
import threading

LED_PIN = 18
INTERVAL_SECONDS = 1

_stop_event = threading.Event()
_blink_thread = None

def _blink_loop():
    while not _stop_event.is_set():
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(INTERVAL_SECONDS)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(INTERVAL_SECONDS)

def start_blinking():
    global _blink_thread
    
    # Setup pin on first use
    GPIO.setup(LED_PIN, GPIO.OUT)
    
    if _blink_thread and _blink_thread.is_alive():
        return
    
    _stop_event.clear()
    _blink_thread = threading.Thread(target=_blink_loop, daemon=True)
    _blink_thread.start()

def stop_blinking():
    _stop_event.set()
    GPIO.output(LED_PIN, GPIO.LOW)
    if _blink_thread:
        _blink_thread.join()