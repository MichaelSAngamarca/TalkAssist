"""
Modern GUI for TalkAssist using tkinter
Displays conversations in a clean, chat-like interface
Handles TTS to avoid duplicate audio output
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from datetime import datetime
import queue
import pyttsx3

class TalkAssistGUI:
    def __init__(self, root=None):
        if root is None:
            self.root = tk.Tk()
        else:
            self.root = root
        
        self.root.title("TalkAssist")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f0f0")
        
        # Queue for thread-safe updates
        self.update_queue = queue.Queue()
        
        # Conversation history
        self.conversation_history = []
        
        # TTS engine (initialized lazily)
        self._tts_engine = None
        self._tts_lock = threading.Lock()
        self.tts_rate = 150
        self.tts_volume = 0.9
        
        self._create_widgets()
        self._start_update_loop()
    
    def _get_tts_engine(self):
        """Get or create TTS engine (thread-safe)"""
        if self._tts_engine is None:
            with self._tts_lock:
                if self._tts_engine is None:
                    try:
                        self._tts_engine = pyttsx3.init()
                        self._tts_engine.setProperty('rate', self.tts_rate)
                        self._tts_engine.setProperty('volume', self.tts_volume)
                    except Exception as e:
                        print(f"Warning: Could not initialize TTS engine: {e}")
                        return None
        return self._tts_engine
    
    def speak(self, text, rate=150, volume=0.9):
        """Speak text using text-to-speech (handled by GUI to avoid duplicates)"""
        if not text or text.strip() == "":
            return
        if text.lower().startswith(("error processing message", "sorry, the bot", "tts error")):
            return
        
        # Update rate/volume if changed
        if rate != self.tts_rate or volume != self.tts_volume:
            self.tts_rate = rate
            self.tts_volume = volume
            engine = self._get_tts_engine()
            if engine:
                engine.setProperty('rate', rate)
                engine.setProperty('volume', volume)
        
        # Speak in a separate thread to avoid blocking
        def _speak_thread():
            engine = self._get_tts_engine()
            if engine:
                try:
                    engine.say(text)
                    engine.runAndWait()
                    engine.stop()
                except Exception as e:
                    print(f"TTS Error: {e}")
        
        tts_thread = threading.Thread(target=_speak_thread, daemon=True)
        tts_thread.start()
        tts_thread = threading.Thread(target=_speak_thread, daemon=True)
        tts_thread.start()
        
    def _create_widgets(self):
        """Create and layout all GUI widgets"""
        # Main container
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header with status
        header_frame = tk.Frame(main_frame, bg="#2c3e50", height=60)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(
            header_frame,
            text="TalkAssist",
            font=("Segoe UI", 20, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Status indicator
        self.status_label = tk.Label(
            header_frame,
            text="● Ready",
            font=("Segoe UI", 12),
            bg="#2c3e50",
            fg="#95a5a6"
        )
        self.status_label.pack(side=tk.RIGHT, padx=20, pady=15)
        
        # Conversation area with scrollbar
        conversation_frame = tk.Frame(main_frame, bg="#ffffff", relief=tk.SUNKEN, bd=1)
        conversation_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Canvas for scrolling
        canvas = tk.Canvas(conversation_frame, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(conversation_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#ffffff")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        self.conversation_canvas = canvas
        self.conversation_frame = self.scrollable_frame
        
        # Info bar at bottom
        info_frame = tk.Frame(main_frame, bg="#ecf0f1", height=30)
        info_frame.pack(fill=tk.X)
        info_frame.pack_propagate(False)
        
        self.info_label = tk.Label(
            info_frame,
            text="Press Ctrl+Shift+A to activate, or say 'hey talk assist'",
            font=("Segoe UI", 9),
            bg="#ecf0f1",
            fg="#7f8c8d"
        )
        self.info_label.pack(pady=5)
        
    def _start_update_loop(self):
        """Start the update loop to process queued messages"""
        self._process_queue()
        self.root.after(50, self._start_update_loop)
    
    def _process_queue(self):
        """Process all pending updates from the queue"""
        try:
            while True:
                update = self.update_queue.get_nowait()
                update_type = update.get('type')
                
                if update_type == 'user_message':
                    self._add_user_message(update['message'])
                elif update_type == 'bot_message':
                    self._add_bot_message(update['message'])
                elif update_type == 'status':
                    self._update_status(update['status'], update.get('color', '#95a5a6'))
                elif update_type == 'info':
                    self._update_info(update['info'])
        except queue.Empty:
            pass
    
    def _add_user_message(self, message):
        """Add a user message to the conversation"""
        if not message or not message.strip():
            return
        
        # Create message frame
        msg_frame = tk.Frame(self.conversation_frame, bg="#ffffff")
        msg_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Message bubble (right-aligned)
        bubble_frame = tk.Frame(msg_frame, bg="#3498db", relief=tk.FLAT)
        bubble_frame.pack(side=tk.RIGHT, padx=(50, 0))
        
        # Message text
        msg_text = tk.Label(
            bubble_frame,
            text=message,
            font=("Segoe UI", 11),
            bg="#3498db",
            fg="white",
            wraplength=400,
            justify=tk.LEFT,
            padx=15,
            pady=10
        )
        msg_text.pack()
        
        # Timestamp
        timestamp = datetime.now().strftime("%H:%M")
        time_label = tk.Label(
            msg_frame,
            text=timestamp,
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#95a5a6"
        )
        time_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Scroll to bottom
        self._scroll_to_bottom()
        
        # Store in history
        self.conversation_history.append(('user', message, timestamp))
    
    def _add_bot_message(self, message):
        """Add a bot message to the conversation"""
        if not message or not message.strip():
            return
        
        # Skip internal error messages
        if message.lower().startswith(("error processing message", "sorry, the bot", "tts error")):
            return
        
        # Create message frame
        msg_frame = tk.Frame(self.conversation_frame, bg="#ffffff")
        msg_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Bot avatar/indicator (left side)
        avatar_label = tk.Label(
            msg_frame,
            text="🤖",
            font=("Segoe UI", 16),
            bg="#ffffff"
        )
        avatar_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Message bubble (left-aligned)
        bubble_frame = tk.Frame(msg_frame, bg="#ecf0f1", relief=tk.FLAT)
        bubble_frame.pack(side=tk.LEFT, padx=(0, 50))
        
        # Message text
        msg_text = tk.Label(
            bubble_frame,
            text=message,
            font=("Segoe UI", 11),
            bg="#ecf0f1",
            fg="#2c3e50",
            wraplength=400,
            justify=tk.LEFT,
            padx=15,
            pady=10
        )
        msg_text.pack()
        
        # Timestamp
        timestamp = datetime.now().strftime("%H:%M")
        time_label = tk.Label(
            msg_frame,
            text=timestamp,
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#95a5a6"
        )
        time_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Scroll to bottom
        self._scroll_to_bottom()
        
        # Store in history
        self.conversation_history.append(('bot', message, timestamp))
    
    def _scroll_to_bottom(self):
        """Scroll conversation to the bottom"""
        self.conversation_canvas.update_idletasks()
        self.conversation_canvas.yview_moveto(1.0)
    
    def _update_status(self, status, color="#95a5a6"):
        """Update the status indicator"""
        self.status_label.config(text=f"● {status}", fg=color)
    
    def _update_info(self, info):
        """Update the info bar"""
        self.info_label.config(text=info)
    
    # Public methods for thread-safe updates
    def add_user_message(self, message):
        """Thread-safe method to add user message"""
        self.update_queue.put({'type': 'user_message', 'message': message})
    
    def add_bot_message(self, message):
        """Thread-safe method to add bot message"""
        self.update_queue.put({'type': 'bot_message', 'message': message})
    
    def update_status(self, status, color="#95a5a6"):
        """Thread-safe method to update status"""
        self.update_queue.put({'type': 'status', 'status': status, 'color': color})
    
    def update_info(self, info):
        """Thread-safe method to update info"""
        self.update_queue.put({'type': 'info', 'info': info})
    
    def run(self):
        """Start the GUI main loop"""
        # Handle window close event
        def on_closing():
            try:
                import sys
                main_module = sys.modules.get('main')
                if main_module and hasattr(main_module, 'should_exit_program'):
                    setattr(main_module, 'should_exit_program', True)
                if main_module and hasattr(main_module, 'stop_monitoring'):
                    stop_monitoring = getattr(main_module, 'stop_monitoring')
                    if stop_monitoring:
                        stop_monitoring.set()
            except:
                pass
            self.root.quit()
            self.root.destroy()
        
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        self.root.mainloop()
    
    def destroy(self):
        """Close the GUI"""
        try:
            self.root.quit()
        except:
            pass
        try:
            self.root.destroy()
        except:
            pass

