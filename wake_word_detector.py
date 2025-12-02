import whisper
import pyaudio
import numpy as np
import re
import threading
from difflib import SequenceMatcher

class WakeWordDetector:
    def __init__(self, wake_phrase="hey talk assist", model_size="base"):
        print(f"Loading Whisper model ({model_size}) for wake word detection...")
        self.whisper_model = whisper.load_model(model_size)
        self.wake_phrase = wake_phrase.lower()
        self.wake_words = self._extract_wake_words(wake_phrase)
        
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        
        self.listen_duration = 3.0
        self.silence_threshold = 120
        self.min_volume = 20
        
        self._stop_event = threading.Event()
    
    def _extract_wake_words(self, phrase):
        words = phrase.lower().split()
        return {
            'full_phrase': phrase.lower(),
            'key_words': ['hey', 'talk', 'assist'],
            'variations': [
                phrase.lower(),
                phrase.lower().replace(' ', ''),
                'hey talk assist',
                'hey talkassist',
                'talk assist',
            ]
        }
    
    def _similar(self, a, b):
        return SequenceMatcher(None, a, b).ratio()
    
    def check_audio_level(self, audio_data):
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        volume = np.abs(audio_np).mean()
        return volume
    
    def listen_for_wake_word(self, max_duration=3.0):
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        frames = []
        total_volume = 0
        num_chunks = 0
        speech_detected = False
        max_chunks = int((self.RATE / self.CHUNK) * max_duration)
        min_speech_chunks = int((self.RATE / self.CHUNK) * 0.3)
        
        for i in range(max_chunks):
            if self._stop_event.is_set():
                break
            
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            frames.append(data)
            volume = self.check_audio_level(data)
            total_volume += volume
            num_chunks += 1
            
            if volume > self.silence_threshold:
                speech_detected = True
                print("█", end="", flush=True)
            else:
                print("░", end="", flush=True)
        
        print()
        
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        avg_volume = total_volume / num_chunks if num_chunks > 0 else 0
        
        if (
            avg_volume < self.min_volume or not speech_detected or num_chunks < min_speech_chunks
        ):
            return ""
        
        audio_data = b''.join(frames)
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        audio_np = audio_np / 32768.0
        
        if self._stop_event.is_set():
            return ""
        
        try:
            result = self.whisper_model.transcribe(audio_np, language="en", fp16=False)
            raw_text = (result.get('text', '')).strip().lower()
            normalized= re.sub(r"[^a-z\s]", '', raw_text)
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            return normalized
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
    
    def is_wake_word_detected(self, text):
        if not text:
            return False
        
        text_lower = text.lower().strip()
        normalized= re.sub(r"[^a-z\s]", '', text_lower)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        if self.wake_phrase in text_lower or self.wake_phrase in normalized:
            return True
        
        for variation in self.wake_words['variations']:
            if variation in text_lower or variation in normalized:
                return True
        
       
        key_words = self.wake_words['key_words']
        
        if all(word in text_lower for word in key_words):
            indices = [text_lower.find(word) for word in key_words]
            if all(idx >= 0 for idx in indices):
                if max(indices) - min(indices) < 50:
                    return True
        
        patterns = [
            r'hey\s+talk\s+assist',
            r'hey\s+talkassist',
            r'hey\s+talk\s+assistant',
            r'hey\s+talk\s+assists',
        ]
        
        for pattern in patterns:
            if re.search(pattern, normalized):
                return True
        
        candidates = [self.wake_phrase] + self.wake_words['variations']
        for candidate in candidates:
            similarity = self._similar(normalized, candidate)
            if similarity >= 0.7:
                return True
        return False
    
    def wait_for_wake_word(self, verbose=True):
        if verbose:
            print("\n" + "="*60)
            print(f"Wake Word Detector - Listening for '{self.wake_phrase}'")
            print("="*60)
            print("Say the wake phrase to activate TalkAssist...")
            print("Press Ctrl+C to exit\n")
        
        try:
            while not self._stop_event.is_set():
                if verbose:
                    print("Listening...", end=" ", flush=True)
                
                transcribed_text = self.listen_for_wake_word(max_duration=self.listen_duration)
                
                if transcribed_text:
                    if verbose:
                        print(f"Transcribed: '{transcribed_text}'")
                    
                    if self.is_wake_word_detected(transcribed_text):
                        if verbose:
                            print(f"\n✓ Wake word detected! ('{transcribed_text}')")
                            print("="*60 + "\n")
                        return True
                    elif verbose:
                        print("  (Wake word not detected, continuing to listen...)")
                elif verbose:
                    print("  (No speech detected)")
                
        except KeyboardInterrupt:
            if verbose:
                print("\n\nWake word detection interrupted.")
            return False
        except Exception as e:
            if verbose:
                print(f"\nError in wake word detection: {e}")
            return False
    
    def stop(self):
        self._stop_event.set()


if __name__ == "__main__":
    detector = WakeWordDetector(wake_phrase="hey talk assist", model_size="base")
    detected = detector.wait_for_wake_word()
    
    if detected:
        print("Wake word detected Ready to start main application.")
    else:
        print("Wake word detection stopped.")


