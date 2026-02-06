# hardware/toggle_switch.py

import threading
import time
import RPi.GPIO as GPIO

GPIO_PIN = 21


class ManualRecordSwitch:
    """
    Classe para chave DPDT toggle switch 2 posições
    ON  = gravação manual ativa
    OFF = gravação manual desativa
    """

    def __init__(self, pin: int = GPIO_PIN, on_change=None, logger=None, poll_interval=0.02):
        self.pin = pin
        self.on_change = on_change
        self.logger = logger
        self.poll_interval = poll_interval

        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Estado inicial
        self._last_state = GPIO.input(self.pin)

        # Thread de polling
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._poll_loop,
            daemon=True
        )
        self._thread.start()

        if self.logger:
            self.logger.info(f"ManualRecordSwitch (polling) inicializado no GPIO {self.pin}")

    def _poll_loop(self):
        while not self._stop_event.is_set():
            current_state = GPIO.input(self.pin)

            if current_state != self._last_state:
                self._last_state = current_state
                state = not current_state  # ON = True (pull-up)

                if self.logger:
                    self.logger.debug(f"ManualRecordSwitch estado: {state}")

                if self.on_change:
                    self.on_change(state)

            time.sleep(self.poll_interval)

    def close(self):
        self._stop_event.set()
