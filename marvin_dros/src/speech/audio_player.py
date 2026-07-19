"""
Audio player node for Marvin speech project.
"""

import pyaudio
import numpy as np
from threading import Lock
from queue import Queue, Empty
from messages.audio import AudioMessage
from messages.robot import EventMessage
from dros import Node, Bus

class AudioPlayer(Node):
    def __init__(self,bus:Bus, topic:str='/speech_stream', device_name:str='Jabra'):
        super().__init__(bus)
        self.device_name = device_name
        self.channels = 1
        self.sample_rate = 16000
        self.chunk_size = 512
        self.format: str = '16kmono'
        self.buffer_underruns = 0
        self.audio_queue = Queue(maxsize=256)
        self.stream_lock = Lock()
        self.stream = None
        self.is_playing = False
        self.audio = pyaudio.PyAudio()
        self.topic = topic

    def startup(self):
        """Subscribe to the audio playback topic."""
        print(f"AudioPlayer subscribing to topic: {self.topic}")
        self.subscribe_event(self.topic, self.play_message)
        self.subscribe_event("/events", self.event_handler)
        with self.stream_lock:
            self.init_audio_stream()

    def play_message(self, incoming_msg: dict):
        msg = AudioMessage.model_validate(incoming_msg)
        if msg.info.format != self.format:
            print(
                f'Audio format set to: {msg.info.format}, '
                f'{msg.info.sample_rate}Hz, {msg.info.num_channels}ch, '
                f'{msg.info.chunk_size} samples/chunk'
            )
            with self.stream_lock:
                self.format = msg.info.format
                self.sample_rate = msg.info.sample_rate
                self.channels = msg.info.num_channels
                self.chunk_size = msg.info.chunk_size
                if self.stream is not None:
                    self.cleanup_stream()
                self.init_audio_stream()

        # Convert message data to numpy array
        audio_data = np.array(msg.data.int16_data, dtype=np.int16)

        # Try to add to queue
        try:
            self.audio_queue.put_nowait(audio_data.tobytes())
        except Exception as e:
            # Queue is full, drop the oldest chunk
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.put_nowait(audio_data.tobytes())
                self.buffer_underruns += 1
            except Empty:
                pass
    
    def event_handler(self, message):
        try:
            event = EventMessage.model_validate(message)
            if event.message == 'stop':
                self.stop()
        except Exception as e:
            print("Error processing event message:", e)

    def stop(self):
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()

    def _find_device(self) -> int:
        """Find the audio output device index by name."""
        if self.device_name == 'default':
            return 0
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            if self.device_name in device_info.get('name', '') and device_info.get('maxOutputChannels', 0) > 0:
                print(f'Found audio output device: {device_info["name"]} (index {i})')
                return i
        return 0

    def init_audio_stream(self):
        """Initialize the audio output stream."""
        try:
            device_index = self._find_device()
            
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size,
                output_device_index=device_index,
                stream_callback=self.audio_callback
            )
            
            self.stream.start_stream()
            self.is_playing = True
            
            print('Audio output stream started successfully')
            
        except Exception as e:
            print(f'Failed to initialize audio stream: {e}')
            self.is_playing = False

    def audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback function for playing audio chunks."""
        if status:
            print(f'Audio stream status: {status}')
        
        try:
            # Get audio data from queue
            audio_data = self.audio_queue.get_nowait()
            return (audio_data, pyaudio.paContinue)
        except Empty:
            # No audio data available, return silence
            silence = b'\x00' * (frame_count * self.channels * 2)  # 2 bytes per sample for int16
            return (silence, pyaudio.paContinue)

    def cleanup_stream(self):
        """Clean up the audio stream. Caller must hold stream_lock."""
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            self.is_playing = False

    def shutdown(self):
        """Shutdown the audio player and clean up resources."""
        with self.stream_lock:
            self.cleanup_stream()
        if self.audio is not None:
            self.audio.terminate()
