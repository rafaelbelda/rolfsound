"""
Controle de Encoder KY-040 (somente INPUT)
- Gira = emite delta (+1 / -1)
- Botão = callback simples
"""

import logging

CLK_PIN = 23  # GPIO17
DT_PIN = 24  # GPIO27
SW_PIN = 25  # GPIO22

def testEncoder():
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        raise ImportError(
            "Este módulo só pode ser executado em um Raspberry Pi com RPi.GPIO instalado."
        )

class EncoderControl:
    """
    Encoder rotacional como dispositivo de entrada puro
    NÃO conhece threshold, step ou limites
    """

    def __init__(self, logger=None):
        import RPi.GPIO as GPIO
        self.GPIO = GPIO

        self.logger = logger or logging.getLogger(__name__)

        GPIO.setwarnings(False)

        self.clk_pin = CLK_PIN
        self.dt_pin = DT_PIN
        self.sw_pin = SW_PIN

        GPIO.setup(self.clk_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.dt_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.sw_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.last_clk_state = GPIO.input(self.clk_pin)

        self.on_change_callback = None
        self.on_button_callback = None
        self.on_long_press_callback = None

        self._button_down_time = None

        try:
            GPIO.add_event_detect(
                self.clk_pin,
                GPIO.BOTH,
                callback=self._encoder_callback,
                bouncetime=2,
            )

            GPIO.add_event_detect(
                self.sw_pin,
                GPIO.BOTH,
                callback=self._button_callback,
                bouncetime=300,
            )

            self.logger.info(
                f"Encoder inicializado CLK={self.clk_pin}, DT={self.dt_pin}, SW={self.sw_pin}"
            )

        except Exception as e:
            self.logger.error(f"Erro ao configurar encoder: {e}")
            raise

    # =========================================================

    def _encoder_callback(self, channel):
        try:
            clk_state = self.GPIO.input(self.clk_pin)
            dt_state = self.GPIO.input(self.dt_pin)

            if clk_state != self.last_clk_state and clk_state == 1:
                delta = +1 if dt_state != clk_state else -1

                if self.on_change_callback:
                    self.on_change_callback(delta)

            self.last_clk_state = clk_state

        except Exception as e:
            self.logger.error(f"Erro no callback do encoder: {e}")

    def _button_callback(self, channel):
        import time
        pressed = not self.GPIO.input(self.sw_pin)

        if pressed:
            self._button_down_time = time.time()
        else:
            if self._button_down_time:
                duration = time.time() - self._button_down_time
                self._button_down_time = None

                if duration > 1.5:
                    if self.on_long_press_callback:
                        self.on_long_press_callback()
                else:
                    if self.on_button_callback:
                        self.on_button_callback()


    # =========================================================

    def on_change(self, callback):
        """callback(delta: int)"""
        self.on_change_callback = callback
        self.logger.debug("Callback on_change registrado")

    def on_button(self, callback):
        """callback()"""
        self.on_button_callback = callback
        self.logger.debug("Callback on_button registrado")

    def on_long_press(self, callback):
        """callback()"""
        self.on_long_press_callback = callback
        self.logger.debug("Callback on_long_press registrado")
