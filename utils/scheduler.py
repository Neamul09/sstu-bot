from telegram.ext import ContextTypes
from database import Database, supabase
from utils.timezone import get_now
import datetime
import logging
import pytz
from config import Config

logger = logging.getLogger(__name__)

async def check_class_reminders(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    now = get_now()
    check_time = (now + datetime.timedelta(minutes=60)).strftime("%H:%M")
    day = now.weekday()
    
    # Query all slots starting at check_time (approx)
    slots = supabase.table("timetable").select("*").eq("day_of_week", day).eq("start_time", check_time).execute().data
    
    current_date_str = now.strftime("%Y-%m-%d")

    for slot in slots:
        # Check if cancelled
        if Database.is_class_cancelled(slot["id"], current_date_str):
            continue
            
        class_id = slot["class_id"]
        # Find all users in this class (Dept_Sem)
        dept, sem = class_id.split("_")
        users = supabase.table("users").select("id, pref_class_reminders").eq("department", dept).eq("semester", int(sem)).execute().data
        
        for user in users:
            if not user.get("pref_class_reminders", True):
                continue
            try:
                await bot.send_message(
                    chat_id=user["id"],
                    text=f"⏰ *Reminder*: Class for *{slot['subject']}* starts in 60 minutes!"
                         f"\n🕒 Time: {slot['start_time']} - {slot['end_time']}"
                         + (f"\n📍 Room: {slot['room']}" if slot['room'] else ""),
                    parse_mode="Markdown"
                )
            except Exception:
                pass

async def check_deadline_reminders(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Check 24h reminders
    remind_24h = now + datetime.timedelta(hours=24)
    # Check 1h reminders
    remind_1h = now + datetime.timedelta(hours=1)
    
    # Simple logic: Fetch upcoming deadlines that haven't been reminded
    deadlines = supabase.table("deadlines").select("*").filter("due_datetime", "lt", (remind_24h + datetime.timedelta(minutes=5)).isoformat()).execute().data
    
    for d in deadlines:
        due = datetime.datetime.fromisoformat(d["due_datetime"]).replace(tzinfo=pytz.UTC)
        time_diff = due - now
        
        # 24h reminder
        if datetime.timedelta(hours=23, minutes=50) <= time_diff <= datetime.timedelta(hours=24, minutes=10) and not d["reminded_24h"]:
            await send_deadline_push(bot, d, "24 hours")
            supabase.table("deadlines").update({"reminded_24h": True}).eq("id", d["id"]).execute()
            
        # 1h reminder
        elif datetime.timedelta(minutes=50) <= time_diff <= datetime.timedelta(hours=1, minutes=10) and not d["reminded_1h"]:
            await send_deadline_push(bot, d, "1 hour")
            supabase.table("deadlines").update({"reminded_1h": True}).eq("id", d["id"]).execute()

async def send_deadline_push(bot, deadline, time_left):
    class_id = deadline["class_id"]
    dept, sem = class_id.split("_")
    users = supabase.table("users").select("id, pref_deadline_reminders").eq("department", dept).eq("semester", int(sem)).execute().data
    
    for user in users:
        if not user.get("pref_deadline_reminders", True):
            continue
        try:
            await bot.send_message(
                chat_id=user["id"],
                text=f"🚨 *Deadline Alert*: '{deadline['title']}' is due in *{time_left}*!",
                parse_mode="Markdown"
            )
        except Exception:
            pass

async def daily_digest(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    now = get_now()
    tomorrow = now + datetime.timedelta(days=1)
    
    # Send digest to everyone
    all_users = supabase.table("users").select("*").execute().data
    
    for user in all_users:
        if not user.get("pref_daily_digest", True):
            continue
            
        class_id = f"{user['department']}_{user['semester']}"
        
        # 1. Tomorrow's Timetable
        tomorrow_day_idx = tomorrow.weekday()
        slots = Database.get_timetable(class_id, tomorrow_day_idx)
        
        # 2. Upcoming deadlines in next 7 days
        next_week = (now + datetime.timedelta(days=7)).isoformat()
        deadlines = supabase.table("deadlines").select("*").eq("class_id", class_id).gt("due_datetime", now.astimezone(pytz.UTC).isoformat()).lt("due_datetime", next_week).execute().data
        
        text = f"📬 *Daily Academic Digest*\n_For {tomorrow.strftime('%d %b, %Y')}_\n\n"
        
        text += "📅 *Tomorrow's Classes:*\n"
        if not slots:
            text += "   🌴 No classes scheduled.\n"
        else:
            for s in slots:
                if Database.is_class_cancelled(s["id"], tomorrow.strftime("%Y-%m-%d")):
                    text += f"   🚫 ~{s['subject']}~ (Cancelled)\n"
                else:
                    text += f"   🔹 {s['subject']} ({s['start_time'][:5]})\n"
                    
        text += "\n🚨 *Upcoming Deadlines (Next 7 Days):*\n"
        if not deadlines:
            text += "   🎉 Nothing critically due soon!\n"
        else:
            for d in deadlines:
                due = datetime.datetime.fromisoformat(d["due_datetime"]).astimezone(pytz.timezone(Config.TZ))
                text += f"   📌 {d['title']} - {due.strftime('%A, %I:%M %p')}\n"
                
        try:
            await bot.send_message(user["id"], text, parse_mode="Markdown")
        except:
            pass

async def reset_weekly_overrides(context: ContextTypes.DEFAULT_TYPE):
    """
    Runs every Friday at 23:59 local time.
    Clears all expired cancelled_classes and class_overrides rows so that
    per-week exceptions do not carry over into the next week.
    """
    now = get_now()
    today_str = now.strftime("%Y-%m-%d")
    try:
        # Delete cancellations on or before today
        del_cancelled = supabase.table("cancelled_classes") \
            .delete() \
            .lte("cancel_date", today_str) \
            .execute()
        # Delete overrides on or before today
        del_overrides = supabase.table("class_overrides") \
            .delete() \
            .lte("override_date", today_str) \
            .execute()
        logger.info(
            "[Weekly Reset] Cleared expired overrides for week ending %s. "
            "cancelled_classes deleted: %d, class_overrides deleted: %d",
            today_str,
            len(del_cancelled.data) if del_cancelled.data else 0,
            len(del_overrides.data) if del_overrides.data else 0,
        )
    except Exception as e:
        logger.error("[Weekly Reset] Failed to clear overrides: %s", e)

async def dispatch_scheduled_notifications(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()
    
    # Get all pending notifications where scheduled_time <= now
    pending = Database.get_pending_notifications(now_iso)
    
    if not pending:
        return
        
    from handlers.timetable import get_routine_text
    
    for notif in pending:
        class_id = notif["class_id"]
        dept, sem = class_id.split("_")
        target_date = notif["target_date"]
        
        routine_text = get_routine_text(class_id, dept, int(sem), target_date, "STUDENT")
        msg = f"📢 *CLASS ROUTINE UPDATE (Scheduled)*\n\n{routine_text}"
        
        users = supabase.table("users").select("id").eq("department", dept).eq("semester", int(sem)).execute().data
        for user in users:
            try:
                await bot.send_message(chat_id=user["id"], text=msg, parse_mode="Markdown")
            except Exception:
                pass
                
        # Mark as sent
        Database.mark_notification_sent(notif["id"])

def start_scheduler(application):
    job_queue = application.job_queue
    # PTB's JobQueue run_repeating takes interval in seconds
    job_queue.run_repeating(check_class_reminders, interval=60, first=10)
    job_queue.run_repeating(check_deadline_reminders, interval=300, first=10)
    job_queue.run_repeating(dispatch_scheduled_notifications, interval=60, first=15)

    local_tz = pytz.timezone(Config.TZ)

    # Run Daily Digest at 20:00 (8 PM) Local Time
    target_time = datetime.time(hour=20, minute=0, tzinfo=local_tz)
    job_queue.run_daily(daily_digest, time=target_time)

    # Run Weekly Routine Reset every Friday at 23:59 local time
    # weekday: 0=Mon … 4=Fri … 6=Sun  (PTB uses the same convention)
    reset_time = datetime.time(hour=23, minute=59, tzinfo=local_tz)
    job_queue.run_daily(
        reset_weekly_overrides,
        time=reset_time,
        days=(4,),   # Friday only
    )
    logger.info("[Scheduler] Weekly routine reset job registered for Friday 23:59 %s", Config.TZ)
