from supertonic import TTS
from unicodedata import normalize
import re
import pyaudio
import numpy as np
from threading import Lock, Thread
from queue import Full, Queue, Empty
import time

CHUNK_SIZE = 1024
SAMPLE_RATE = 44100
CHANNELS = 1
VOICE_NAME = "F5"

class TextToSpeech:
    def __init__(self, auto_download=True):
        self.tts = TTS(auto_download=auto_download)
        self.voice_style = self.tts.get_voice_style(voice_name=VOICE_NAME)
        self.total_steps = 6
        self.speed = 1.6

    def synthesize(self, text):
        wav, duration =  self.tts.synthesize(text=text, voice_style = self.voice_style, total_steps=self.total_steps, speed=self.speed)
        wav_chunks = []
        for i in range(0, len(wav[0]), CHUNK_SIZE):
            chunk = wav[0][i:i+CHUNK_SIZE]
            audio_int16 = (np.clip(chunk, -1.0, 1.0) * 32767).astype(np.int16)
            wav_chunks.append(audio_int16.tobytes())
        return wav_chunks

    def prepare_text(self, text: str) -> list[str]:
        """Preprocess and chunk text for TTS synthesis."""
        preprocessed = self._preprocess_text(text)
        chunks = self._chunk_text(preprocessed)
        return chunks
    
    def _chunk_text(self, text: str, max_len: int = 300) -> list[str]:
        """
        Split text into chunks by paragraphs and sentences.

        Args:
            text: Input text to chunk
            max_len: Maximum length of each chunk (default: 300)

        Returns:
            List of text chunks
        """

        # Split by paragraph (two or more newlines)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text.strip()) if p.strip()]

        chunks = []

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Split by sentence boundaries (period, question mark, exclamation mark followed by space)
            # But exclude common abbreviations like Mr., Mrs., Dr., etc. and single capital letters like F.
            pattern = r"(?<!Mr\.)(?<!Mrs\.)(?<!Ms\.)(?<!Dr\.)(?<!Prof\.)(?<!Sr\.)(?<!Jr\.)(?<!Ph\.D\.)(?<!etc\.)(?<!e\.g\.)(?<!i\.e\.)(?<!vs\.)(?<!Inc\.)(?<!Ltd\.)(?<!Co\.)(?<!Corp\.)(?<!St\.)(?<!Ave\.)(?<!Blvd\.)(?<!\b[A-Z]\.)(?<=[.!?])\s+"
            sentences = re.split(pattern, paragraph)

            current_chunk = ""

            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 <= max_len:
                    current_chunk += (" " if current_chunk else "") + sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence

            if current_chunk:
                chunks.append(current_chunk.strip())

        return chunks
    
    def _preprocess_text(self, text: str) -> str:
        text = normalize("NFKD", text)

        # Remove emojis (wide Unicode range)
        emoji_pattern = re.compile(
            "[\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f700-\U0001f77f"
            "\U0001f780-\U0001f7ff"
            "\U0001f800-\U0001f8ff"
            "\U0001f900-\U0001f9ff"
            "\U0001fa00-\U0001fa6f"
            "\U0001fa70-\U0001faff"
            "\u2600-\u26ff"
            "\u2700-\u27bf"
            "\U0001f1e6-\U0001f1ff]+",
            flags=re.UNICODE,
        )
        text = emoji_pattern.sub("", text)

        # Replace various dashes and symbols
        replacements = {
            "–": "-",
            "‑": "-",
            "—": "-",
            "_": " ",
            "\u201c": '"',  # left double quote "
            "\u201d": '"',  # right double quote "
            "\u2018": "'",  # left single quote '
            "\u2019": "'",  # right single quote '
            "´": "'",
            "`": "'",
            "[": " ",
            "]": " ",
            "|": " ",
            "/": " ",
            "#": " ",
            "→": " ",
            "←": " ",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)

        # Remove special symbols
        text = re.sub(r"[♥☆♡©\\]", "", text)

        # Replace known expressions
        expr_replacements = {
            "@": " at ",
            "e.g.,": "for example, ",
            "i.e.,": "that is, ",
        }
        for k, v in expr_replacements.items():
            text = text.replace(k, v)

        # Fix spacing around punctuation
        text = re.sub(r" ,", ",", text)
        text = re.sub(r" \.", ".", text)
        text = re.sub(r" !", "!", text)
        text = re.sub(r" \?", "?", text)
        text = re.sub(r" ;", ";", text)
        text = re.sub(r" :", ":", text)
        text = re.sub(r" '", "'", text)

        # Remove duplicate quotes
        while '""' in text:
            text = text.replace('""', '"')
        while "''" in text:
            text = text.replace("''", "'")
        while "``" in text:
            text = text.replace("``", "`")

        # Remove extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        # If text doesn't end with punctuation, quotes, or closing brackets, add a period
        if not re.search(r"[.!?;:,'\"')\]}…。」』】〉》›»]$", text):
            text += "."
        return text

class Player:
    def __init__(self, device_index=-1):
        self.audio = pyaudio.PyAudio()
        self.device_index = device_index
        self.stream = None
        self.is_playing = False
        self.audio_queue = Queue(maxsize=1024)
        self.stream_lock = Lock()
        self.buffer_underruns = 0

    def play_audio(self, audio_data):
        """Add audio data to the playback queue."""
        try:
            self.audio_queue.put_nowait(audio_data)
            if not self.stream or not self.is_playing:
                self.init_audio_stream()
        except Full:
            print("Audio queue is full, dropping audio chunk")
            self.buffer_underruns += 1

    def audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback function for outputting audio chunks."""
        if status:
            print(f'Audio stream status: {status}')
        
        try:
            audio_data = self.audio_queue.get_nowait()
            return (audio_data, pyaudio.paContinue)
        except Empty:
            # No audio data available, output silence
            silence = (b'\x00\x00' * frame_count * CHANNELS)  # 16-bit stereo silence
            return (silence, pyaudio.paContinue)

    def cancel_playback(self):
        """Stop playback and clear the audio queue."""
        with self.stream_lock:
            if self.stream and self.is_playing:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            self.is_playing = False
            # Clear the audio queue
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except Empty:
                    break
            print("Playback cancelled and audio queue cleared")
            
    def init_audio_stream(self):
        """Initialize the audio output stream."""
        try:
            device_index = self.device_index if self.device_index >= 0 else None
            
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True,
                frames_per_buffer=CHUNK_SIZE,
                output_device_index=device_index,
                stream_callback=self.audio_callback
            )
            self.stream.start_stream()
            self.is_playing = True
            print('Audio output stream started successfully')
        except Exception as e:
            print(f'Failed to initialize audio stream: {e}')
            self.is_playing = False

class TTSController:
    def __init__(self, auto_download=True, device_index=-1):
        self.tts = TextToSpeech(auto_download=auto_download)
        self.player = Player(device_index=device_index)
        self.input_queue = Queue()
        self.is_running = False
        self.worker_thread = None
    
    def start(self):
        """Start the TTS processing thread."""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
    
    def stop(self):
        """Stop the TTS processing thread."""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        self.player.cancel_playback()
    
    def queue_text(self, text: str):
        """Add text to the processing queue."""
        self.input_queue.put(text)
    
    def _worker_loop(self):
        """Main worker loop that processes text and plays audio."""
        while self.is_running:
            try:
                text = self.input_queue.get(timeout=0.5)
                text_chunks = self.tts.prepare_text(text)
                for chunk in text_chunks:
                    audio_data = self.tts.synthesize(chunk)
                    for audio_chunk in audio_data:
                        self.player.play_audio(audio_chunk)
            except Empty:
                continue

def main():
    tts_controller = TTSController(auto_download=True, device_index=-1)
    tts_controller.start()
    
    try:
        while True:
            user_input = input("Enter text to synthesize (or 'exit' to quit): ")
            if user_input.lower() == 'exit':
                break
            tts_controller.queue_text(user_input)
    except KeyboardInterrupt:
        pass
    finally:
        tts_controller.stop()

if __name__ == "__main__":
    main()
