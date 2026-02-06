import queue
from time import time

import numpy as np
import sounddevice as sd

from src import config

try:
    from src.hardware.enconder_KY_040 import EncoderControl
    ENCODER_AVAILABLE = True
except ImportError:
    ENCODER_AVAILABLE = False


def get_session_uptime() -> float:  # seconds
    if SESSION_STARTED_AT is None:
        return 0.0
    return time() - SESSION_STARTED_AT

# =========================
# Configuração
# =========================
SESSION_STARTED_AT = None
DEBUG_MODE = config.get("general")["debug_mode"]

TRIGGER_DURATION = config.get("recorder")["trigger_duration"]
SAMPLE_RATE = config.get("monitor")["sample_rate"]
BLOCK_SIZE = config.get("monitor")["block_size"]
MONITOR_CHANNEL = config.get("monitor")["channel_index"]
MONITOR_ALL_CHANNELS = config.get("monitor")["monitor_all_channels"]


# =========================
# Utilidades
# =========================

def rms_level(block: np.ndarray) -> float:
    return np.sqrt(np.mean(block * block))

RELATIVE_CHANGE = 0.05  # 5% to display log changes in debug mode false

def changed(prev, curr, rel=RELATIVE_CHANGE, abs_min=1e-3) -> bool:
    if prev is None:
        return True
    if isinstance(curr, bool):
        return prev != curr
        # ignore tiny fluctuations near zero
    if abs(prev) < abs_min and abs(curr) < abs_min:
        return False

    scale = max(abs(prev), abs_min)
    return abs(curr - prev) >= scale * rel

# =========================
# Classe base
# =========================

class Monitor:
    def __init__(self, logger):
        self.logger = logger
        self.audio_queue = queue.SimpleQueue()
        self.monitor_all_channels = MONITOR_ALL_CHANNELS

        self._last_logged = {}

        if self.monitor_all_channels:
            self.channel_index = None
        else:
            self.channel_index = MONITOR_CHANNEL - 1

        if ENCODER_AVAILABLE:
            self.encoder = EncoderControl(logger=logger)
        else:
            logger.warning("Encoder não disponível")
            self.encoder = None

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            self.logger.warning(f"Audio status: {status}")

        if self.monitor_all_channels or self.channel_index is None:
            block = indata.mean(axis=1)
        elif indata.shape[1] > self.channel_index:
            block = indata[:, self.channel_index].copy()
        else:
            block = indata[:, 0].copy()

        self.audio_queue.put(block)

    def handle_block(self, block: np.ndarray):
        """Override in subclasses."""
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

                global SESSION_STARTED_AT
                SESSION_STARTED_AT = time()

                while True:
                    block = self.audio_queue.get()
                    self.handle_block(block)

                    threshold = getattr(self, "threshold", 0.0)

                    recording = getattr(self, 'recording', False)
                    rms = getattr(self, '_last_rms', rms_level(block))
                    trigger_s = getattr(self, "trigger_samples", 0) / SAMPLE_RATE
                    silence_s = getattr(self, "silence_samples", 0) / SAMPLE_RATE

                    msg =  f"[Recording] {recording} | "\
                        f"[RMS] {rms:.4f} | "\
                        f"[Threshold] {threshold:.4f} | "\
                        f"[Trigger] {trigger_s:.2f}s/{TRIGGER_DURATION:.1f}s | "\
                        f"[Silence] {silence_s:.1f}s"\

                    # debug: live console update
                    # prod: log only when values change meaningfully

                    if DEBUG_MODE:
                        print("\r" + msg.ljust(100), end="", flush=True)
                    else:
                        fields = {
                            "recording": recording,
                            "rms": rms,
                            "threshold": threshold,
                            "trigger": trigger_s,
                            "silence": silence_s,
                        }

                        should_log = False
                        for k, v in fields.items():
                            if changed(self._last_logged.get(k), v):
                                should_log = True
                                break
                            
                        if should_log:
                            self._last_logged = fields.copy()
                            self.logger.debug(msg)

        except KeyboardInterrupt:
            print()
            self.logger.info("Encerrando monitor")

        except Exception as e:
            self.logger.error(f"Erro: {e}", exc_info=True)
