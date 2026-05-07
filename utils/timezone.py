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

def get_date_for_day_of_week(target_day_idx: int) -> str:
    """
    Returns the YYYY-MM-DD date string for a given day of the week 
    in the current week (Monday-based).
    """
    from datetime import timedelta
    now = get_now()
    current_day_idx = now.weekday()
    diff = target_day_idx - current_day_idx
    target_date = now + timedelta(days=diff)
    return target_date.strftime("%Y-%m-%d")

def format_date_with_ordinal(date_str: str) -> str:
    """
    Converts YYYY-MM-DD to '11th May, 2026 - Monday' format.
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day = dt.day
    
    if 11 <= (day % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(day % 10, 4)]
        
    return f"{day}{suffix} {dt.strftime('%B, %Y - %A')}"


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
