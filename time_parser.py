"""
A module for parsing and manipulating time-related data.
Includes functions for converting time formats, calculating durations, and scheduling events.
"""

import re
from datetime import datetime, timedelta

class TimeParser:
    """
    This will set up the parser.
    we have a dictionary of days to numbers. including their abbreviations. helps with parsing days of the week.
    """
    def __init__(self):
        self.days_of_week = {
            "monday": 0, "mon": 0,
            "tuesday": 1, "tue": 1,"tues": 1,
            "wednesday": 2, "wed": 2,
            "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
            "friday": 4, "fri": 4,
            "saturday": 5, "sat": 5,
            "sunday": 6, "sun": 6
        }

    """
     This will parse a time string and return a datetime object.
     It can handle formats like "3 PM", "15:30", "next Monday at 10 AM", etc.
     It takes spoken text and figures out when the reminder should happen
     """
    def parse_time(self, text):
        text = text.lower().strip()
        text = self._convert_words_to_numbers(text)
        now = datetime.now()
        daypart_defaults = {"morning": "9 am", "afternoon": "3 pm", "evening": "7 pm", "night": "9 pm"}
        text = re.sub(r'\btonight\b', 'today night', text)
        for part, clock in daypart_defaults.items():
            text = re.sub(rf'\b(tomorrow|today|next\s+\w+)\s+{part}\b', rf'\1 at {clock}', text)
            text = re.sub(rf'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+{part}\b', rf'\1 at {clock}', text)
        for part, clock in daypart_defaults.items():
            if not re.search(rf'\b(tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+(at\s+)?\d+\s*(am|pm)', text):
                text = re.sub(rf'\b{part}\b', f'today at {clock}', text)
        if 'next week' in text:
            base = (now + timedelta(days=7)).replace(hour=9, minute=0, second=0, microsecond=0)
            if (not re.search(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', text) and not self._extract_time(text)):
                base = (now + timedelta(days=7)).replace(hour=9, minute=0, second=0, microsecond=0)
                return base, True, None

        # pattern 1 : in X minutes/hours/days
        pattern = r'in (\d+) (minute|minutes|min|mins|hour|hours|hr|hrs|day|days)'
        match = re.search(pattern, text)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            if 'minute' in unit or 'min' in unit:
                return now + timedelta(minutes = value), True, None
            elif 'hour' in unit or 'hr' in unit:
                return now + timedelta(hours = value), True, None
            elif 'day' in unit:
                return now + timedelta(days = value), True, None

        # pattern 2 : processing "tomorrow" or "tomorrow at x "
        if 'tomorrow' in text:
            base_time = now + timedelta(days=1)
            #checking if a specific time is mentionned, if no time is mentioned set 9 am tomorrow by default
            time_match = self._extract_time(text)
            if time_match:
                try:
                    target_time = datetime.combine(base_time.date(), time_match)
                    return target_time, True, None
                except:
                    return None, False, "Invalid time format"
            else:
                return base_time.replace(hour=9, minute=0, second=0, microsecond=0), True, None

        # pattern 3 : " today at x"
        if 'today' in text:
            time_match = self._extract_time(text)
            if time_match:
                try:
                    target_time = datetime.combine(now.date(), time_match)
                    if target_time <= now:
                        return None, False, "that time has already passed today"
                    return target_time, True, None
                except:
                    return None, False, "Invalid time format"
        # pattern 4 : week days like "friday", "next monday"
        for day_name, day_num in self.days_of_week.items():
            if day_name in text:
                days_ahead = day_num - now.weekday()
                # if the day is already passed, select the day of next week
                if days_ahead < 0:
                    days_ahead += 7

                # handling next day, will go straight to next week
                if 'next' in text:
                    if days_ahead < 7:
                        days_ahead += 7
                target_date = now + timedelta(days=days_ahead)
                time_match = self._extract_time(text)
                if time_match:
                    try:
                        target_time = datetime.combine(target_date.date(), time_match)
                        return target_time, True, None
                    except:
                        return None, False, "Invalid time format"
                else:
                    return target_date.replace(hour=9, minute=0, second=0, microsecond=0), True, None
        # pattern 5 : for time like "2pm" "17:30"
        time_match = self._extract_time(text)
        if time_match:
            try:
                target_time = datetime.combine(now.date(), time_match)
                if target_time <= now:
                    #if the time has already passed, shedule for tomorrow
                    target_time = datetime.combine((now + timedelta(days=1)).date(), time_match)
                return target_time, True, None
            except:
                return None, False, "Invalid time format"
            
        return None, False, "Could not understand the time. Try formmats like '2 hours', 'tomorrow at 1pm', or 'monday at 1pm'"

    def _convert_words_to_numbers(self, text):
        # Convert word numbers to digit
        word_to_num = {
            'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
            'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
            'eleven': '11', 'twelve': '12', 'fifteen': '15', 'twenty': '20',
            'thirty': '30', 'forty': '40', 'fifty': '50', 'sixty': '60'
        }
    
        for word, num in word_to_num.items():
            text = text.replace(word, num)
        
        return text
    
    # get the time form the text, then return datetime.time object or none "4pm", "16:30", "4:30"
    def _extract_time(self, text):
        # pattern 1: "10:30am" , "10.30 pm" 
        pattern2 = r'(\d{1,2})[:.](\d{2})\s*(am|pm|a\.m\.|p\.m\.)'
        match = re.search(pattern2, text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            meridien = match.group(3).lower()
            if 'pm' in meridien or 'p.m' in meridien:
                if hour != 12:
                    hour += 12
            elif 'am' in meridien or 'a.m' in meridien:
                if hour == 12:
                    hour = 0
            if 0 <= hour < 24 and 0 <= minute < 60:
                return datetime.strptime(f"{hour}:{minute}", "%H:%M").time()
        # pattern 1: "10am", "10 am", "10pm"
        pattern1= r'(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)'
        match = re.search(pattern1, text)
        if match:
            hour = int(match.group(1))
            meridien = match.group(2).lower()
            if 'pm' in meridien or 'p.m' in meridien:
                if hour != 12:
                    hour += 12
            elif 'am' in meridien or 'a.m' in meridien:
                if hour == 12:
                    hour = 0
            if 0 <= hour < 24:
                return datetime.strptime(f"{hour}:00", "%H:%M").time()
            
        pattern_b = r'(\d{1,2})\s+(\d{2})\s*(am|pm|a\.m\.|p\.m\.)'
        match = re.search(pattern_b, text)
        if match:
            hour = int(match.group(1)); minute = int(match.group(2))
            meridien = match.group(3).lower()
            if 'pm' in meridien and hour != 12: hour += 12
            if 'am' in meridien and hour == 12: hour = 0
            if 0 <= hour < 24 and 0 <= minute < 60:
                return datetime.strptime(f"{hour}:{minute}", "%H:%M").time()
            
        pattern_c = r'\b(\d{3,4})\s*(am|pm|a\.m\.|p\.m\.)\b'
        match = re.search(pattern_c, text)
        if match:
            raw = int(match.group(1)); hour, minute = raw // 100, raw % 100
            meridien = match.group(2).lower()
            if 'pm' in meridien and hour != 12: hour += 12
            if 'am' in meridien and hour == 12: hour = 0
            if 0 <= hour < 24 and 0 <= minute < 60:
                return datetime.strptime(f"{hour}:{minute}", "%H:%M").time()
            

        # pattern 3: for 24 hour format: 16:45, 8:00
        pattern3 = r'(\d{1,2})[:.](\d{2})(?!\s*[ap]\.?m\.?)'
        match = re.search(pattern3, text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            if 0 <= hour < 24 and 0 <= minute < 60:
                return datetime.strptime(f"{hour}:{minute}", "%H:%M").time()
        return None
    
    def format_time_human(self, dt):
        now = datetime.now()
        
        # If today
        if dt.date() == now.date():
            return f"today at {dt.strftime('%I:%M %p')}"
        
        # If tomorrow
        if dt.date() == (now + timedelta(days=1)).date():
            return f"tomorrow at {dt.strftime('%I:%M %p')}"
        
        # If within a week
        days_until = (dt.date() - now.date()).days
        if 0 < days_until <= 7:
            return f"{dt.strftime('%A')} at {dt.strftime('%I:%M %p')}"
        
        # Otherwise full date
        return dt.strftime('%A, %B %d at %I:%M %p')
   

        