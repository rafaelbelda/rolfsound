# src/recorder.py

import os
from datetime import datetime
import numpy as np
from scipy.io.wavfile import write as wav_write

import src.hardware.led_recording as led_rec

from src.monitor import Monitor, rms_level, SAMPLE_RATE, BLOCK_SIZE, get_session_uptime
from src.settings import config
from src.tools.ntfy import notify

try:
    from src.hardware.toggle_switch import ManualRecordSwitch, GPIO_PIN as MANUAL_SWITCH_PIN
    SWITCH_AVAILABLE = True
except ImportError:
    SWITCH_AVAILABLE = False

# =========================
# Configuração
# =========================
OUTPUT_DIR = config.get("recorder")["output_dir"]

AUTO_RECORD_DEFAULT = config.get("recorder")["auto_record"]
TRIGGER_DURATION = config.get("recorder")["trigger_duration"]
SILENCE_SECONDS = config.get("recorder")["stop_seconds"]

THRESHOLD = config.get("recorder")["threshold"]
MIN_THRESHOLD = config.get("recorder")["min_threshold"]
MAX_THRESHOLD = config.get("recorder")["max_threshold"]
THRESHOLD_STEP = config.get("recorder")["encoder_step"]

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

        # --- recorder state ---
        self.auto_record = AUTO_RECORD_DEFAULT
        self.manual_recording = False
        self.recording = False

        self.last_filename = None
        self.last_duration = 0

        # --- threshold ---
        self.threshold = THRESHOLD

        # Encoder callbacks
        if self.encoder:
            self.encoder.on_change(self._on_threshold_change)
            self.encoder.on_button(self._on_button_press)
            self.encoder.on_long_press(self._on_encoder_long_press)

        # Toggle switch manual
        if SWITCH_AVAILABLE:
            self.manual_switch = ManualRecordSwitch(
                pin=MANUAL_SWITCH_PIN,
                on_change=self._on_manual_switch,
                logger=logger,
            )
        else:
            self.manual_switch = None
            self.logger.warning("Toggle switch do auto recorder manual não disponível")

        self.switch_available = SWITCH_AVAILABLE and self.manual_switch is not None

        # --- buffers ---
        self.recorded_blocks = []
        self.silence_samples = 0
        self.max_silence_samples = int(SILENCE_SECONDS * SAMPLE_RATE)
        self.prebuffer_size = int(TRIGGER_DURATION * SAMPLE_RATE / BLOCK_SIZE)
        self.prebuffer = []
        self.trigger_samples = 0
        self.min_trigger_samples = int(TRIGGER_DURATION * SAMPLE_RATE)

        ensure_output_dir()

    # =========================
    # Encoder callbacks
    # =========================

    def _on_threshold_change(self, delta: int):
        new_threshold = self.threshold + delta * THRESHOLD_STEP
        new_threshold = max(MIN_THRESHOLD, min(MAX_THRESHOLD, new_threshold))

        if new_threshold != self.threshold:
            self.threshold = new_threshold
            self.logger.info(f"Threshold ajustado: {self.threshold:.4f}")

    def _on_button_press(self):
        """Long press ou botão curto do encoder para alternar auto record"""
        self.auto_record = not self.auto_record

        config.set("monitor.auto_record", self.auto_record)
        config.save()
        self.logger.info(f"Auto Record {'ativado' if self.auto_record else 'desativado'}")


    def _on_encoder_long_press(self):
        config.set("recorder.threshold", self.threshold)
        config.set("monitor.auto_record", self.auto_record)
        config.save()

        self.logger.info("Configuração salva como padrão")
    
    # =========================
    # Toggle switch callback
    # =========================

    def _on_manual_switch(self, state: bool):
        if not self.manual_switch:
            return

        self.manual_recording = state
        if state:
            if not self.recording:
                self.logger.info("Gravação manual iniciada")
                self.start_recording()
        else:
            if self.recording:
                self.logger.info("Gravação manual encerrada")
                self.stop_and_save()

                if self.last_filename:
                    notify(
                        f"Gravado: {self.last_filename} ({self.last_duration:.1f}s)",
                        tags=["studio_microphone"],
                        fired_by="on_auto_record_stop"
                    )
    # =========================
    # Audio handling
    # =========================

    def handle_block(self, block: np.ndarray):
        # calc rms level before processing for logging and monitoring purposes
        level = rms_level(block)
        self._last_rms = level
        
        # prioridade: manual record
        if self.manual_recording:
            if self.recording:
                self.recorded_blocks.append(block)
            return

        # auto record normal
        if not self.auto_record and not self.recording:
            return

        if self.recording:
            self.recorded_blocks.append(block)

            if level < self.threshold:
                self.silence_samples += len(block)
                if self.silence_samples >= self.max_silence_samples:
                    self.stop_and_save()
            else:
                self.silence_samples = 0

        else:
            self.prebuffer.append(block)
            if len(self.prebuffer) > self.prebuffer_size:
                self.prebuffer.pop(0)

            if level >= self.threshold:
                self.trigger_samples += len(block)
                if self.trigger_samples >= self.min_trigger_samples:
                    self.start_recording()
            else:
                self.trigger_samples = 0

    # =========================
    # Start/Stop recording
    # =========================

    def start_recording(self):
        if get_session_uptime() < 3:
            self.logger.debug("Ignorando gatilho pois a sessão é muito recente (< 3s)")
            self.prebuffer.clear()
            self.trigger_samples = 0
            return

        self.recording = True
        self.recorded_blocks = list(self.prebuffer)
        self.prebuffer.clear()
        self.silence_samples = 0
        self.trigger_samples = 0
        self.logger.info("Gravação iniciada")
        led_rec.start_blinking()

    def stop_and_save(self):

        self.recording = False
        led_rec.stop_blinking()

        if not self.recorded_blocks:
            self.logger.error("Nenhum dado gravado para salvar.")
            return

        if not self.should_save():
            self.recorded_blocks.clear()
            return

        audio = np.concatenate(self.recorded_blocks)
        pcm = float_to_int16(audio)

        filename = current_filename()
        wav_write(filename, SAMPLE_RATE, pcm)

        self.recorded_blocks.clear()
        self.silence_samples = 0

        duration = len(audio) / SAMPLE_RATE
        self.last_filename = filename
        self.last_duration = duration
        self.logger.info(f"Gravado: {filename} ({duration:.1f}s)")  

    # =========================
    # Check disk space
    # =========================

    def should_save(self) -> bool:
        try:
            total_size = 0
            for filename in os.listdir(OUTPUT_DIR):
                if filename.endswith(".wav"):
                    total_size += os.path.getsize(os.path.join(OUTPUT_DIR, filename))
            if total_size > 12 * 1024 * 1024 * 1024:  # 12 GB
                self.logger.warning("Gravação descartada (espaço insuficiente)")
                self.recording = False
                self.recorded_blocks.clear()
                return False
            return True
        except Exception as e:
            self.logger.error(f"Erro ao verificar espaço: {e}")
            #later: display on oled error
            return False
