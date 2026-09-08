import io
import time
import wave
import numpy as np
import sounddevice as sd
from typing import Callable, Optional, List
import threading
import logging

logger = logging.getLogger("VoiceIO")

class VoiceIO:
    def __init__(self, sample_rate: int = 16000, on_audio_chunk: Optional[Callable[[bytes], None]] = None):
        self.sample_rate = sample_rate
        self.on_audio_chunk = on_audio_chunk
        self.on_volume_level: Optional[Callable[[float], None]] = None
        self.on_phrase_recorded: Optional[Callable[[bytes], None]] = None
        self.is_recording = False
        self.is_playing = False
        self._stream: Optional[sd.InputStream] = None
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_playback = threading.Event()

        # Detecção de Atividade Vocal (VAD) e buffer de fala
        self._speech_buffer: List[bytes] = []
        self._is_speaking_active = False
        self._last_speech_time = 0.0
        self._speech_lock = threading.Lock()
        self._speech_monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()

    def set_volume_listener(self, callback: Callable[[float], None]):
        self.on_volume_level = callback

    def set_phrase_listener(self, callback: Callable[[bytes], None]):
        self.on_phrase_recorded = callback

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Codifica bytes PCM 16-bit mono em formato WAV padrão em memória."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm_data)
        return buf.getvalue()

    def _monitor_silence(self):
        """Thread em segundo plano que monitora o fim da frase por silêncio após fala."""
        while not self._stop_monitor.is_set():
            time.sleep(0.15)
            phrase_wav = None
            with self._speech_lock:
                # Se o usuário estava falando e agora há mais de 1.1s de silêncio
                if self._is_speaking_active and (time.time() - self._last_speech_time > 1.1):
                    total_pcm = b"".join(self._speech_buffer)
                    self._speech_buffer.clear()
                    self._is_speaking_active = False

                    # Mínimo de ~0.7 segundos de áudio capturado (16000 * 2 * 0.7 = 22400 bytes)
                    if len(total_pcm) >= 22400:
                        phrase_wav = self._pcm_to_wav(total_pcm)

            if phrase_wav and self.on_phrase_recorded:
                try:
                    self.on_phrase_recorded(phrase_wav)
                except Exception as e:
                    logger.error(f"Erro ao disparar callback de áudio vocal: {e}")

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

        # Converte float32 para int16 PCM
        pcm16 = (indata * 32767).astype(np.int16).tobytes()

        if self.on_audio_chunk:
            self.on_audio_chunk(pcm16)

        # Detecção de Atividade Vocal (VAD)
        if self.on_phrase_recorded:
            with self._speech_lock:
                if vol > 12.0:
                    self._speech_buffer.append(pcm16)
                    self._is_speaking_active = True
                    self._last_speech_time = time.time()
                elif self._is_speaking_active:
                    # Anexa quadros subsequentes enquanto aguarda o limiar de silêncio
                    self._speech_buffer.append(pcm16)

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

            # Inicia thread monitora de VAD
            self._stop_monitor.clear()
            self._speech_monitor_thread = threading.Thread(target=self._monitor_silence, daemon=True)
            self._speech_monitor_thread.start()

            logger.info("Captação de voz ativa (microfone ouvindo).")
        except Exception as e:
            logger.error(f"Erro ao inicializar microfone com sounddevice: {e}")

    def stop_listening(self):
        self._stop_monitor.set()
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
