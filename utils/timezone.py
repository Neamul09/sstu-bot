from datetime import datetime
import pytz
from config import Config

def get_now():
    tz = pytz.timezone(Config.TZ)
    return datetime.now(tz)

def format_time(dt):
    return dt.strftime("%I:%M %p")

def get_day_of_week():
    return get_now().weekday()

def parse_time(time_str: str) -> str:
    """
    Parses a time string in various AM/PM or 24h formats and returns a valid HH:MM (24h) string.
    Raises ValueError if invalid.
    """
    time_str = time_str.strip().lower()
    
    formats = [
        "%I:%M %p", "%I:%M%p", "%I %p", "%I%p",
        "%H:%M", "%H"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return dt.strftime("%H:%M")
        except ValueError:
            continue
            
    raise ValueError(f"Invalid time format: {time_str}")
