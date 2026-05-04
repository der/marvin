import asyncio
import time
from collections import deque
from queue import Queue, Empty

import numpy as np
import pyaudio
import torch
from src.messages.base import BaseNode
from src.messages.audio import AudioMessage, AudioInfo, AudioData
from silero_vad import load_silero_vad


def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1/32768
    sound = sound.squeeze()  # depends on the use case
    return sound

class VADCapture:

    def __init__(self, client: BaseNode, device_index=-1, use_onnx=True, topic='audio_stream', threshold=0.9, pause_limit=10, lookback_limit=5):
        self.client = client
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 512
        self.device_index = device_index
        self.topic = topic
        self.threshold = threshold
        self.use_onnx = use_onnx
        self.pause_limit = pause_limit
        self.lookback_limit = lookback_limit
        self.lookback_queue = deque(maxlen=lookback_limit)

        self.info = AudioInfo(sample_rate=self.sample_rate, chunk_size=self.chunk_size, num_channels=self.channels)

        self.init_model()

        # Publish queue (filled by audio_callback, drained by _publish_loop)
        # Needed because PyAudio callbacks cannot be async, so we can't await client.publish directly from the callback.
        self._publish_queue = Queue()

        # Audio stream
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_streaming = False
        self.init_audio_stream()
        self.is_voice = False
        self.pause_length = 0

    def init_model(self):
        self.model = load_silero_vad(onnx=self.use_onnx, opset_version=15)
        print("VAD model loaded successfully")

    def init_audio_stream(self):
        """Initialize the audio input stream."""
        try:
            device_index = self.device_index if self.device_index >= 0 else None

            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=device_index,
                stream_callback=self.audio_callback
            )

            self.stream.start_stream()
            self.is_streaming = True
            print('Audio stream started successfully')

        except Exception as e:
            print(f'Failed to initialize audio stream: {e}')
            self.is_streaming = False

    def audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback function for processing audio chunks."""
        if status:
            print(f'Audio stream status: {status}')

        audio_int16 = np.frombuffer(in_data, np.int16)
        audio_float32 = int2float(audio_int16)
        new_confidence = self.model(torch.from_numpy(audio_float32), 16000).item()
        if new_confidence > self.threshold:
            if not self.is_voice:
                print("Voice detected")
                self._publish_queue.put_nowait(("/events", {"type": "sys", "message": "interrupt"}))
                self._publish_queue.put_nowait(("/events", {"type": "vad", "message": "voice start"}))
                self.lookback_queue.append(audio_int16)
                event = 'start_utterance'
                for data in self.lookback_queue:
                    audio = AudioMessage(
                        info=self.info,
                        data=AudioData(int16_data=data.tolist()),
                        event=event)
                    self._publish_queue.put_nowait((self.topic, audio.model_dump()))
                    event = ''
                self.lookback_queue.clear()
                self.is_voice = True
            else:
                audio = AudioMessage(
                        info=self.info,
                        data=AudioData(int16_data=audio_int16.tolist()))
                self._publish_queue.put_nowait((self.topic, audio.model_dump()))
            self.pause_length = 0
        else:
            if self.is_voice:
                self.pause_length += 1
                if self.pause_length > self.pause_limit:
                    print("Voice ended")
                    self._publish_queue.put_nowait(("/events", {"type": "vad", "message": "voice end"}))
                    audio = AudioMessage(
                        info=self.info,
                        data=AudioData(int16_data=audio_int16.tolist()),
                        event='end_utterance')
                    self._publish_queue.put_nowait((self.topic, audio.model_dump()))
                    self.is_voice = False
            self.lookback_queue.append(audio_int16)

        return (None, pyaudio.paContinue)

    async def _publish_loop(self):
        """Drain the publish queue and await each client.publish call."""
        while True:
            try:
                topic, payload = self._publish_queue.get(timeout=1)  # Wait for an item, timeout to allow graceful shutdown
                # print(f"Publishing to {topic}: {payload if isinstance(payload, str) else 'AudioMessage'}")
                await self.client.publish(topic, payload)
                self._publish_queue.task_done()
            except Empty:
                pass
            await asyncio.sleep(0)  # Yield control to the event loop

    async def run(self):
        """Start the publish queue consumer. Call this from the async event loop."""
        await self._publish_loop()

    def cleanup(self):
        """Clean up resources."""
        if self.stream is not None:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                pass
        
        if self.audio is not None:
            self.audio.terminate()

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
