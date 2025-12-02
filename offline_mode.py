"""
Offline mode
This file contains code to enable offline functionality for the chatbot.
It includes modules for speech recognition, text-to-speech, and local processing.
"""
import os
from pydoc import text
import whisper
import pyttsx3
import pyaudio
import numpy as np
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import json
import threading
import time
from time_parser import TimeParser
import re
from math_parser import MathParser

reminders_lock = threading.Lock()
class OfflineMode:
    def __init__(self):
        print ("loading the whisper model...")
        self.whisper_model = whisper.load_model("small")  # there are base, small, medium, large models

        self.tts_rate = 150
        self.tts_volume = 0.9

        self.math_parser = MathParser()
        self.time_parser = TimeParser()
        # initializing the scheduler here
        job_defaults = {"coalesce": True, "max_instances": 3}
        self.scheduler = BackgroundScheduler(job_defaults=job_defaults)
        self.scheduler.start()
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        
        self.reminders_file = "reminders.json"
        
        # control for cooperative shutdown
        self._stop_event = threading.Event()
        
        # TTS engine and lock for thread-safe access
        self._tts_engine = None
        self._tts_lock = threading.Lock()
        self._tts_thread = None
        
        # Load existing reminders into scheduler
        self._load_existing_reminders()
        self.is_running = False

    def speak(self, text):
        # This function is to convert text to speech
        print(f"TalkAssist: {text}")
        # Try to use GUI TTS first (non-blocking)
        gui_speak_called = False
        try:
            import sys
            main_module = sys.modules.get('main')
            if main_module:
                if hasattr(main_module, 'gui_instance'):
                    gui = getattr(main_module, 'gui_instance')
                    if gui:
                        try:
                            gui.add_bot_message(text)
                        except:
                            pass
                        
                        """try:
                            # Use GUI TTS to avoid duplicate audio (non-blocking)
                            gui.speak(text, self.tts_rate, self.tts_volume)
                            gui_speak_called = True
                        except:
                            pass
                        
                        if gui_speak_called:
                            return"""
        except:
           pass
        
        # Wait for previous TTS thread to finish before starting a new one
        if self._tts_thread and self._tts_thread.is_alive():
            self._tts_thread.join(timeout=15)  # Wait up to 15 seconds (TTS can take time)
        time.sleep(0.3)
        
        def _speak_fallback():
            # Use lock inside the thread to ensure only one TTS operation at a time
            with self._tts_lock:
                engine = None
                try:
                    # Using 'sapi5' driver explicitly on Windows to avoid conflicts
                    try:
                        engine = pyttsx3.init(driverName='sapi5')
                    except:
                        # Fallback to default if sapi5 fails
                        engine = pyttsx3.init()
                    
                    engine.setProperty('rate', self.tts_rate)
                    engine.setProperty('volume', self.tts_volume)
                    engine.say(text)
                    engine.runAndWait()
                    engine.stop()
                except:
                    pass
                finally:
                    # Clean up engine completely
                    if engine is not None:
                        try:
                            engine.stop()
                            time.sleep(0.1)
                            del engine
                        except:
                            pass
        self._tts_thread = threading.Thread(target=_speak_fallback, daemon=True)
        self._tts_thread.start()


    def check_audio_level(self, audio_data):
        #checking the volume level of audio data
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        volume = np.abs(audio_np).mean()
        return volume
    
    def fix_transcription_errors(self, text):
        """Fix common Whisper transcription errors"""
        corrections = {
            # Common number/word confusions
            r'\bat10d\b': 'attend',
            r'\bat tend\b': 'attend',
            r'\batt end\b': 'attend',
            r'\ba10d\b': 'attend',
            r'\b2day\b': 'today',
            r'\bto morrow\b': 'tomorrow',
            r'\b2 morrow\b': 'tomorrow',
            r'\b2morrow\b': 'tomorrow',
            r'\btomorow\b': 'tomorrow',
            r'\btommorow\b': 'tomorrow',
            r'\btommorrow\b': 'tomorrow',
            r'\bmee ting\b': 'meeting',
            r'\bmeating\b': 'meeting',
            r'\b(\d+)\s*p\s*m\b': r'\1 PM',
            r'\b(\d+)\s*a\s*m\b': r'\1 AM',
            r'\b(\d+)\s*p\.?\s?m\.?\b': r'\1 PM',
            r'\b(\d+)\s*a\.?\s?m\.?\b': r'\1 AM',
            r'\b(\d{1,2})\.(\d{2})\b': r'\1:\2',
        }
        for pattern, replacement in corrections.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        text = re.sub(r'\b(a\.?m\.?|p\.?m\.?)\b\.', r'\1', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def listen(self, max_duration=7, silence_duration=2.0):
         # is able to record audio with automatic silence detection. Will stp recording after silence_durantion seconds of silence
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
        silence_chunks = 0
        max_silence_chunks = int((self.RATE / self.CHUNK) * silence_duration)
        speech_detected = False
        min_speech_chunks = int((self.RATE / self.CHUNK) * 0.5)

        for i in range(0, int(self.RATE / self.CHUNK * max_duration)):
            # Check if we should stop (for mode switching)
            if self._stop_event.is_set():
                print("\n(stopped - mode switch requested)")
                break
            
                
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            frames.append(data)
            # Checking the volume level
            volume = self.check_audio_level(data)
            total_volume += volume
            num_chunks += 1
             # this will show when sound is detected
            if volume > 200:  # speech detected
                print("█", end="", flush=True)
                silence_chunks = 0
                speech_detected = True
            else:
                print("░", end="", flush=True)
                if speech_detected:
                    silence_chunks += 1
            if speech_detected and silence_chunks >= max_silence_chunks:
                if num_chunks >= min_speech_chunks:
                    print("(stopped - silence detected)")
                    break

        print()

        stream.stop_stream()
        stream.close()
        audio.terminate()

        avg_volume = total_volume / num_chunks if num_chunks > 0 else 0
        print(f"Average audio level: {avg_volume:.0f}")
        # Checking if the audio was too low to process
        # if no speech was detected
        # saved audio to a temp file and transcribe it
        if avg_volume < 30:
            return ""
        
        # Convert audio frames to numpy array and normalize for Whisper
        # Whisper expects float32 audio in range [-1, 1]
        audio_data = b''.join(frames)
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        # Normalize to [-1, 1] range
        audio_np = audio_np / 32768.0

        # Check if we should stop before transcription
        if self._stop_event.is_set():
            return ""
        
        # transcribing the audio using whisper
        # Pass numpy array directly to avoid ffmpeg dependency
        # Whisper expects 16kHz mono audio, which matches our recording settings
        print("Transcribing the audio...")
        result = self.whisper_model.transcribe(audio_np, language="en", fp16=False)
        text = result['text'].strip()

        text = self.fix_transcription_errors(text)
        if text:
            print(f"✓ You said: {text}")
            # Update GUI if available
            try:
                import sys
                main_module = sys.modules.get('main')
                if main_module and hasattr(main_module, 'gui_instance'):
                    gui = getattr(main_module, 'gui_instance')
                    if gui:
                        gui.add_user_message(text)
            except:
                pass
        else:
            self.speak("I didn't catch that. Please try again.")

        return text
    
    # function to process the voice commands
    def process_command(self, text):
        text_lower = text.lower()
        # for exit commands
        exit_patterns = [
            r'\bgoodbye\b', r'\bexit\b', r'\bquit\b', r'\bstop talking\b',
            r'\bbye\b', r'\bsee you\b', r'\bend conversation\b', r'\bterminate\b'
        ]
        if any(re.search(pattern, text_lower) for pattern in exit_patterns):
            self.speak("Goodbye! Have a great day!")
            return False
        
        # Math or calculation commands
        if self.math_parser.is_math_expression(text_lower):
            time_date_keywords = ["time", "date", "day", "today", "tomorrow", "when"]
            is_time_question = any(keyword in text_lower for keyword in time_date_keywords)
            if not is_time_question:
                try:
                    result = self.math_parser.parse_and_calculate(text)
                    self.speak(f"The answer is {result}")
                except ValueError as e:
                    print(f"Math error: {e}")
                    self.speak("Sorry, I couldn't calculate that.")
                return True
            
        # for time queries
        if any (word in text_lower for word in ["time", "what's the time", "current time", "tell me the time", "time now", "what time is it", "can you tell me the time"]):
            current_time = datetime.now().strftime("%I:%M %p")
            self.speak(f"The current time is {current_time}")
            return True
        # for date queries
        if any (word in text_lower for word in ["date", "what's the date", "current date", "what day is today", "tell me the date", "what is today", "what day is it", "can you tell me the date"]):
            current_date = datetime.now().strftime(" %A, %B %d, %Y")
            self.speak(f"Today is {current_date}")
            return True
        
         #getting the list of reminders
        if any (word in text_lower for word in ["list reminders", "show reminders", "what are my reminders", "my reminders", "list reminder"]):
            self.list_reminders()
            return True
        
        # for setting reminders
        if (re.search(r'\bremind\s+me\b', text_lower) or "set a reminder" in text_lower or "reminder to" in text_lower or "need to" in text_lower or "have to" in text_lower):
            self.set_reminder(text)
            return True
        
       
        # deleting individual reminder by number :added oct 28
        if any(word in text_lower for word in ["delete reminder", "remove reminder", "cancel reminder"]):
            self.delete_reminder_by_number(text)
            return True
        
        # deleting reminder by keyword or content :added oct 28
        if any(word in text_lower for word in ["delete the", "remove the", "cancel the"]):
            self.delete_reminder_by_content(text)
            return True
        
        # for clearing all reminders
        if any(word in text_lower for word in ["clear all reminders","delete all reminders", "remove all reminders", "cancel all reminders"]):
            self.clear_all_reminders()
            return True
        
        time_keywords = ["tonight", "tomorrow", "today", "monday", "tuesday", "wednesday", 
                     "thursday", "friday", "saturday", "sunday", "morning", "afternoon", 
                     "evening", "night", "next week", "pm", "am"]
    
        has_time_reference = any(keyword in text_lower for keyword in time_keywords)
        has_time_format = bool(re.search(r'\bat\s+\d{1,2}', text_lower)) or bool(re.search(r'\bin\s+\d+', text_lower))
        if has_time_reference or has_time_format:
            question_words = ["what", "when", "where", "how", "why", "who", "is", "are", "do", "does", "can", "will", "should"]
            is_question = any(text_lower.startswith(word) for word in question_words)
            if not is_question:
                self.speak("Got it! I'll set that reminder for you.")
                self.set_reminder(text)
                return True
       
        #what to say if the command is not recognized
        self.speak("I'm sorry, I can only tell the time, date, set reminders, and list reminders in offline mode.")
        return True
    
    def _load_existing_reminders(self):
        """Load existing reminders and schedule only future active ones.
        Any active reminders whose time is already in the past are marked inactive.
        """
        if os.path.exists(self.reminders_file):
            try:
                with reminders_lock:
                    with open(self.reminders_file, 'r', encoding='utf-8') as f:
                        reminders = json.load(f)
                
                now = datetime.now()
                changed = False
                for reminder in reminders:
                    if reminder.get("active", True):
                        try:
                            reminder_time = datetime.fromisoformat(reminder['time'])
                        except Exception as e:
                            print(f"Skipping reminder {reminder.get('id')}: bad time value {reminder.get('time')}, {e}")
                            continue

                        if reminder_time > now:
                            job_id = f"reminder_{reminder['id']}"
                            try:
                                self.scheduler.add_job(
                                    self.trigger_reminder,
                                    'date',
                                    run_date=reminder_time,
                                    args=[reminder['id'], reminder['text']],
                                    id=job_id,
                                    replace_existing=True,
                                )
                            except Exception as e:
                                print(f"Error scheduling reminder {reminder.get('id')}: {e}")
                        else:
                            reminder["active"] = False
                            changed = True

                if changed:
                    try:
                        with reminders_lock:
                            with open(self.reminders_file, 'w', encoding='utf-8') as f:
                                json.dump(reminders, f, indent=4)
                    except Exception as e:
                        print(f"Error  updating overdue reminders: {e}")
            except Exception as e:
                print(f"Error loading reminders: {e}")

    
    def _extract_task_from_text(self, text):
        """Extract the task description from text, removing time information."""
        time_patterns = [
            r'in\s+\d+\s+(minute|minutes|min|mins|hour|hours|hr|hrs|day|days)\b',
            r'\btomorrow\s+at\s+',
            r'\btoday\s+at\s+',
            r'\bon\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+at\s+',
            r'\bat\s+\d{1,2}[:.]?\d{0,2}\s*(am|pm|a\.m\.|p\.m\.)\b',
            r'\b\d{1,2}[:.]?\d{0,2}\s*(am|pm|a\.m\.|p\.m\.)\b',
            r'\bon\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(morning|afternoon|evening|night|tonight)\b',
            r'\bnext\s+week\b',
        ]
        
        task = text
        for pattern in time_patterns:
            task = re.sub(pattern, '', task, flags=re.IGNORECASE)
        
        task = re.sub(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', '', task, flags=re.IGNORECASE)
        task = re.sub(r'\b(tomorrow|today)\b', '', task, flags=re.IGNORECASE)
        task = re.sub(r'\b(to\s+)?morrow\b', '', task, flags=re.IGNORECASE)
        task = re.sub(r'[.,!?]+', '', task)
        task = re.sub(r'\s+', ' ', task)
        task = task.strip()
        task = re.sub(r'^(to|at|on|in)\s+', '', task, flags=re.IGNORECASE)
        task = re.sub(r'\s+(to|at|on|in)$', '', task, flags=re.IGNORECASE)
        
        if len(task) < 3 or task.isdigit():
            return ""
        
        return task
    
    def set_reminder(self, text):
        """Set a reminder from natural language text."""
        with reminders_lock:
        # Load existing reminders
            if os.path.exists(self.reminders_file):
                try:
                    with open(self.reminders_file, 'r') as f:
                        reminders = json.load(f)
                except:
                    reminders = []
            else:
                reminders = []
        
        # Clean and preprocess text
        raw_lower = text.lower().strip()
        cleaned = text.strip()
        
        # Remove trigger prefixes
        trigger_prefix = re.compile(
            r'^(?:'
            r'remind\s+me(?:\s+to)?'
            r'|set\s+(?:a\s+|the\s+)?reminder(?:\s+to)?'
            r'|remember\s+to'
            r'|we\s+(?:need|have)\s+to'
            r')\s+',
            re.IGNORECASE
        )
        m = trigger_prefix.match(cleaned.lower())
        if m:
            cleaned = cleaned[m.end():].strip()
        
        cleaned = re.sub(r'^\bmorrow\b', 'tomorrow', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bto\s+morrow\b', 'tomorrow', cleaned, flags=re.IGNORECASE)
        
        if not cleaned:
            self.speak("What would you like me to remind you about?")
            return
        
        # Parse time
        parsed_time, success, error = self.time_parser.parse_time(cleaned)
        
        if not success:
            # Default to 1 minute from now if parsing fails
            reminder_time = datetime.now() + timedelta(minutes=1)
            reminder_text = cleaned
            self.speak("I could not understand the time. Setting reminder for 1 minute from now.")
        else:
            reminder_time = parsed_time
            converted_text = self.time_parser._convert_words_to_numbers(cleaned)
            reminder_text = self._extract_task_from_text(converted_text)
            if not reminder_text or len(reminder_text) < 3:
                reminder_text = cleaned
            reminder_text = re.sub(r'\b(we\s+)?remind\s+me(\s+to)?\b', '', reminder_text, flags=re.IGNORECASE).strip()
            reminder_text = re.sub(r'^(for|to)\s+', '', reminder_text, flags=re.IGNORECASE).strip()
        
        # Get next reminder ID
        reminder_id = max([r.get('id', 0) for r in reminders], default=0) + 1
        
        # Create reminder
        reminder = {
            "id": reminder_id,
            "text": reminder_text,
            "time": reminder_time.isoformat(),
            "active": True,
        }
        
        reminders.append(reminder)
        
        # Write to JSON file
        try:
            with reminders_lock:
                with open(self.reminders_file, 'w') as f:
                    json.dump(reminders, f, indent=4)
        except Exception as e:
            print(f"Error saving reminder: {e}")
            self.speak("Sorry, I couldn't save the reminder.")
            return
        
        # Schedule reminder
        job_id = f"reminder_{reminder_id}"
        try:
           
            self.scheduler.add_job(
                self.trigger_reminder,
                'date',
                run_date=reminder_time,
                args=[reminder_id, reminder_text],
                id=job_id,
                replace_existing=True,
            )
        except Exception as e:
            print(f"Error scheduling reminder: {e}")
        
        human_time = self.time_parser.format_time_human(reminder_time)
        self.speak(f"Reminder set for {human_time}: {reminder_text}")
    
    def delete_reminder_by_number(self, text):
        text_lower = text.lower().strip()
        match = re.search(r'(\d+)', text_lower)
        if match:
            reminder_number = int(match.group(1))
        else: 
            #mapping the word to number
            word_to_number ={
                "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
                "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
            }
            match2 = re.search(r'(?:number|#)\s*([a-z]+)', text_lower)
            if match2 and match2.group(1) in word_to_number:
                reminder_number = word_to_number[match2.group(1)]
            else:
                match3 = re.search(r'\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b', text_lower)
                if match3:
                    reminder_number = word_to_number[match3.group(1)]
                else:
                    self.speak("Please say the reminder number, for example 'delete reminder number 2'.")
                    return
        
        # Load reminders
        if not os.path.exists(self.reminders_file):
            self.speak("You have no reminders to delete.")
            return
        
        try:
            with open(self.reminders_file, 'r') as f:
                reminders = json.load(f)
        except:
            self.speak("Error loading reminders.")
            return
        
        now = datetime.now()
        active_reminders = sorted(
            [r for r in reminders if r.get("active", True) and datetime.fromisoformat(r['time']) > now],
            key=lambda r: datetime.fromisoformat(r['time'])
        )
        
        if not active_reminders:
            self.speak("You have no active reminders to delete.")
            return
        
        if reminder_number < 1 or reminder_number > len(active_reminders):
            self.speak(f"Invalid reminder number. You have {len(active_reminders)} active reminders.")
            return
        
        reminder_to_delete = active_reminders[reminder_number - 1]
        
        # Mark as inactive
        for r in reminders:
            if r['id'] == reminder_to_delete['id']:
                r['active'] = False
                break
        
        # Remove from scheduler
        job_id = f"reminder_{reminder_to_delete['id']}"
        try:
            self.scheduler.remove_job(job_id)
        except:
            pass
        
        # Save to JSON
        try:
            with open(self.reminders_file, 'w') as f:
                json.dump(reminders, f, indent=4)
            self.speak(f"Reminder number {reminder_number} deleted: {reminder_to_delete['text']}")
        except:
            self.speak("Error deleting reminder.")
        
    def delete_reminder_by_content(self, text):
        text_lower = text.lower()
        for phrase in ['delete the', "remove the", "cancel the", "delete", "cancel", "reminder about", "reminder to", "reminder"]:
            text_lower = text_lower.replace(phrase, "")
        text_lower = text_lower.strip()
        if not text_lower or len(text_lower) < 3:
            self.speak("Please tell me what the reminder is about. For example, say 'delete the reminder about calling mom'")
            return
        
        # Load reminders
        if not os.path.exists(self.reminders_file):
            self.speak("You have no active reminder to delete.")
            return
        
        try:
            with open(self.reminders_file, 'r') as f:
                reminders = json.load(f)
        except:
            self.speak("Error loading reminders.")
            return
        
        now = datetime.now()
        active_reminders = [r for r in reminders if r.get("active", True) and datetime.fromisoformat(r['time']) > now]
        if not active_reminders:
            self.speak("You have no active reminder to delete.")
            return
        
        #here we are looking for reminder that matches the search text
        matching_reminders = []
        for reminder in active_reminders:
            reminder_text_lower = reminder['text'].lower()
            if text_lower in reminder_text_lower or any(word in reminder_text_lower for word in text_lower.split()):
                matching_reminders.append(reminder)
        if not matching_reminders:
            self.speak(f"I could not find any reminders matching '{text_lower}'. Please try again with different keywords.")
            return
        if len(matching_reminders) == 1:
            reminder = matching_reminders[0]
            # Mark as inactive
            for r in reminders:
                if r['id'] == reminder['id']:
                    r['active'] = False
                    break
            
            # Remove from scheduler
            job_id = f"reminder_{reminder['id']}"
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
            
            # Save to JSON
            try:
                with open(self.reminders_file, 'w') as f:
                    json.dump(reminders, f, indent=4)
                self.speak(f"Deleted reminder: {reminder['text']}")
            except:
                self.speak("Failed to delete the reminder. Please try again")
        else:
            matching_reminders.sort(key=lambda r: datetime.fromisoformat(r['time']))
            self.speak(f"I found {len(matching_reminders)} reminders matching your request:")
            for i, reminder in enumerate(matching_reminders, 1):
                time_str = datetime.fromisoformat(reminder['time']).strftime("%I:%M %p on %B %d")
                self.speak(f"Number {i}: {reminder['text']} at {time_str}")
            self.speak("Please say ' delete reminder number' followed by the number you want to delete")
    
    def delete_reminder_by_id(self, reminder_id):
        """Delete a reminder by ID."""
        if not os.path.exists(self.reminders_file):
            return False
        
        try:
            with open(self.reminders_file, 'r') as f:
                reminders = json.load(f)
        except:
            return False
        
        for r in reminders:
            if r['id'] == reminder_id:
                r['active'] = False
                break
        
        # Remove from scheduler
        job_id = f"reminder_{reminder_id}"
        try:
            self.scheduler.remove_job(job_id)
        except:
            pass
        
        # Save to JSON
        try:
            with open(self.reminders_file, 'w') as f:
                json.dump(reminders, f, indent=4)
            return True
        except:
            return False

    def clear_all_reminders(self):
        """Clear all reminders."""
        if not os.path.exists(self.reminders_file):
            self.speak("You have no reminders to clear.")
            return
        
        try:
            with open(self.reminders_file, 'r') as f:
                reminders = json.load(f)
        except:
            self.speak("Error loading reminders.")
            return
        
        # Remove all jobs from scheduler
        for reminder in reminders:
            job_id = f"reminder_{reminder['id']}"
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
        
        # Clear reminders
        reminders = []
        
        # Save to JSON
        try:
            with open(self.reminders_file, 'w') as f:
                json.dump(reminders, f, indent=4)
            self.speak("All reminders have been cleared.")
        except:
            self.speak("Error clearing reminders.")

    def trigger_reminder(self, reminder_id, reminder_text):
        """Trigger a reminder when its time is reached."""
        self.speak(f"Reminder: {reminder_text}")
        # Mark as inactive
        if os.path.exists(self.reminders_file):
            try:
                with reminders_lock:
                    with open(self.reminders_file, 'r') as f:
                        reminders = json.load(f)
                    for r in reminders:
                        if r['id'] == reminder_id:
                            r['active'] = False
                    with open(self.reminders_file, 'w') as f:
                        json.dump(reminders, f, indent=4)
            except:
                pass

    def list_reminders(self):
        """List all active reminders."""
        if not os.path.exists(self.reminders_file):
            self.speak("You have no active reminders.")
            return
        
        try:
            with reminders_lock:    
                with open(self.reminders_file, 'r', encoding="utf-8") as f:
                    reminders = json.load(f)
        except:
            self.speak("Error loading reminders.")
            return
        
        now = datetime.now()
        active_reminders = [
            r for r in reminders 
            if r.get("active", True) and datetime.fromisoformat(r['time']) > now
        ]
        
        if not active_reminders:
            self.speak("You have no active reminders.")
            return
        active_reminders.sort(key=lambda r: datetime.fromisoformat(r["time"]))
        parts = []
        for r in active_reminders:
            text = r.get('text', 'No description')
            time_str = r.get('time', '')
            try:
                dt = datetime.fromisoformat(time_str)
                friendly_time = dt.strftime("%I:%M %p on %B %d, %Y")
            except Exception:
                friendly_time = time_str or "an unknown time"
            parts.append(f"{text} at {friendly_time}")
        if len(active_reminders) == 1:
            msg = "You have 1 active reminder: " + parts[0]
        else:
            msg = f"You have {len(active_reminders)} active reminders: " + "; ".join(parts)
        self.speak(msg)
        return msg

    def run(self):
        print("\n" + "="*60)
        print("TalkAssist - Offline Mode")
        print("="*60)
        print("Commands: time, date, 'remind me to...', 'list reminders', 'goodbye'")
        print("="*60 + "\n")

        # Ensure _stop_event is cleared at start
        self._stop_event.clear()
        
        # Mark as running
        self.is_running = True
        
        # Speak greeting and ensure it completes before continuing
        greeting = "Hello! I am TalkAssist running in offline mode. How can I assist you today?"
        self.speak(greeting)
        
        # Give TTS a moment to start, especially when using GUI TTS from a thread
        time.sleep(0.5)

        conversation_ended_naturally = False
        
        iteration = 0
        while not self._stop_event.is_set() and self.is_running:
            iteration += 1
            #print(f"DEBUG: Loop iteration {iteration} - stop_event={self._stop_event.is_set()}, is_running={self.is_running}")
            
            try:
                # Check stop event before listening
                if self._stop_event.is_set():
                    break
                
                if not self.is_running:
                    break

                if self._tts_thread and self._tts_thread.is_alive():
                    time.sleep(0.1)
                    continue
                
                # Debug output to show we're about to listen
                
                try:
                    user_text = self.listen()
                    #print(f"DEBUG: listen() returned: '{user_text}'")
                except Exception as listen_error:
                    #print(f"DEBUG: Error in listen(): {listen_error}")
                    import traceback
                    traceback.print_exc()
                    user_text = ""  # Set to empty string to continue loop

                # Check stop event after listening
                if self._stop_event.is_set():
                    print("DEBUG: Stop event is set after listen(), breaking loop")
                    break

                if not user_text or user_text.strip() == "":
                    # Empty input - continue listening (don't break the loop)
                    continue

                #print(f"DEBUG: Processing command: {user_text}")
                try:
                    should_continue = self.process_command(user_text)
                    
                    # Give TTS a moment to start (especially important for GUI TTS)
                    time.sleep(0.3)
                    
                except Exception as cmd_error:
                    print(f"DEBUG: Error in process_command: {cmd_error}")
                    import traceback
                    traceback.print_exc()
                    should_continue = True  # Continue the loop even if command processing fails

                # Verify we should continue before checking the flag
                if not should_continue:
                    conversation_ended_naturally = True
                    # Stop the loop to allow cleanup
                    self._stop_event.set()
                    self.is_running = False
                    break
                
                # Re-check stop event after processing (in case something set it during processing)
                if self._stop_event.is_set():
                    break
                    
                if not self.is_running:
                    break
                
                # Explicitly continue to next iteration
                continue
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by the user (Ctrl+C)")
                self.speak("Goodbye! Have a great day!")
                conversation_ended_naturally = True
                self.is_running = False
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                import traceback
                traceback.print_exc()
                self.speak("Sorry, I encountered an error. Please try again.")
                # Continue the loop even after errors - don't exit
                print("DEBUG: Error handled, continuing loop...")
                continue

        # Mark as not running
        self.is_running = False
        
        if conversation_ended_naturally:
            print("\nConversation ended. Returning to wake word detection...")
            # Don't shut down scheduler on natural end - reminders should persist
        else:
            print("\nShutting down...")
            try:
                self.scheduler.shutdown()
            except:
                pass  # Scheduler might already be shut down
            print("Goodbye!")

    def stop(self):
        """Request the offline loop to stop and shutdown resources."""
        self.is_running = False
        self._stop_event.set()
        try:
            self.scheduler.shutdown()
        except:
            pass  # Scheduler might already be shut down

if __name__ == "__main__":
    offline_mode = OfflineMode()
    offline_mode.run()



