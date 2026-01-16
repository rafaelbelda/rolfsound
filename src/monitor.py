import queue
import logging

import numpy as np
import sounddevice as sd

from src import config

try:
    from src.hardware.enconder_KY_040 import testEncoder
    testEncoder()
    from src.hardware.enconder_KY_040 import EncoderControl
    ENCODER_AVAILABLE = True

except ImportError:
    from src.hardware.windows_encoder_stub import EncoderControl
    ENCODER_AVAILABLE = False


# =========================
# Configuração
# =========================
TRIGGER_DURATION = config.get("recorder")["trigger_duration"]
SAMPLE_RATE = config.get("monitor")["sample_rate"]
BLOCK_SIZE = config.get("monitor")["block_size"]
THRESHOLD = config.get("recorder")["threshold"]
MONITOR_CHANNEL = config.get("monitor")["channel_index"]

# =========================
# Utilidades
# =========================

def rms_level(block: np.ndarray) -> float:
    return np.sqrt(np.mean(block * block))

# =========================
# Classe base
# =========================

class Monitor:
    def __init__(self, logger):
        self.logger = logger
        self.audio_queue = queue.SimpleQueue()
        self.channel_index = MONITOR_CHANNEL - 1

        if ENCODER_AVAILABLE:
            self.encoder = EncoderControl(logger=logger)
            self.encoder.set_threshold(THRESHOLD)

            self.encoder.on_change(
                lambda v: logger.info(f"Threshold ajustado: {v:.4f}")
            )

            self.encoder.on_button(
                lambda: logger.info("Botão pressionado")
            )
        else:
            self.encoder = None

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            self.logger.warning(f"Audio status: {status}")

        if indata.shape[1] > self.channel_index:
            block = indata[:, self.channel_index].copy()
        else:
            block = indata[:, 0].copy()

        self.audio_queue.put(block)

    def handle_block(self, block: np.ndarray):
        """
        Override in subclasses.
        """
        pass

    def run(self, device_index):
        try:
            with sd.InputStream(
                device=device_index,
                channels=2,
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                dtype="float32",
                callback=self.audio_callback,
            ):
                self.logger.info("Monitorando áudio... Pressione Ctrl+C para sair.")

                while True:
                    block = self.audio_queue.get()
                    self.handle_block(block)

                    threshold = self.encoder.get_threshold() if self.encoder else THRESHOLD

                    print(
                        f"\r[Recording] {self.recording} | "
                        f"[RMS] {rms_level(block):.4f} | "
                        f"[Threshold] {threshold:.4f} | "
                        f"[Trigger] {self.trigger_samples / SAMPLE_RATE:.2f}s/{TRIGGER_DURATION:.1f}s | "
                        f"[Silence] {self.silence_samples / SAMPLE_RATE:.1f}s",
                        end="",
                        flush=True,
                    )

        except KeyboardInterrupt:
            print()
            self.logger.info("Encerrando monitor")

        except Exception as e:
            self.logger.error(f"Erro: {e}", exc_info=True)
