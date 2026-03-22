"""
Audio player node for Marvin speech project.
Used from a roslibpy client to play audio chunks received from a topic.
"""

import pyaudio
import numpy as np
from threading import Lock
from queue import Queue, Empty
import roslibpy

class AudioPlayer:
    def __init__(self):
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
        with self.stream_lock:
            self.init_audio_stream()

    def play_message(self, msg):
        info = msg['info']
        if info['format'] != self.format:
            print(
                f'Audio format set to: {info["format"]}, '
                f'{info["sample_rate"]}Hz, {info["num_channels"]}ch, '
                f'{info["chunk_size"]} samples/chunk'
            )
            with self.stream_lock:
                self.format = info['format']
                self.sample_rate = info['sample_rate']
                self.channels = info['num_channels']
                self.chunk_size = info['chunk_size']
                if self.stream is not None:
                    self.cleanup_stream()
                self.init_audio_stream()

        # Convert message data to numpy array
        audio_data = np.array(msg['data']['int16_data'], dtype=np.int16)

        # Test for events - not yet wired up
        if msg['event'] != '':
            print(f'Received audio event: {msg["event"]}')

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

    def init_audio_stream(self):
        """Initialize the audio output stream."""
        try:
            device_index = 0
            
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

    def cleanup(self):
        """Clean up all resources."""
        with self.stream_lock:
            self.cleanup_stream()
        if self.audio is not None:
            self.audio.terminate()

def main():
    player = AudioPlayer()

    client = roslibpy.Ros(host='192.168.178.61', port=9090)
    client.run()

    listener = roslibpy.Topic(client, '/audio_stream', 'audio_msg/Audio')
    listener.subscribe(lambda message: player.play_message(message))

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print('Shutting down audio player...')
        player.cleanup()
    finally:
        client.terminate()

if __name__ == "__main__":
    main()
    
