import asyncio
import time
from collections import deque
from queue import Queue, Empty

import numpy as np
import pyaudio
import torch
from messages.audio import AudioMessage, AudioInfo, AudioData
from silero_vad import load_silero_vad
from dros import Node, Bus

def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1/32768
    sound = sound.squeeze()  # depends on the use case
    return sound

class VADCapture(Node):

    def __init__(self, bus: Bus, device_name="Jabbra", use_onnx=True, topic='/audio_stream', threshold=0.9, pause_limit=10, lookback_limit=5):
        super().__init__(bus)
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 512
        self.device_name = device_name
        self.topic = topic
        self.threshold = threshold
        self.use_onnx = use_onnx
        self.pause_limit = pause_limit
        self.lookback_limit = lookback_limit
        self.lookback_queue = deque(maxlen=lookback_limit)
        self.init_model()

        self.info = AudioInfo(sample_rate=self.sample_rate, chunk_size=self.chunk_size, num_channels=self.channels)

        # Audio stream
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_streaming = False
        self.is_voice = False
        self.pause_length = 0

    def init_model(self):
        self.model = load_silero_vad(onnx=self.use_onnx, opset_version=15)
        print("VAD model loaded successfully")

    def _find_device(self) -> int:
        """Find the audio input device index by name."""
        if self.device_name == 'default':
            return 0
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            if self.device_name in device_info.get('name', '') and device_info.get('maxInputChannels', 0) > 0:
                print(f'Found audio input device: {device_info["name"]} (index {i})')
                return i
        return 0

    def startup(self):
        """Initialize the audio input stream."""
        try:
            device_index = self._find_device() if self.device_name != 'default' else None

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
        if status and status != 2:  # Ignore overflow (status code 2)
            print(f'Audio stream status: {status}')

        audio_int16 = np.frombuffer(in_data, np.int16)
        audio_float32 = int2float(audio_int16)
        new_confidence = self.model(torch.from_numpy(audio_float32), 16000).item()
        if new_confidence > self.threshold:
            if not self.is_voice:
                print("Voice detected")
                self.publish("/events", {"type": "sys", "message": "interrupt"})
                self.publish("/events", {"type": "vad", "message": "voice start"})
                self.lookback_queue.append(audio_int16)
                event = 'start_utterance'
                for data in self.lookback_queue:
                    audio = AudioMessage(
                        info=self.info,
                        data=AudioData(int16_data=data.tolist()),
                        event=event)
                    self.publish(self.topic, audio.model_dump())
                    event = ''
                self.lookback_queue.clear()
                self.is_voice = True
            else:
                audio = AudioMessage(
                        info=self.info,
                        data=AudioData(int16_data=audio_int16.tolist()))
                self.publish(self.topic, audio.model_dump())
            self.pause_length = 0
        else:
            if self.is_voice:
                self.pause_length += 1
                if self.pause_length > self.pause_limit:
                    print("Voice ended")
                    self.publish("/events", {"type": "vad", "message": "voice end"})
                    audio = AudioMessage(
                        info=self.info,
                        data=AudioData(int16_data=audio_int16.tolist()),
                        event='end_utterance')
                    self.publish(self.topic, audio.model_dump())
                    self.is_voice = False
            self.lookback_queue.append(audio_int16)

        return (None, pyaudio.paContinue)

    def shutdown(self):
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
        self.shutdown()
