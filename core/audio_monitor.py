# core/audio_monitor.py
"""
Monitoraggio audio in tempo reale con calcolo di uno spettro a bande
(FFT) per alimentare gli equalizzatori grafici:
- "Interno"  -> microfono predefinito di sistema
- "Esterno"  -> ciò che esce dagli altoparlanti, catturato in loopback

Uso la libreria `soundcard` invece di `sounddevice`/PortAudio: il
supporto al loopback WASAPI su Windows varia molto da una versione di
PortAudio all'altra (nella v3 dava l'errore
"WasapiSettings.__init__() got an unexpected keyword argument 'loopback'"
su alcuni ambienti), mentre `soundcard` lo gestisce in modo nativo e
stabile tramite `get_microphone(..., include_loopback=True)`.

Tutto è avvolto in try/except: se manca la libreria, se un dispositivo
non è disponibile o il loopback non è supportato, il monitor lo segnala
restituendo `None` per quella sorgente, senza mai interrompere l'app.
"""

import sys
import time
import warnings

import numpy as np
from PySide6.QtCore import QThread, Signal

# `soundcard` emette un RuntimeWarning ad ogni micro-interruzione del
# buffer di registrazione ("data discontinuity"). È innocuo (la barra
# dell'equalizzatore al massimo salta un frame), ma se stampato ad ogni
# ciclo può letteralmente sommergere la console e rallentare l'app per
# via del solo I/O di stampa. Lo silenziamo qui, una volta per tutte.
warnings.filterwarnings("ignore", message=".*data discontinuity.*")

try:
    import soundcard as sc
    _SOUNDCARD_OK = True
except Exception:
    sc = None
    _SOUNDCARD_OK = False

N_BARS = 30
MIN_FREQ = 60.0
MAX_FREQ = 8000.0
SAMPLE_RATE = 44100
BLOCK_SIZE = 2048  # buffer più ampio: meno probabilità di discontinuità nel flusso audio


def _compute_bars(block) -> list:
    """Calcola N_BARS livelli (0.0-1.0) dallo spettro di un blocco audio."""
    if block is None or block.size == 0:
        return [0.0] * N_BARS
    mono = block.mean(axis=1) if block.ndim > 1 else block
    if mono.size < 8:
        return [0.0] * N_BARS

    windowed = mono * np.hanning(mono.size)
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(mono.size, d=1.0 / SAMPLE_RATE)

    max_freq = min(MAX_FREQ, SAMPLE_RATE / 2)
    edges = np.logspace(np.log10(MIN_FREQ), np.log10(max_freq), N_BARS + 1)

    bars = []
    for i in range(N_BARS):
        mask = (freqs >= edges[i]) & (freqs < edges[i + 1])
        magnitude = float(spectrum[mask].mean()) if np.any(mask) else 0.0
        bars.append(magnitude)

    # Normalizzazione empirica (non un vero dBFS): serve solo a un
    # effetto visivo "da equalizzatore" coerente.
    reference = mono.size * 0.03
    bars = [min(1.0, b / reference) if reference > 0 else 0.0 for b in bars]
    return bars


class AudioMonitor(QThread):
    bars_ready = Signal(object, object)  # mic_bars (list|None), out_bars (list|None)

    def __init__(self, interval_ms: int = 120, parent=None):
        super().__init__(parent)
        self.interval_s = interval_ms / 1000.0
        self._running = True
        self._paused = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        self._running = False

    def run(self):
        if not _SOUNDCARD_OK:
            while self._running:
                self.bars_ready.emit(None, None)
                time.sleep(1.0)
            return

        mic_cm = mic_rec = None
        out_cm = out_rec = None

        try:
            mic_device = sc.default_microphone()
            mic_cm = mic_device.recorder(samplerate=SAMPLE_RATE, channels=1, blocksize=BLOCK_SIZE)
            mic_rec = mic_cm.__enter__()
        except Exception as exc:
            print(f"[AudioMonitor] Microfono non disponibile: {exc}")

        try:
            speaker = sc.default_speaker()
            loopback_device = sc.get_microphone(id=str(speaker.id), include_loopback=True)
            out_cm = loopback_device.recorder(samplerate=SAMPLE_RATE, channels=2, blocksize=BLOCK_SIZE)
            out_rec = out_cm.__enter__()
        except Exception as exc:
            print(f"[AudioMonitor] Loopback audio di sistema non disponibile: {exc}")

        while self._running:
            if not self._paused:
                mic_bars = None
                out_bars = None
                if mic_rec is not None:
                    try:
                        data = mic_rec.record(numframes=BLOCK_SIZE)
                        mic_bars = _compute_bars(data)
                    except Exception:
                        mic_bars = None
                if out_rec is not None:
                    try:
                        data = out_rec.record(numframes=BLOCK_SIZE)
                        out_bars = _compute_bars(data)
                    except Exception:
                        out_bars = None
                self.bars_ready.emit(mic_bars, out_bars)
            time.sleep(self.interval_s)

        for cm in (mic_cm, out_cm):
            if cm is not None:
                try:
                    cm.__exit__(None, None, None)
                except Exception:
                    pass
