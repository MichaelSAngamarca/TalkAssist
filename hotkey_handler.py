import threading
import keyboard
import pyttsx3
from wake_word_detector import WakeWordDetector

def speak(text, rate=150, volume=0.9):
    """Speak text using text-to-speech."""
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', rate)
        engine.setProperty('volume', volume)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        pass

class HotkeyHandler:
    def __init__(self, hotkey='ctrl+shift+a', wake_phrase="hey talk assist", model_size="base"):
        self.hotkey = hotkey
        self.wake_phrase = wake_phrase
        self.model_size = model_size
        self.wake_detector = None
        self.is_listening = False
        self.is_running = False
        self.callback = None
        self.hotkey_registered = False
    
    def set_callback(self, callback):
        self.callback = callback
    
    def reset_running_state(self):
        self.is_running = False
        self.is_listening = False
    
    def _on_hotkey_pressed(self):
        if self.is_listening or self.is_running:
            print(f"[{self.hotkey.upper()}] Already running. Please wait for current session to complete.")
            return
        
        self.is_running = True
        print(f"\n[{self.hotkey.upper()}] Hotkey pressed! Starting TalkAssist...")
        
        if self.callback:
            callback_thread = threading.Thread(target=self._execute_callback, daemon=True)
            callback_thread.start()
        else:
            self._start_wake_word_detection()
    
    def _execute_callback(self):
        try:
            self.callback()
        except Exception as e:
            self.reset_running_state()
    
    def _start_wake_word_detection(self):
        try:
            self.is_listening = True
            self.wake_detector = WakeWordDetector(wake_phrase=self.wake_phrase, model_size=self.model_size)
            wake_detected = self.wake_detector.wait_for_wake_word(verbose=True)
            
            if wake_detected:
                print("\n" + "="*60)
                print("Wake word detected! Starting TalkAssist...")
                print("="*60 + "\n")
                
                if self.wake_detector:
                    self.wake_detector.stop()
                    self.wake_detector = None
                
                if self.callback:
                    self.callback()
            else:
                print("Wake word detection stopped.")
            
            self.is_listening = False
            self.is_running = False
            
        except Exception as e:
            self.is_listening = False
            self.is_running = False
    
    def start_listening(self):
        if self.hotkey_registered:
            print("Hotkey handler is already listening.")
            return
        
        speak("Press the hotkey to start application")
        
        keyboard.add_hotkey(self.hotkey, self._on_hotkey_pressed)
        self.hotkey_registered = True
        
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        self.is_running = False
        self.is_listening = False
        
        if self.wake_detector:
            self.wake_detector.stop()
            self.wake_detector = None
        
        if self.hotkey_registered:
            keyboard.unhook_all()
            self.hotkey_registered = False


if __name__ == "__main__":
    handler = HotkeyHandler(hotkey='ctrl+shift+a')
    handler.start_listening()

