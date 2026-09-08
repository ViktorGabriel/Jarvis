import time
import numpy as np
import sounddevice as sd
from typing import Callable, Optional
import threading
import logging

logger = logging.getLogger("VoiceIO")

class VoiceIO:
    def __init__(self, sample_rate: int = 16000, on_audio_chunk: Optional[Callable[[bytes], None]] = None):
        self.sample_rate = sample_rate
        self.on_audio_chunk = on_audio_chunk
        self.on_volume_level: Optional[Callable[[float], None]] = None
        self.is_recording = False
        self.is_playing = False
        self._stream: Optional[sd.InputStream] = None
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_playback = threading.Event()

    def set_volume_listener(self, callback: Callable[[float], None]):
        self.on_volume_level = callback

    def _audio_input_callback(self, indata, frames, time_info, status):
        if status:
            logger.warning(f"Status do microfone: {status}")

        # Calcula o nível de volume RMS (0.0 a 100.0) para alimentar a animação do HUD
        rms = np.sqrt(np.mean(indata**2))
        vol = min(100.0, float(rms * 400.0))

        if self.on_volume_level:
            self.on_volume_level(vol)

        # Se houver áudio sendo tocado e o usuário falar alto (Barge-in / Interrupção)
        if self.is_playing and vol > 15.0:
            logger.info("Barge-in detectado! Interrompendo fala do J.A.R.V.I.S.")
            self.stop_speaking()

        if self.on_audio_chunk:
            # Converte float32 para int16 PCM
            pcm16 = (indata * 32767).astype(np.int16).tobytes()
            self.on_audio_chunk(pcm16)

    def start_listening(self):
        if self.is_recording:
            return
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=self._audio_input_callback,
                blocksize=1024
            )
            self._stream.start()
            self.is_recording = True
            logger.info("Captação de voz ativa (microfone ouvindo).")
        except Exception as e:
            logger.error(f"Erro ao inicializar microfone com sounddevice: {e}")

    def stop_listening(self):
        if self._stream and self.is_recording:
            self._stream.stop()
            self._stream.close()
            self.is_recording = False

    def play_pcm_audio(self, pcm_bytes: bytes, sample_rate: int = 24000):
        """Reproduz áudio PCM retornado pelo Gemini Live com capacidade de cancelamento imediato."""
        self.stop_speaking()
        self._stop_playback.clear()
        self.is_playing = True

        def _worker():
            try:
                audio_data = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                sd.play(audio_data, samplerate=sample_rate)
                sd.wait()
            except Exception as e:
                logger.error(f"Erro na reprodução de áudio: {e}")
            finally:
                self.is_playing = False

        self._playback_thread = threading.Thread(target=_worker, daemon=True)
        self._playback_thread.start()

    def stop_speaking(self):
        """Cancela instantaneamente qualquer fala ativa do assistente."""
        if self.is_playing:
            self._stop_playback.set()
            sd.stop()
            self.is_playing = False
