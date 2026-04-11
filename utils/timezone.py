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
