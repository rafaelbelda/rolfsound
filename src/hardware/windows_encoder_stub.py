class EncoderControl:
    def __init__(self, *_, **__):
        self._threshold = 0.02

    def set_threshold(self, value):
        self._threshold = value

    def get_threshold(self):
        return self._threshold

    def on_change(self, *_):
        pass

    def on_button(self, *_):
        pass
