# hardware/toggle_switch.py

GPIO_PIN = 23

class ManualRecordSwitch:
    """
    Classe para chave DPDT toggle switch 2 posições
    ON = gravação manual ativa
    OFF = gravação manual desativa
    """
    def __init__(self, pin:int = GPIO_PIN, on_change=None, logger=None):
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        self.pin = pin
        self.on_change = on_change
        self.logger = logger

        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            pin,
            GPIO.BOTH,
            callback=self._callback,
            bouncetime=50
        )

    def _callback(self, channel):
        state = not self.GPIO.input(self.pin)  # ON = True
        if self.logger:
            self.logger.debug(f"ManualRecordSwitch estado: {state}")
        self.on_change(state)
