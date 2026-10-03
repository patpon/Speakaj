"""Microphone capture into an in-memory 16-bit mono WAV."""

from __future__ import annotations

import io
import threading
import time
import wave

import numpy as np


def to_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    """Encode float32 samples in [-1, 1] as a 16-bit PCM mono WAV file."""
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return buf.getvalue()


def is_silent(samples: np.ndarray, threshold: float = 0.01) -> bool:
    """True when the recording's RMS level is below the threshold."""
    if samples.size == 0:
        return True
    return float(np.sqrt(np.mean(np.square(samples)))) < threshold


class Recorder:
    def __init__(self, sample_rate: int = 16000, max_seconds: float = 300.0):
        self.sample_rate = sample_rate
        self.max_seconds = max_seconds
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream = None
        self._started_at = 0.0
        self.level = 0.0  # latest input level for the overlay meter

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def _callback(self, indata, frames, time_info, status):  # noqa: ARG002
        mono = indata[:, 0].copy()
        with self._lock:
            self._chunks.append(mono)
        self.level = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
        if time.monotonic() - self._started_at > self.max_seconds:
            import sounddevice as sd

            raise sd.CallbackStop

    def start(self) -> None:
        import sounddevice as sd

        if self._stream is not None:
            return
        with self._lock:
            self._chunks = []
        self._started_at = time.monotonic()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> tuple[np.ndarray, float]:
        """Stop recording; return (samples, duration_seconds)."""
        stream, self._stream = self._stream, None
        if stream is not None:
            stream.stop()
            stream.close()
        with self._lock:
            samples = np.concatenate(self._chunks) if self._chunks else np.zeros(0, "float32")
            self._chunks = []
        self.level = 0.0
        return samples, samples.size / self.sample_rate

