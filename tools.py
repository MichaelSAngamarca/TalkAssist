import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from elevenlabs.conversational_ai.conversation import ClientTools
from langchain_community.tools import DuckDuckGoSearchRun
from connectivity_checker import check_internet_connectivity, safe_api_call
import time
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

client_tools = ClientTools()
client_tools.register("searchWeb", search_web)
client_tools.register("saveToTxt", save_to_txt)
client_tools.register("getCurrentTime", get_current_time)
client_tools.register("getRegionInfo", get_region_info)
client_tools.register("getWeatherInfo",get_weather_info)
client_tools.register("getDateInfo", get_date_info)