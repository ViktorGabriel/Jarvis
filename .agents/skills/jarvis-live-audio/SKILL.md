---
name: jarvis-live-audio
description: "Guidelines and real-time audio pipeline patterns for the Gemini Multimodal Live API, PCM 16kHz/24kHz streaming, WebSockets, barge-in interruption, and sounddevice integration."
---

# Jarvis Live Audio Skill

Use this skill when configuring, debugging, or enhancing real-time voice and streaming capabilities with Google GenAI Live API.

## 1. Streaming Specifications
- **Input (Microphone)**: Linear PCM 16-bit, 16000 Hz sample rate, single channel (mono), little-endian.
- **Output (Playback)**: Linear PCM 16-bit, 24000 Hz sample rate (default for Gemini Live output speech).
- **Chunk Sizing**: 1024 to 2048 samples per frame to achieve latency < 100ms.

## 2. Barge-in & Interruption Pattern
- Monitor the microphone RMS level continuously during agent playback.
- If RMS volume exceeds threshold (e.g. > 15-20% max input) while `is_playing == True`:
  1. Trigger immediate `sd.stop()` to halt audio output immediately.
  2. Send cancel frame / interrupt flag to Gemini Live session.
  3. Switch state in HUD to `LISTENING`.
  4. Discard queued audio output buffers.
