import time
import pyaudio
import numpy as np
import torch
import roslibpy
from silero_vad import (load_silero_vad,
                          read_audio,
                          get_speech_timestamps,
                          save_audio,
                          VADIterator,
                          collect_chunks)

def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1/32768
    sound = sound.squeeze()  # depends on the use case
    return sound

class VADCapture():

    def __init__(self, client, device_index=-1, use_onnx=True, topic='audio_stream', threshold=0.9, pause_limit=12):
        self.client = client
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 512
        self.device_index = device_index
        self.topic = topic
        self.threshold = threshold
        self.use_onnx = use_onnx
        self.pause_limit = pause_limit

        self.info = {'sample_rate': self.sample_rate, 'chunk_size': self.chunk_size, 'num_channels': self.channels}
        self.talker = roslibpy.Topic(client, topic, 'audio_msg/Audio')

        self.init_model()

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
        #print(f"Speech probability: {new_confidence:.3f}")
        if new_confidence > self.threshold:
            if not self.is_voice:
                print("Voice detected")
                self.talker.publish(roslibpy.Message({'info': self.info, 'data': {'int16_data': self.lookback.tolist()}, 'event': 'start_utterance'}))
                self.is_voice = True
            self.talker.publish(roslibpy.Message({'info': self.info, 'data': {'int16_data': audio_int16.tolist()}}))
            self.pause_length = 0
        else:
            if self.is_voice:
                self.pause_length += 1
                if self.pause_length > self.pause_limit:
                    print("Voice ended")
                    self.talker.publish(roslibpy.Message({'info': self.info, 'data': {'int16_data': audio_int16.tolist()}, 'event': 'end_utterance'}))
                    self.is_voice = False
            self.lookback = audio_int16

        return (None, pyaudio.paContinue)

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

def main(args=None):
    try:
        capture = VADCapture()
        time.sleep(15)  # Keep the capture running for a while to test
    except KeyboardInterrupt:
        print('Shutting down audio capture...')
    finally:
        capture.cleanup()

if __name__ == '__main__':
    main()
