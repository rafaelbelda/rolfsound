import os
from datetime import datetime

import numpy as np
from scipy.io.wavfile import write as wav_write

from src.monitor import Monitor, rms_level, SAMPLE_RATE, BLOCK_SIZE, THRESHOLD
from src import config
from src.recorder.voice_detection import VoiceDetector


# =========================
# Configuração
# =========================

TRIGGER_DURATION = config.get("recorder")["trigger_duration"]
SILENCE_SECONDS = config.get("recorder")["stop_seconds"]
OUTPUT_DIR = config.get("recorder")["output_dir"]

# Detecção de voz
VOICE_DETECTION_ENABLED = config.get("recorder.voice_detection.enabled", default=False)
VOICE_RATIO_THRESHOLD = config.get("recorder.voice_detection.voice_ratio_threshold", default=0.5)
MIN_VOICE_FREQ = config.get("recorder.voice_detection.min_voice_freq", default=300)
MAX_VOICE_FREQ = config.get("recorder.voice_detection.max_voice_freq", default=3400)

# =========================
# Utilidades
# =========================

def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def current_filename():
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(OUTPUT_DIR, f"rec_{ts}.wav")

def float_to_int16(signal: np.ndarray) -> np.ndarray:
    signal = np.clip(signal, -1.0, 1.0)
    return (signal * 32767).astype(np.int16)

# =========================
# Recorder
# =========================

class Recorder(Monitor):
    def __init__(self, logger):
        super().__init__(logger)

        self.recording = False
        self.recorded_blocks = []

        self.silence_samples = 0
        self.max_silence_samples = int(SILENCE_SECONDS * SAMPLE_RATE)

        self.prebuffer_size = int(TRIGGER_DURATION * SAMPLE_RATE / BLOCK_SIZE)
        self.prebuffer = []

        self.trigger_samples = 0
        self.min_trigger_samples = int(TRIGGER_DURATION * SAMPLE_RATE)

        self.voice_detection_enabled = VOICE_DETECTION_ENABLED
        if self.voice_detection_enabled:
            self.voice_detector = VoiceDetector(
                sample_rate=SAMPLE_RATE,
                min_voice_freq=MIN_VOICE_FREQ,
                max_voice_freq=MAX_VOICE_FREQ,
                voice_ratio_threshold=VOICE_RATIO_THRESHOLD
            )
            logger.info(
                f"Detecção de voz ativada "
                f"(banda: {MIN_VOICE_FREQ}-{MAX_VOICE_FREQ}Hz, "
                f"threshold: {VOICE_RATIO_THRESHOLD:.1%})"
            )
        else:
            self.voice_detector = None
            logger.info("Detecção de voz desativada")

        ensure_output_dir()

    def handle_block(self, block: np.ndarray):
        threshold = self.encoder.get_threshold() if self.encoder else THRESHOLD
        level = rms_level(block)

        has_voice = True  # Default: sempre grava
        if self.voice_detection_enabled and self.voice_detector:
            has_voice = self.voice_detector.has_voice(block)

        if self.recording:
            self.recorded_blocks.append(block)

            if level < threshold:
                self.silence_samples += len(block)
                if self.silence_samples >= self.max_silence_samples:
                    self.stop_and_save()
            else:
                self.silence_samples = 0

        else:
            self.prebuffer.append(block)
            if len(self.prebuffer) > self.prebuffer_size:
                self.prebuffer.pop(0)

            if level >= threshold and has_voice:
                self.trigger_samples += len(block)
                if self.trigger_samples >= self.min_trigger_samples:
                    self.start_recording()
            else:
                self.trigger_samples = 0

    def start_recording(self):
        self.recording = True
        self.recorded_blocks = list(self.prebuffer)
        self.prebuffer.clear()
        self.silence_samples = 0
        self.trigger_samples = 0
        self.logger.info("Gravação iniciada")

    def should_save(self) -> bool:
        try:
            total_size = 0
            for filename in os.listdir(OUTPUT_DIR):
                if filename.endswith(".wav"):
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    total_size += os.path.getsize(filepath)

            if total_size > 10 * 1024 * 1024 * 1024:
                self.logger.warning("Gravação descartada (espaço insuficiente)")
                self.recording = False
                self.recorded_blocks.clear()
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao verificar espaço: {e}")
            return True

    def stop_and_save(self):
        if not self.recorded_blocks:
            self.recording = False
            return
        
        if not self.should_save():
            return
        
        audio = np.concatenate(self.recorded_blocks)
        pcm = float_to_int16(audio)

        filename = current_filename()
        wav_write(filename, SAMPLE_RATE, pcm)

        duration = len(audio) / SAMPLE_RATE
        self.logger.info(f"Gravado: {filename} ({duration:.1f}s)")

        self.recording = False
        self.recorded_blocks.clear()
        self.silence_samples = 0