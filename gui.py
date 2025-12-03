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
import json
import os

class TalkAssistGUI:
    def __init__(self, root=None):
        if root is None:
            self.root = tk.Tk()
        else:
            self.root = root
        
        self.root.title("TalkAssist")
        self.root.geometry("1000x600")
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

        # TTS queue + worker (single thread handles all speech)
        self._tts_queue = queue.Queue()
        self._tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self._tts_thread.start()

        
        # Reminders data
        self.reminders = []
        self.reminders_file = "reminders.json"
        
        self._create_widgets()
        self._load_reminders()
        self._start_update_loop()
    
    def _get_tts_engine(self):
        """Get or create TTS engine (thread-safe)"""
        if self._tts_engine is None:
            with self._tts_lock:
                if self._tts_engine is None:
                    try:
                        try:
                            self._tts_engine = pyttsx3.init(driverName='sapi5')
                        except Exception:
                            self._tts_engine = pyttsx3.init()
                        self._tts_engine.setProperty('rate', self.tts_rate)
                        self._tts_engine.setProperty('volume', self.tts_volume)
                        print("TTS engine initialized")
                    except Exception as e:
                        print(f"TTS Initialization Error: {e}")
                        return None
        return self._tts_engine
        
    def _tts_worker(self):
        while True:
            item = self._tts_queue.get()
            if item is None:
                # Optional: allow clean shutdown by putting None in the queue
                self._tts_queue.task_done()
                break

            text, rate, volume = item

            if not text or text.strip() == "":
                self._tts_queue.task_done()
                continue

            engine = self._get_tts_engine()
            if not engine:
                self._tts_queue.task_done()
                continue

            # Only one TTS operation at a time
            with self._tts_lock:
                try:
                    if rate != self.tts_rate or volume != self.tts_volume:
                        self.tts_rate = rate
                        self.tts_volume = volume
                        engine.setProperty('rate', rate)
                        engine.setProperty('volume', volume)

                    # NOTE: no engine.stop() here, we keep the engine alive
                except Exception as e:
                    print(f"TTS Error: {e}")

            self._tts_queue.task_done()

    
    def speak(self, text, rate=150, volume=0.9):
        """Queue text to be spoken by TTS engine"""
        if not text or text.strip() == "":
            return
        if text.lower().startswith(("error processing message", "sorry, the bot", "tts error")):
            return
        if not hasattr(self, '_tts_queue') or self._tts_queue is None:
            self._tts_queue = queue.Queue()
            self._tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self._tts_thread.start()
        self._tts_queue.put((text, rate, volume))

        
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
        
        # Navigation buttons
        nav_frame = tk.Frame(header_frame, bg="#2c3e50")
        nav_frame.pack(side=tk.LEFT, padx=(40, 0))
        
        # Conversation button
        self.conversation_btn = tk.Label(
            nav_frame,
            text="💬 Conversation",
            font=("Segoe UI", 11, "bold"),
            bg="#3498db",
            fg="white",
            padx=15,
            pady=8,
            cursor="hand2",
        )
        self.conversation_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.conversation_btn.bind("<Button-1>", lambda e: self._show_conversation_view())
        self.conversation_btn.bind("<Enter>", lambda e: self.conversation_btn.config(relief=tk.RAISED))
        self.conversation_btn.bind("<Leave>", lambda e: self.conversation_btn.config(relief=tk.FLAT))
                
        # Reminders button
        self.reminders_btn = tk.Label(
            nav_frame,
            text="📋 Reminders",
            font=("Segoe UI", 11),
            bg="#2980b9",
            fg="white",
            padx=15,
            pady=8,
            cursor="hand2",
        )
        self.reminders_btn.pack(side=tk.LEFT)
        self.reminders_btn.bind("<Button-1>", lambda e: self._show_reminders_view())
        self.reminders_btn.bind("<Enter>", lambda e: self.reminders_btn.config(relief=tk.RAISED))
        self.reminders_btn.bind("<Leave>", lambda e: self.reminders_btn.config(relief=tk.FLAT))
        
        # Status indicator
        self.status_label = tk.Label(
            header_frame,
            text="● Ready",
            font=("Segoe UI", 12),
            bg="#2c3e50",
            fg="#95a5a6"
        )
        self.status_label.pack(side=tk.RIGHT, padx=20, pady=15)

        # Microphone indicator (hidden initially)
        self.mic_label = tk.Label(
            header_frame,
            text="🎤 Listening...",
            font=("Segoe UI", 12, "bold"),
            bg="#2c3e50",
            fg="#e74c3c"  # red color
        )
        self.mic_label.pack(side=tk.RIGHT, padx=20, pady=15)
        self.mic_label.pack_forget()
        
        # Main content area (will switch between conversation and reminders)
        self.content_frame = tk.Frame(main_frame, bg="#f0f0f0")
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Conversation area with scrollbar
        conversation_frame = tk.Frame(self.content_frame, bg="#ffffff", relief=tk.SUNKEN, bd=1)
        conversation_frame.pack(fill=tk.BOTH, expand=True)
        
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
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        self.conversation_canvas = canvas
        self.conversation_frame = self.scrollable_frame
        self.conversation_container = conversation_frame
        
        # Reminders section (separate page - initially hidden)
        reminders_container = tk.Frame(self.content_frame, bg="#ffffff", relief=tk.SUNKEN, bd=1)
        # Will be shown when reminders button is clicked
        
        # Reminders header
        reminders_header = tk.Frame(reminders_container, bg="#34495e", height=50)
        reminders_header.pack(fill=tk.X)
        reminders_header.pack_propagate(False)
        
        reminders_title = tk.Label(
            reminders_header,
            text="📋 Reminders",
            font=("Segoe UI", 18, "bold"),
            bg="#34495e",
            fg="white"
        )
        reminders_title.pack(pady=15)
        
        # Reminders scrollable area
        reminders_canvas = tk.Canvas(reminders_container, bg="#ffffff", highlightthickness=0)
        reminders_scrollbar = ttk.Scrollbar(reminders_container, orient="vertical", command=reminders_canvas.yview)
        self.reminders_scrollable_frame = tk.Frame(reminders_canvas, bg="#ffffff")
        
        self.reminders_scrollable_frame.bind(
            "<Configure>",
            lambda e: reminders_canvas.configure(scrollregion=reminders_canvas.bbox("all"))
        )
        
        reminders_canvas.create_window((0, 0), window=self.reminders_scrollable_frame, anchor="nw")
        reminders_canvas.configure(yscrollcommand=reminders_scrollbar.set)
        
        reminders_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        reminders_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind mousewheel to reminders canvas
        def _on_reminders_mousewheel(event):
            reminders_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        reminders_canvas.bind("<MouseWheel>", _on_reminders_mousewheel)
        
        # Also bind to the scrollable frame for better UX
        self.reminders_scrollable_frame.bind("<MouseWheel>", _on_reminders_mousewheel)
        
        self.reminders_canvas = reminders_canvas
        self.reminders_container = reminders_container
        
        # Track current view
        self.current_view = "conversation"  # "conversation" or "reminders"
        
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

    def _get_bubble_font(self):
        """Return the font tuple used inside bubbles (single place to tweak)."""
        return ("Segoe UI", 11)

    def _draw_rounded_rect(self, canvas, x1, y1, x2, y2, r=12, **kwargs):
        """
        Draw a rounded rectangle by composing rectangles + corner ovals.
        kwargs are passed to each create_* call (use 'fill' and 'outline').
        """
        # center rectangles
        canvas.create_rectangle(x1 + r, y1, x2 - r, y2, **kwargs)
        canvas.create_rectangle(x1, y1 + r, x2, y2 - r, **kwargs)
        # corner ovals
        canvas.create_oval(x1, y1, x1 + 2*r, y1 + 2*r, **kwargs)
        canvas.create_oval(x2 - 2*r, y1, x2, y1 + 2*r, **kwargs)
        canvas.create_oval(x1, y2 - 2*r, x1 + 2*r, y2, **kwargs)
        canvas.create_oval(x2 - 2*r, y2 - 2*r, x2, y2, **kwargs)

    def _create_bubble_widget(self, parent, text, bg_color, fg_color, align="left", max_width=400, pad_x=12, pad_y=10):
        """
        Create a Canvas containing a rounded bubble + text.
        Returns the canvas widget (already sized).
        align: "left" or "right" (only affects packing in caller).
        """
        fnt = self._get_bubble_font()
        canvas = tk.Canvas(parent, bg="#ffffff", highlightthickness=0, bd=0)
        # Create text with width so it wraps
        text_id = canvas.create_text(pad_x, pad_y, text=text, anchor="nw", width=max_width,
                                     font=fnt, fill=fg_color)
        # Measure
        canvas.update_idletasks()
        bbox = canvas.bbox(text_id)  # (x1, y1, x2, y2)
        if not bbox:
            bbox = (0, 0, max_width, fnt[1] if isinstance(fnt[1], int) else 14)
        x1 = bbox[0] - pad_x
        y1 = bbox[1] - pad_y
        x2 = bbox[2] + pad_x
        y2 = bbox[3] + pad_y
        # Ensure positive coords
        if x1 < 0: x1 = 0
        if y1 < 0: y1 = 0

        # Draw rounded rect behind text (use same fill for outline for a clean look)
        self._draw_rounded_rect(canvas, x1, y1, x2, y2, r=12, fill=bg_color, outline=bg_color)
        # Raise text above the shapes
        canvas.tag_raise(text_id)

        # Size the canvas to fit the bubble neatly
        width = x2 + 6
        height = y2 + 6
        canvas.config(width=width, height=height)
        return canvas
        
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
                elif update_type == 'refresh_reminders':
                    self._load_reminders()
                elif update_type == 'mic':
                    action = update.get('action', '')
                    if action == 'show':
                        self.show_microphone()
                    else:
                        self.hide_microphone()
        except queue.Empty:
            pass
    
    def _add_user_message(self, message):
        """Add a user message to the conversation"""
        if not message or not message.strip():
            return
        
        # Create message frame
        msg_frame = tk.Frame(self.conversation_frame, bg="#ffffff")
        msg_frame.pack(fill=tk.X, padx=10, pady=6)
        
        # Bubble canvas (right side)
        bubble_canvas = self._create_bubble_widget(
            msg_frame,
            text=message,
            bg_color="#3498db",   # user's bubble color
            fg_color="white",
            align="right",
            max_width=420
        )
        bubble_canvas.pack(side=tk.RIGHT, padx=(50, 10))
        
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
        msg_frame.pack(fill=tk.X, padx=10, pady=6)
        
        # Bot avatar/indicator (left side)
        avatar_label = tk.Label(
            msg_frame,
            text="🤖",
            font=("Segoe UI", 16),
            bg="#ffffff"
        )
        avatar_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Bubble canvas (left side)
        bubble_canvas = self._create_bubble_widget(
            msg_frame,
            text=message,
            bg_color="#ecf0f1",   # bot bubble color
            fg_color="#2c3e50",
            align="left",
            max_width=420
        )
        bubble_canvas.pack(side=tk.LEFT, padx=(10, 50))
        
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
    
    def _show_conversation_view(self):
        """Switch to conversation view"""
        self.current_view = "conversation"
        # Hide reminders
        self.reminders_container.pack_forget()
        # Show conversation
        self.conversation_container.pack(fill=tk.BOTH, expand=True)
        # Update button styles
        self.conversation_btn.config(bg="#3498db", font=("Segoe UI", 11, "bold"))
        self.reminders_btn.config(bg="#2980b9", font=("Segoe UI", 11))
    
    def _show_reminders_view(self):
        """Switch to reminders view"""
        self.current_view = "reminders"
        # Hide conversation
        self.conversation_container.pack_forget()
        # Show reminders
        self.reminders_container.pack(fill=tk.BOTH, expand=True)
        # Update button styles
        self.reminders_btn.config(bg="#3498db", font=("Segoe UI", 11, "bold"))
        self.conversation_btn.config(bg="#2980b9", font=("Segoe UI", 11))
        # Refresh reminders display
        self._load_reminders()
    
    def _load_reminders(self):
        """Load reminders from JSON file"""
        try:
            if os.path.exists(self.reminders_file):
                with open(self.reminders_file, 'r', encoding='utf-8') as f:
                    self.reminders = json.load(f)
                self._display_reminders()
            else:
                self.reminders = []
        except Exception as e:
            print(f"Error loading reminders: {e}")
            self.reminders = []
    
    def _display_reminders(self):
        """Display reminders in the reminders section"""
        # Clear existing reminders
        for widget in self.reminders_scrollable_frame.winfo_children():
            widget.destroy()
        
        if not self.reminders:
            no_reminders_label = tk.Label(
                self.reminders_scrollable_frame,
                text="No reminders",
                font=("Segoe UI", 10),
                bg="#ffffff",
                fg="#95a5a6"
            )
            no_reminders_label.pack(pady=20, padx=10)
            return
        
        for reminder in self.reminders:
            self._create_reminder_widget(reminder)
    
    def _create_reminder_widget(self, reminder):
        """Create a widget for a single reminder"""
        # Determine colors based on active status
        if reminder.get('active', False):
            bg_color = "#e8f5e9"
            border_color = "#4caf50"
            status_text = "● Active"
            status_color = "#2e7d32"
        else:
            bg_color = "#f5f5f5"
            border_color = "#9e9e9e"
            status_text = "○ Inactive"
            status_color = "#757575"
        
        # Reminder container
        reminder_frame = tk.Frame(
            self.reminders_scrollable_frame,
            bg=bg_color,
            relief=tk.RAISED,
            bd=1
        )
        reminder_frame.pack(fill=tk.X, padx=20, pady=8)
        
        # Status indicator
        status_frame = tk.Frame(reminder_frame, bg=bg_color)
        status_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        status_label = tk.Label(
            status_frame,
            text=status_text,
            font=("Segoe UI", 9, "bold"),
            bg=bg_color,
            fg=status_color
        )
        status_label.pack(side=tk.LEFT)
        
        # Reminder ID (small, subtle)
        id_label = tk.Label(
            status_frame,
            text=f"#{reminder.get('id', '?')}",
            font=("Segoe UI", 8),
            bg=bg_color,
            fg="#95a5a6"
        )
        id_label.pack(side=tk.RIGHT)
        
        # Reminder text
        text_label = tk.Label(
            reminder_frame,
            text=reminder.get('text', 'No text'),
            font=("Segoe UI", 11),
            bg=bg_color,
            fg="#2c3e50",
            wraplength=600,
            justify=tk.LEFT,
            anchor="w"
        )
        text_label.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # Reminder time
        time_str = reminder.get('time', '')
        if time_str:
            try:
                # Parse ISO format datetime
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%Y-%m-%d %H:%M")
            except:
                formatted_time = time_str
        else:
            formatted_time = "No time set"
        
        time_label = tk.Label(
            reminder_frame,
            text=f"⏰ {formatted_time}",
            font=("Segoe UI", 9),
            bg=bg_color,
            fg="#7f8c8d"
        )
        time_label.pack(fill=tk.X, padx=10, pady=(0, 10))
    
    def refresh_reminders(self):
        """Refresh the reminders display (thread-safe)"""
        self.update_queue.put({'type': 'refresh_reminders'})
    
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

    def show_microphone(self):
        """Directly show the microphone indicator (UI thread)."""
        # If mic_label was added use it; otherwise create fallback
        try:
            # If mic_label exists but is hidden, pack it to show
            if hasattr(self, 'mic_label'):
                # Ensure it's visible on the right without duplicating
                try:
                    self.mic_label.pack(side=tk.RIGHT, padx=20, pady=15)
                except Exception:
                    # If already packed, ignore
                    pass
            else:
                # Create a fallback mic label if it doesn't exist
                self.mic_label = tk.Label(self.root, text="🎤 Listening...", font=("Helvetica", 12, "bold"), bg="#2c3e50", fg="#e74c3c")
                self.mic_label.pack(side=tk.RIGHT, padx=20, pady=15)
        except Exception:
            pass

    def hide_microphone(self):
        """Directly hide the microphone indicator (UI thread)."""
        try:
            if hasattr(self, 'mic_label'):
                self.mic_label.pack_forget()
        except Exception:
            pass

    # Microphone control (thread-safe)
    def show_microphone_safe(self):
        """Thread-safe request to show the microphone indicator."""
        self.update_queue.put({'type': 'mic', 'action': 'show'})

    def hide_microphone_safe(self):
        """Thread-safe request to hide the microphone indicator."""
        self.update_queue.put({'type': 'mic', 'action': 'hide'})
    
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