from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from database import Database
from config import Config
from utils.timezone import get_now, get_day_of_week
from utils.helpers import build_menu
import datetime
import pytz

# States for Rescheduling
CHOOSE_ACTION, NEW_TIME, NEW_ROOM = range(3)

async def manage_classes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = Database.get_user(user_id)
    
    if not user or user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        await update.message.reply_text("❌ Only CRs or Teachers can manage class routine.")
        return ConversationHandler.END

    class_id = f"{user['department']}_{user['semester']}"
    day = get_day_of_week()
    current_date = get_now().strftime("%Y-%m-%d")
    
    slots = Database.get_timetable(class_id, day)
    
    if not slots:
        await update.message.reply_text("🌴 No classes scheduled for today to manage.")
        return ConversationHandler.END

    text = f"⚙️ *Today's Class Management*\n_Date: {current_date}_\n\nSelect a class slot to manage:"
    
    buttons = []
    for slot in slots:
        label = f"{slot['subject']} ({slot['start_time'][:5]})"
        buttons.append(InlineKeyboardButton(label, callback_data=f"mng_{slot['id']}"))
            
    reply_markup = build_menu(buttons, n_cols=1)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    return CHOOSE_ACTION

async def handle_slot_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    slot_id = query.data.split("_")[1]
    context.user_data["mng_slot_id"] = slot_id
    
    # Fetch slot info
    res = Database.supabase.table("timetable").select("*").eq("id", slot_id).execute()
    slot = res.data[0]
    
    text = f"🛠 *Manage Specific Class*\nSubject: *{slot['subject']}*\nTime: {slot['start_time'][:5]} - {slot['end_time'][:5]}\n\nWhat would you like to do for *Today*?"
    
    kb = [
        [InlineKeyboardButton("🚫 Cancel for Today", callback_data=f"cxl_{slot_id}")],
        [InlineKeyboardButton("🕒 Reschedule for Today", callback_data=f"resched_{slot_id}")],
        [InlineKeyboardButton("❌ Cancel Action", callback_data="cancel_mng")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return CHOOSE_ACTION

async def handle_cancellation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    slot_id = query.data.split("_")[1]
    current_date = get_now().strftime("%Y-%m-%d")
    user = Database.get_user(query.from_user.id)
    
    Database.cancel_class(slot_id, current_date, reason="Emergency change")
    
    # Fetch slot info for broadcast
    res = Database.supabase.table("timetable").select("*").eq("id", slot_id).execute()
    slot = res.data[0]
    dept, sem = slot['class_id'].split("_")
    
    alert_msg = f"🚨 *CLASS CANCELLED* 🚨\n\nSubject: *{slot['subject']}*\nTime: {slot['start_time'][:5]}\nDate: {current_date}\n\n_Alerted by your representative._"
    
    class_users = Database.supabase.table("users").select("id").eq("department", dept).eq("semester", int(sem)).neq("id", user["id"]).execute().data
    for u in class_users:
        try: await context.bot.send_message(u["id"], alert_msg, parse_mode="Markdown")
        except: pass
            
    await query.edit_message_text(f"✅ Class *{slot['subject']}* cancelled and students alerted.", parse_mode="Markdown")
    return ConversationHandler.END

async def start_rescheduling(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("🕒 *Rescheduling*\n\nPlease type the *New Time* (Format HH:MM, e.g., 14:30):")
    return NEW_TIME

async def get_reschedule_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_time = update.message.text
    try:
        datetime.datetime.strptime(new_time, "%H:%M")
        context.user_data["mng_new_time"] = new_time
        await update.message.reply_text("📍 *Great!* Now optionally type the *New Room*, or type 'skip':")
        return NEW_ROOM
    except:
        await update.message.reply_text("⚠️ Invalid time. Use HH:MM format.")
        return NEW_TIME

async def finish_rescheduling(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_room = update.message.text if update.message.text.lower() != "skip" else None
    slot_id = context.user_data["mng_slot_id"]
    new_time = context.user_data["mng_new_time"]
    current_date = get_now().strftime("%Y-%m-%d")
    user = Database.get_user(update.effective_user.id)
    
    # Logic: Simply add an override in the new table (Implementation logic would check this during view)
    Database.add_class_override({
        "slot_id": slot_id,
        "override_date": current_date,
        "new_start_time": new_time,
        "new_room": new_room
    })
    
    res = Database.supabase.table("timetable").select("*").eq("id", slot_id).execute()
    slot = res.data[0]
    dept, sem = slot['class_id'].split("_")
    
    alert_msg = f"🕒 *CLASS RESCHEDULED* 🕒\n\nSubject: *{slot['subject']}*\n*NEW Time*: {new_time}\n*NEW Room*: {new_room or 'N/A'}\nDate: {current_date}"
    
    class_users = Database.supabase.table("users").select("id").eq("department", dept).eq("semester", int(sem)).neq("id", user["id"]).execute().data
    for u in class_users:
        try: await context.bot.send_message(u["id"], alert_msg, parse_mode="Markdown")
        except: pass

    await update.message.reply_text("✅ Class rescheduled and students alerted!")
    return ConversationHandler.END

async def cancel_mng(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Action Cancelled.")
    else:
        await update.message.reply_text("❌ Action Cancelled.")
    return ConversationHandler.END

manage_class_handler = ConversationHandler(
    entry_points=[CommandHandler("manage_class", manage_classes_cmd)],
    states={
        CHOOSE_ACTION: [
            CallbackQueryHandler(handle_slot_selection, pattern="^mng_"),
            CallbackQueryHandler(handle_cancellation_callback, pattern="^cxl_"),
            CallbackQueryHandler(start_rescheduling, pattern="^resched_"),
            CallbackQueryHandler(cancel_mng, pattern="^cancel_mng$")
        ],
        NEW_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_reschedule_time)],
        NEW_ROOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_rescheduling)]
    },
    fallbacks=[CommandHandler("cancel", cancel_mng)]
)
