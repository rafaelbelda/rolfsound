import logging
import threading
import time

import RPi.GPIO as GPIO

CLK_PIN = 12
DT_PIN  = 16
SW_PIN  = 20


class EncoderControl:
    def __init__(self, logger=None, poll_interval=0.01):
        self.logger = logger or logging.getLogger(__name__)

        self.clk_pin = CLK_PIN
        self.dt_pin  = DT_PIN
        self.sw_pin  = SW_PIN

        self.poll_interval = poll_interval

        GPIO.setup(self.clk_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.dt_pin,  GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.sw_pin,  GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.last_clk = GPIO.input(self.clk_pin)
        self.last_sw  = GPIO.input(self.sw_pin)

        self.on_change_callback = None
        self.on_button_callback = None
        self.on_long_press_callback = None

        self._button_down_time = None
        self._stop_event = threading.Event()

        self._thread = threading.Thread(
            target=self._poll_loop,
            daemon=True
        )
        self._thread.start()

        self.logger.info(
            f"Encoder (polling) inicializado CLK={self.clk_pin}, DT={self.dt_pin}, SW={self.sw_pin}"
        )

    # =========================================================

    def _poll_loop(self):
        while not self._stop_event.is_set():
            self._poll_encoder()
            self._poll_button()
            time.sleep(self.poll_interval)

    def _poll_encoder(self):
        clk = GPIO.input(self.clk_pin)

        if clk != self.last_clk and clk == 1:
            dt = GPIO.input(self.dt_pin)
            delta = +1 if dt != clk else -1

            if self.on_change_callback:
                self.on_change_callback(delta)

        self.last_clk = clk

    def _poll_button(self):
        sw = GPIO.input(self.sw_pin)
        pressed = (sw == 0)

        if pressed and self.last_sw == 1:
            self._button_down_time = time.time()

        elif not pressed and self.last_sw == 0:
            if self._button_down_time:
                duration = time.time() - self._button_down_time
                self._button_down_time = None

                if duration > 1.5:
                    if self.on_long_press_callback:
                        self.on_long_press_callback()
                else:
                    if self.on_button_callback:
                        self.on_button_callback()

        self.last_sw = sw

    # =========================================================

    def on_change(self, callback):
        self.on_change_callback = callback
        self.logger.debug("Callback on_change registrado")

    def on_button(self, callback):
        self.on_button_callback = callback
        self.logger.debug("Callback on_button registrado")

    def on_long_press(self, callback):
        self.on_long_press_callback = callback
        self.logger.debug("Callback on_long_press registrado")

    def close(self):
        self._stop_event.set()
