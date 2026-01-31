import numpy as np
from scipy import signal as sp_signal
import logging
from collections import deque

logger = logging.getLogger(__name__)


class VoiceDetector:
    """
    Detecta presença de voz humana em blocos de áudio usando DSP clássico.
    Combina:
      - energia (RMS)
      - concentração espectral na banda de voz
      - flatness espectral (rejeita tons puros)
      - variação temporal do pico espectral (apenas para ruído fraco)
    """

    def __init__(
        self,
        sample_rate: int,
        min_voice_freq: float = 400,
        max_voice_freq: float = 2500,
        voice_ratio_threshold: float = 0.50,
        rms_min: float = 0.0095,
        flatness_max: float = 0.23,
        peak_history_size: int = 40,
        peak_var_min: float = 8.0,
    ):
        self.sample_rate = sample_rate
        self.min_voice_freq = min_voice_freq
        self.max_voice_freq = max_voice_freq
        self.voice_ratio_threshold = voice_ratio_threshold

        self.rms_min = rms_min
        self.flatness_max = flatness_max
        self.peak_var_min = peak_var_min

        self.peak_history = deque(maxlen=peak_history_size)

        # =========================
        # Band-pass da voz
        # =========================
        try:
            self.sos = sp_signal.butter(
                4,
                [min_voice_freq, max_voice_freq],
                btype="band",
                fs=sample_rate,
                output="sos"
            )
            self.filter_available = True
        except Exception:
            self.filter_available = False
            logger.warning("Falha ao criar filtro passa-banda de voz")

        # =========================
        # Notches (hum + artefatos comuns)
        # =========================
        self.notches = []
        hum_freqs = [
            (60, 30),
            (120, 30),
            (180, 30),
            (240, 30),
            (297, 40),
        ]

        for freq, Q in hum_freqs:
            try:
                b, a = sp_signal.iirnotch(freq, Q, fs=self.sample_rate)
                self.notches.append((b, a))
            except Exception:
                logger.warning(f"Falha ao criar notch em {freq} Hz")

    # ==========================================================
    # CORE DSP
    # ==========================================================
    def _process_block(self, block: np.ndarray) -> dict:
        processed = block.astype(np.float32, copy=True)

        # 1. Notches
        for b, a in self.notches:
            processed = sp_signal.lfilter(b, a, processed)

        # 2. Band-pass da voz
        if self.filter_available:
            voice_band = sp_signal.sosfilt(self.sos, processed)
        else:
            voice_band = processed

        # 3. RMS
        total_rms = np.sqrt(np.mean(processed ** 2))
        voice_rms = np.sqrt(np.mean(voice_band ** 2))
        voice_ratio = voice_rms / (total_rms + 1e-10)

        # 4. FFT para métricas espectrais
        fft = np.fft.rfft(processed)
        mag = np.abs(fft) + 1e-12

        spectral_flatness = np.exp(np.mean(np.log(mag))) / np.mean(mag)

        return {
            "processed": processed,
            "voice_band": voice_band,
            "total_rms": total_rms,
            "voice_rms": voice_rms,
            "voice_ratio": voice_ratio,
            "spectral_flatness": spectral_flatness,
        }

    # ==========================================================
    # DECISÃO TEMPO REAL
    # ==========================================================
    def has_voice(self, block: np.ndarray) -> bool:
        if not self.filter_available:
            logger.warning("Filtro de voz indisponível, assumindo presença de voz")
            return True

        try:
            info = self._process_block(block)

            # 1. Gate absoluto
            if info["total_rms"] < self.rms_min:
                return False

            # 2. Rejeita ruído tonal / estacionário
            if info["spectral_flatness"] > self.flatness_max:
                return False

            # 3. Pico espectral (apenas para ruído fraco)
            fft = np.fft.rfft(info["processed"])
            freqs = np.fft.rfftfreq(len(info["processed"]), 1 / self.sample_rate)
            peak_freq = freqs[np.argmax(np.abs(fft))]
            self.peak_history.append(peak_freq)

            if info["total_rms"] < (self.rms_min * 2.0):
                if len(self.peak_history) >= 5:
                    if np.std(self.peak_history) < self.peak_var_min:
                        return False

            # 4. Critério auxiliar
            return info["voice_ratio"] >= self.voice_ratio_threshold

        except Exception:
            logger.error(
                "Erro na detecção de voz, assumindo presença de voz",
                exc_info=True
            )
            return True

    # ==========================================================
    # DEBUG / VISUALIZAÇÃO
    # ==========================================================
    def analyze_spectrum(self, block: np.ndarray) -> dict:
        info = self._process_block(block)

        windowed = info["processed"] * np.hanning(len(info["processed"]))
        fft = np.fft.rfft(windowed)
        freqs = np.fft.rfftfreq(len(windowed), 1 / self.sample_rate)
        magnitude = np.abs(fft)

        peak_freq = freqs[np.argmax(magnitude)]
        self.peak_history.append(peak_freq)

        peak_var = (
            np.std(self.peak_history)
            if len(self.peak_history) >= 5
            else 0.0
        )

        rms_ok = info["total_rms"] >= self.rms_min
        flatness_ok = info["spectral_flatness"] <= self.flatness_max
        ratio_ok = info["voice_ratio"] >= self.voice_ratio_threshold

        peak_var_ok = True
        if info["total_rms"] < (self.rms_min * 2.0):
            peak_var_ok = peak_var >= self.peak_var_min

        has_voice = all([
            rms_ok,
            flatness_ok,
            ratio_ok,
            peak_var_ok,
        ])

        return {
            "voice_rms": info["voice_rms"],
            "total_rms": info["total_rms"],
            "voice_ratio": info["voice_ratio"],
            "spectral_flatness": info["spectral_flatness"],
            "peak_freq": peak_freq,
            "peak_var": peak_var,

            "rms_ok": rms_ok,
            "ratio_ok": ratio_ok,
            "flatness_ok": flatness_ok,
            "peak_var_ok": peak_var_ok,

            "has_voice": has_voice,

            "freqs": freqs,
            "magnitude": magnitude,
        }
