import RPi.GPIO as GPIO
import time
import threading

LED_PIN = 7
INTERVAL_SECONDS_SHORT = 0.15
INTERVAL_SECONDS_LONG = 0.5

GPIO.setmode(GPIO.BCM)

_stop_event = threading.Event()
_blink_thread = None


def _blink_loop():
    while not _stop_event.is_set():
         GPIO.output(LED_PIN, GPIO.HIGH) # ON
         time.sleep(INTERVAL_SECONDS_LONG)
         GPIO.output(LED_PIN, GPIO.LOW) # OFF
 
         #time.sleep(INTERVAL_SECONDS)
         #time.sleep(INTERVAL_SECONDS_LONG)


def start_blinking():
    global _blink_thread

    GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)

    if _blink_thread and _blink_thread.is_alive():
        return

    _stop_event.clear()
    _blink_thread = threading.Thread(
        target=_blink_loop,
        daemon=True
    )
    _blink_thread.start()


def stop_blinking():
    _stop_event.set()
    GPIO.output(LED_PIN, GPIO.LOW)
