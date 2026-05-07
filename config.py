import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    TZ = os.getenv("TZ", "Asia/Dhaka")

    # Bot Specifics
    DEPARTMENTS = [
        "Computer Science & Engineering",
        "Chemistry",
        "Physics",
        "Mathematics"
    ]
    
    # Generate numbers 1-8
    SEMESTERS = [str(i) for i in range(1, 9)]
    
    # Roles
    ROLE_STUDENT = "STUDENT"
    ROLE_CR = "CR"
    ROLE_TEACHER = "TEACHER"
    ROLE_ADMIN = "ADMIN"
