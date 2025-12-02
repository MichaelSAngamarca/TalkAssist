import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from elevenlabs.conversational_ai.conversation import ClientTools
from langchain_community.tools import DuckDuckGoSearchRun
from connectivity_checker import check_internet_connectivity, safe_api_call
import time
import json
from time_parser import TimeParser

load_dotenv()
def handle_api_failure(error_msg, fallback_msg="I'm sorry, I'm having trouble connecting to the internet. Please check your connection and try again."):
    
    if not check_internet_connectivity():
        return "I'm currently offline and cannot access this information. Please check your internet connection."
    return f"Error: {error_msg}. {fallback_msg}"

def get_current_time(parameters):
    location = parameters.get("location")
    
    if location:
        if not check_internet_connectivity():
            return handle_api_failure("No internet connection available")
        
        try:
            geo_url = "https://nominatim.openstreetmap.org/search"
            geo_params = {"q": location, "format": "json"}
            geo_res = requests.get(geo_url, params=geo_params, headers={"User-Agent": "TalkAssistBot/1.0"}).json()

            if not geo_res:
                return f"Could not find location: {location}"

            lat = geo_res[0]["lat"]
            lon = geo_res[0]["lon"]

            tz_url = f"https://timeapi.io/api/TimeZone/coordinate?latitude={lat}&longitude={lon}"
            tz_res = requests.get(tz_url).json()
            timezone = tz_res.get("timeZone", None)

            if not timezone:
                return f"Could not find timezone for {location}."

            time_url = f"https://timeapi.io/api/Time/current/zone?timeZone={timezone}"
            time_res = requests.get(time_url).json()

            current_time = time_res.get("dateTime", None)
            if not current_time:
                return f"Could not get current time for {location}."

            return f"The current time in {location} ({timezone}) is {current_time}"

        except Exception as e:
            return f"Error getting time for {location}: {e}"
    else:
        try:
            now = datetime.now()
            formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
            timezone_name = time.tzname[0] if time.tzname[0] else "local timezone"
            return f"The current local time is {formatted_time} ({timezone_name})"
        except Exception as e:
            return f"Error getting local time: {e}"

def get_region_info(parameters):
    return get_current_time(parameters)

def get_weather_info(parameters):
    location = parameters.get("location")
    if not location:
        return "Please provide a location."
    
    if not check_internet_connectivity():
        return handle_api_failure("No internet connection available")

    try:
        geo_url = "https://nominatim.openstreetmap.org/search"
        geo_params = {"q": location, "format": "json"}
        #geo_res = requests.get(geo_url, params=geo_params).json()
        geo_res = requests.get(geo_url, params=geo_params, headers={"User-Agent": "TalkAssistBot/1.0"}).json()


        if not geo_res:
            return f"Could not find location: {location}"

        lat = geo_res[0]["lat"]
        lon = geo_res[0]["lon"]

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current_weather=true"
        )
        weather_res = requests.get(weather_url).json()

        current_weather = weather_res.get("current_weather", {})
        if not current_weather:
            return f"Could not retrieve weather for {location}."

        temperature = current_weather.get("temperature")
        windspeed = current_weather.get("windspeed")
        conditions = current_weather.get("weathercode")

        weather_map = {
            0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
            45: "foggy", 48: "freezing fog", 51: "light drizzle", 53: "moderate drizzle",
            55: "dense drizzle", 61: "light rain", 63: "moderate rain", 65: "heavy rain",
            71: "light snow", 73: "moderate snow", 75: "heavy snow", 95: "thunderstorm",
        }

        condition_text = weather_map.get(conditions, "unknown conditions")
        return (
            f"The current weather in {location} is {condition_text} "
            f"with a temperature of {temperature}°C and windspeed of {windspeed} km/h."
        )

    except Exception as e:
        return f"Error getting weather info: {e}"
    
def get_date_info(parameters):
    location = parameters.get("location")
    
    if location:
        if not check_internet_connectivity():
            return handle_api_failure("No internet connection available")
        
        try:
            geo_url = "https://nominatim.openstreetmap.org/search"
            geo_params = {"q": location, "format": "json"}
            geo_res = requests.get(geo_url, params=geo_params, headers={"User-Agent": "TalkAssistBot/1.0"}).json()

            if not geo_res:
                return f"Could not find location: {location}"

            lat = geo_res[0]["lat"]
            lon = geo_res[0]["lon"]

            tz_url = f"https://timeapi.io/api/TimeZone/coordinate?latitude={lat}&longitude={lon}"
            tz_res = requests.get(tz_url).json()
            timezone = tz_res.get("timeZone", None)

            if not timezone:
                return f"Could not find timezone for {location}."

            time_url = f"https://timeapi.io/api/Time/current/zone?timeZone={timezone}"
            time_res = requests.get(time_url).json()

            date_string = time_res.get("date", None)
            day_of_week = time_res.get("dayOfWeek", None)

            if not date_string:
                return f"Could not get date for {location}."

            return f"Today's date in {location} ({timezone}) is {day_of_week}, {date_string}."
        except Exception as e:
            return f"Error getting date for {location}: {e}"
    else:
        try:
            now = datetime.now()
            formatted_date = now.strftime("%A, %B %d, %Y")
            timezone_name = time.tzname[0] if time.tzname[0] else "local timezone"
            return f"Today's date is {formatted_date} ({timezone_name})"
        except Exception as e:
            return f"Error getting local date: {e}"

def search_web(parameters):
    query = parameters.get("query") if parameters else None
    if not query:
        return "No query provided."
    
    if not check_internet_connectivity():
        return handle_api_failure("No internet connection available")
    
    try:
        search = DuckDuckGoSearchRun()
        return search.run(query)
    except Exception as e:
        return handle_api_failure(f"Search failed: {str(e)}")

def save_to_txt(parameters):
    filename = parameters.get("filename")
    data = parameters.get("data")

    if not filename or not data:
        return "Missing filename or data."

    try:
        with open(filename, "a", encoding="utf-8") as file:
            file.write(f"{data}\n")
        return f"Data saved to {filename}"
    except Exception as e:
        return f"Error saving file: {e}"
    

   # this is a fuction for the online mode to set rmeinders and store them in a json file like the offline mode
def set_reminder(parameters):
    reminder_text = (parameters.get("text") or parameters.get("reminder") or parameters.get("task") or parameters.get("description") or parameters.get("title"))
    when = parameters.get("time")   or parameters.get("when")

    if not reminder_text:
        return "I could not find what the reminder should be about"
    if not when:
        return "I need to know when to schedule the reminder"
    parser = TimeParser()
    reminder_time = None
    try:
        reminder_time = datetime.fromisoformat(when)
        success = True
        error = None
    except Exception:
        reminder_time = None
        success = False
        error = None
    if reminder_time is None:
        try:
            parsed_time, success, error = parser.parse_time(when)
            reminder_time = parsed_time if success else None
        except Exception as e:
            reminder_time = None
            success = False
            error = str(e)
    if reminder_time is None:
        msg = f"I could not understand the time '{when}'."
        if error:
            msg += f" Error: {error}"
        return msg + "Please try something like 'in 10 minutes' or 'tomorrow at 10 AM'."
    now = datetime.now()
    if reminder_time < now:
       reminder_time = now + timedelta(minutes=5)
    reminders_file = "reminders.json"
    reminders = []
    if os.path.exists(reminders_file):
        try:
            with open(reminders_file, "r", encoding="utf-8") as file:
                reminders = json.load(file)
        except Exception:
            reminders = []

    existing_ids = [r.get("id", 0) for r in reminders if isinstance(r, dict)]
    next_id = (max(existing_ids) if existing_ids else 0) + 1

    new_reminder = {
        "id": next_id,
        "text": reminder_text,
        "time": reminder_time.isoformat(),
        "active": True,
    }
    reminders.append(new_reminder)
    try:
        with open(reminders_file, "w", encoding="utf-8") as file:
            json.dump(reminders, file, indent=4)
        #return f"Reminder set for {reminder_time.strftime('%Y-%m-%d %H:%M:%S')}: {reminder_text}"
    except Exception as e:
        return f"Sory, I could not save the reminder: {e}"
    try:
        import main
        if hasattr(main, "load_existing_reminders"):
            main.load_existing_reminders()
    except Exception as e:
         print(f"Warning: Could not reschedule reminders from set_reminder_tool: {e}")
    human_time = reminder_time.strftime("%I:%M %p on %B %d, %Y")
    return f"Okay, I'll remind you at {human_time}: {reminder_text}"

def list_reminders(parameters):
    reminders_file = "reminders.json"
    if not os.path.exists(reminders_file):
        return "You have no reminders set."
    try:   
        with open(reminders_file, "r", encoding="utf-8") as file:
            reminders = json.load(file)
    except Exception as e:
        return f"Sorry, I couldn't read your reminders: {e}"
    
    reminders = [r for r in reminders if r.get("active", True)]
    if not reminders:
        return "You have no reminders set."
    
    try:
        reminders.sort(key=lambda r: datetime.fromisoformat(r["time"]))
    except Exception:
        pass
    lines = []
    for r in reminders:
        text = r.get("text", "No description")
        time_str = r.get("time", "No time set")
        #active = r.get("active", True)
        try: 
            dt = datetime.fromisoformat(time_str)
            friendly_time = dt.strftime("%I:%M %p on %B %d, %Y")
        except Exception:
            friendly_time = time_str or "Invalid time format"
        #status = "active" if active else "inactive"
        lines.append(f"- {text} at {friendly_time}")
    if len(reminders) == 1:
        prefix = "You have one active reminder:\n"
    else:
        prefix = f"You have {len(reminders)} active reminders:\n"

    return prefix + "\n".join(lines)
    

client_tools = ClientTools()
client_tools.register("searchWeb", search_web)
client_tools.register("saveToTxt", save_to_txt)
client_tools.register("getCurrentTime", get_current_time)
client_tools.register("getRegionInfo", get_region_info)
client_tools.register("getWeatherInfo",get_weather_info)
client_tools.register("getDateInfo", get_date_info)
client_tools.register("setReminder", set_reminder)
client_tools.register("listReminders", list_reminders)