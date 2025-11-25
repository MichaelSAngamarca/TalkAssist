from flask import Flask, render_template, request, jsonify, send_file
from tools import get_weather_info, get_region_info, get_date_info, search_web
from io import BytesIO
from elevenlabs import ElevenLabs
import os
import re
from dotenv import load_dotenv
#from main import handle_user_message, speak as tts_speak

# Load API key
load_dotenv()
api_key = os.getenv("ELEVENLABS_API_KEY")
elevenlabs = ElevenLabs(api_key=api_key)

# Initialize Flask app
app = Flask(
    __name__,
    template_folder="frontend/templates",
    static_folder="frontend/static"
)

# Try to use connectivity_checker if present; fallback to True
try:
    from connectivity_checker import check_internet_connectivity
except Exception:
    # Fallback if module missing
    def check_internet_connectivity(timeout: int = 3) -> bool:
        # Simple best-effort: return True (server is up)
        return True

# PING route used by frontend
@app.route("/ping", methods=["GET"])
def ping():
    try:
        internet = check_internet_connectivity()
        mode = "online" if internet else "offline"
    except Exception:
        internet = False
        mode = "offline"

    return jsonify({
        "status": "ok",
        "backend": True,
        "internet": bool(internet),
        "online": mode == "online",
        "mode": mode
    })

# Home route
@app.route("/")
def index():
    return render_template("index.html")

# Reminders route
@app.route("/reminders")
def reminders():
    return render_template("reminders.html")

# Remove timezone parentheses and trailing microseconds/decimal junk then strip.
def _clean_time_response(response_text):
    if not response_text:
        return response_text
    # remove parentheses with timezone like (America/New_York)
    cleaned = re.sub(r"\s*\([A-Za-z0-9_\/+-]+\)", "", response_text)
    # remove trailing numbers / microseconds (e.g. ...1234567)
    cleaned = re.sub(r"\.?(\d{5,})$", "", cleaned)
    # strip trailing ., spaces, commas
    cleaned = cleaned.rstrip("., ").strip()
    return cleaned

# Chat route
# @app.route("/ask", methods=["POST"])
# def ask():
#     data = request.get_json() or {}
#     user_input = (data.get("message", "") or "").lower()
#     mode = data.get("mode", "online")

#     # If client requested offline/degraded, return JSON response only (frontend will speak)
#     if mode != "online":
#         # Provide a safe local fallback (no heavy imports)
#         if "time" in user_input:
#             from datetime import datetime
#             now = datetime.now()
#             response = now.strftime("The current local time is %I:%M %p on %B %d, %Y.").lstrip("0")
#         elif "date" in user_input:
#             from datetime import date
#             today = date.today()
#             response = today.strftime("Today's date is %B %d, %Y.")
#         elif "remind" in user_input or "reminder" in user_input:
#             response = "Offline mode: reminders are not available through the web UI right now."
#         else:
#             response = "Offline mode active — I can only tell you the local date or time from the web interface."
#         return jsonify({"response": response})

#     # Online mode
#     # Weather
#     if "weather" in user_input:
#         location = extract_location(user_input)
#         if location:
#             response = get_weather_info({"location": location})
#             pretty = location.title()
#             response = response.replace(location.lower(), pretty)
#         else:
#             response = "Please specify a location."

#     # Time / timezone
#     elif "time" in user_input or "timezone" in user_input:
#         location = extract_location(user_input)
#         if location:
#             response = get_region_info({"location": location})
#             # Pretty-print the location
#             response = response.replace(location.lower(), location.title())
#             # Remove timezone parentheses and microseconds and format an ISO datetime if present
#             response = _clean_time_response(response)

#             # Try to find an ISO datetime and nicely format it
#             m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", response)
#             if m:
#                 from datetime import datetime
#                 try:
#                     dt = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
#                     pretty_dt = dt.strftime("%I:%M %p on %B %d, %Y").lstrip("0")
#                     response = response.replace(m.group(1), pretty_dt)
#                 except Exception:
#                     pass
#             response = _clean_time_response(response)
#         else:
#             response = "Please specify a location."

#     # Date
#     elif "date" in user_input:
#         location = extract_location(user_input)
#         response = get_date_info({"location": location})

#     # Search
#     elif "search" in user_input or "find" in user_input:
#         query = user_input.replace("search", "").replace("find", "").strip()
#         response = search_web({"query": query}) if query else "Please tell me what to search for."

#     else:
#         response = "I'm not sure how to help with that yet."

#     return jsonify({"response": response})
@app.route("/ask", methods=["POST"])
def ask():
    from main import handle_user_message
    data = request.get_json() or {}
    user_input = (data.get("message", "") or "").strip()
    mode = data.get("mode", "online")

    if not user_input:
        return jsonify({"response": ""})

    # For offline/degraded, just return a simple fallback (frontend TTS)
    if mode != "online":
        return jsonify({"response": user_input})  

    # Online mode — call main.py's conversation handler
    response = handle_user_message(user_input)
    return jsonify({"response": response})

# Speech route -> online: server TTS audio, offline/degraded: JSON and frontend TTS
# @app.route("/speak", methods=["POST"])
# def speak():
#     data = request.get_json() or {}
#     text = data.get("text", "")
#     mode = data.get("mode", "online")

#     if not text:
#         return jsonify({"error": "No text provided"}), 400

#     # If offline/degraded requested, return JSON for frontend TTS
#     if mode != "online" or elevenlabs is None:
#         # frontend will speak via speechSynthesis
#         return jsonify({"offline_mode": True, "text": text}), 200

#     # Online: ask ElevenLabs for audio
#     try:
#         audio_stream = elevenlabs.text_to_speech.convert(
#             # choose a valid voice id from your Eleven Labs account
#             voice_id="2EiwWnXFnvU5JabPnv8n",
#             model_id="eleven_turbo_v2",
#             text=text
#         )
#         audio_bytes = b"".join(audio_stream)
#         return send_file(
#             BytesIO(audio_bytes),
#             mimetype="audio/mpeg",
#             as_attachment=False
#         )
#     except Exception as e:
#         print("Error in /speak:", e)
#         # fallback JSON so frontend can speak
#         return jsonify({"offline_mode": True, "text": text, "error": str(e)}), 200
@app.route("/speak", methods=["POST"])
def speak():
    """
    Return audio using ElevenLabs or fallback JSON for frontend TTS.
    """
    from main import speak as tts_speak
    data = request.get_json() or {}
    text = data.get("text", "")
    mode = data.get("mode", "online")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    # If offline or degraded, frontend handles speech
    if mode != "online":
        return jsonify({"offline_mode": True, "text": text})

    # Online: try ElevenLabs or main.py TTS
    try:
        # You can also use main.py's speak() helper if you want local TTS
        tts_speak(text)
        return jsonify({"success": True, "text": text})
    except Exception as e:
        return jsonify({"offline_mode": True, "text": text, "error": str(e)}), 200

# Location extraction helper
def extract_location(text):
    """Extracts a location after the word 'in', stripping punctuation."""
    if not text:
        return None
    match = re.search(r"\bin\s+([a-zA-Z\s]+)", text)
    if match:
        location = match.group(1).strip().rstrip("?.!,")
        return location
    return None

# --- Run the app ---
# if __name__ == "__main__":
#    app.run(debug=True)
