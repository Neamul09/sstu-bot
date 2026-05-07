from telegram import Update, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from telegram import InlineKeyboardMarkup
from database import Database
from utils.timezone import get_now, format_time, get_day_of_week, parse_time, get_date_for_day_of_week, format_date_with_ordinal
from utils.helpers import build_menu, get_cancel_button
from utils.course_loader import get_courses
from config import Config
from telegram.error import BadRequest
from utils.i18n import t
import datetime

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# States for Adding Timetable
SUBJ_CHOICE, SUBJ, DAY, START, END, ROOM = range(6)


def get_routine_text(class_id: str, dept: str, sem: int, target_date: str, user_role: str) -> str:
    target_dt = datetime.datetime.strptime(target_date, "%Y-%m-%d")
    day = target_dt.weekday()
    day_name = DAYS[day]
    
    slots = Database.get_timetable(class_id, day)
    
    formatted_date = format_date_with_ordinal(target_date)
    text = f"📅 *Timetable for {formatted_date}*\n_Class: {dept} Semester {sem}_\n\n"
    
    if not slots:
        text += "🌴 No classes scheduled for this day."
    else:
        for slot in slots:
            is_cancelled = Database.is_class_cancelled(slot['id'], target_date)
            overrides = Database.get_class_overrides(slot['id'], target_date)
            override = overrides[0] if overrides else None

            start_formatted = datetime.datetime.strptime(slot['start_time'], "%H:%M:%S").strftime("%I:%M %p")
            end_formatted = datetime.datetime.strptime(slot['end_time'], "%H:%M:%S").strftime("%I:%M %p")

            if is_cancelled:
                text += f"❌ ~~*{slot['subject']}*~~ [CANCELLED]\n"
                text += f"   🕒 {start_formatted} - {end_formatted}\n"
            elif override:
                override_start = datetime.datetime.strptime(override['new_start_time'], "%H:%M:%S").strftime("%I:%M %p")
                text += f"🕒 *{slot['subject']}* [RESCHEDULED]\n"
                text += f"   🕒 *{override_start}* (Originally {start_formatted})\n"
                if override.get('new_room'):
                    text += f"   📍 Room: {override['new_room']}\n"
                else:
                    text += f"   📍 Room: {slot['room']}\n"
            else:
                text += f"🔹 *{slot['subject']}*\n"
                text += f"   🕒 {start_formatted} - {end_formatted}\n"
                if slot['room']:
                    text += f"   📍 Room: {slot['room']}\n"
            
            if user_role in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
                text += f"   `[ID: {slot['id'][:4]}]`"
            text += "\n\n"
            
    return text, slots

async def view_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = Database.get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ You are not registered yet. Use /start")
        return

    lang = user.get("language", "en")
    class_id = f"{user['department']}_{user['semester']}"
    
    query = update.callback_query
    day = get_day_of_week()
    
    if query:
        await query.answer()
        if query.data.startswith("ttt_"):
            try:
                day = int(query.data.split("_")[1])
            except (ValueError, IndexError):
                pass
    
    target_date = get_date_for_day_of_week(day)
    text, slots = get_routine_text(class_id, user['department'], user['semester'], target_date, user["role"])
    
    # Build inline keyboard to switch days
    buttons = [
        InlineKeyboardButton("Prev Day", callback_data=f"ttt_{(day-1)%7}"),
        InlineKeyboardButton("Today", callback_data=f"ttt_{get_day_of_week()}"),
        InlineKeyboardButton("Next Day", callback_data=f"ttt_{(day+1)%7}")
    ]
    # If CR/TEACHER, add management buttons
    footer = []
    
    # Always add the "Official Routine View" button if available
    footer.append(InlineKeyboardButton(t("btn_routine_img", lang), callback_data="view_routine_img"))

    if user["role"] in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        footer.append(InlineKeyboardButton("➕ Add New Class", callback_data="add_slot_trigger"))
        footer.append(InlineKeyboardButton(t("btn_upload_routine", lang), callback_data="upload_routine_trigger"))
        # Add delete buttons for today's slots
        if slots:
            for slot in slots:
                footer.append(InlineKeyboardButton(f"🗑️ Del {slot['subject'][:10]}", callback_data=f"delslot_{slot['id']}"))
        
    reply_markup = build_menu(buttons, n_cols=3, footer_buttons=footer)

    if query:
        try:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        except BadRequest:
            pass # Message perfectly matches, nothing to edit
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

# --- Add Slot Conversation ---

async def add_slot_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        user_id = query.from_user.id
    else:
        user_id = update.effective_user.id
        
    user = Database.get_user(user_id)
    if not user or user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        msg = "❌ Only CRs or Teachers can add slots."
        if query: await query.edit_message_text(msg)
        else: await update.message.reply_text(msg)
        return ConversationHandler.END

    semester = user.get("semester", 0)
    courses = get_courses(semester)

    if courses:
        # Build course picker buttons (2 per row)
        course_buttons = [
            InlineKeyboardButton(c[:30], callback_data=f"course_{i}")
            for i, c in enumerate(courses)
        ]
        footer = [
            InlineKeyboardButton("✏️ Enter Manually", callback_data="course_manual"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"),
        ]
        reply_markup = build_menu(course_buttons, n_cols=2, footer_buttons=footer)
        text = (
            f"📚 *Add New Class Slot*\n"
            f"_Semester {semester} courses — tap to select or enter manually:_"
        )
    else:
        # No courses found for this semester — fall back to manual directly
        footer = [InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")]
        reply_markup = build_menu(footer, n_cols=1)
        text = "📝 *Add New Class Slot*\n\nPlease type the *Subject Name* (e.g., Data Structures):"

    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    # If no courses, go straight to manual text entry
    return SUBJ_CHOICE if courses else SUBJ


async def add_slot_subj_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the course picker selection or the manual input choice."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_action":
        await query.edit_message_text("❌ Action Cancelled.")
        return ConversationHandler.END

    if query.data == "course_manual":
        # User wants to type the subject manually
        await query.edit_message_text(
            "📝 Please type the *Subject Name* (e.g., Data Structures):",
            parse_mode="Markdown"
        )
        return SUBJ  # Go to existing text-based step

    # Otherwise it's a course selection: "course_<index>"
    user_id = query.from_user.id
    user = Database.get_user(user_id)
    semester = user.get("semester", 0)
    courses = get_courses(semester)

    try:
        idx = int(query.data.split("_")[1])
        chosen = courses[idx]
    except (ValueError, IndexError):
        await query.edit_message_text("⚠️ Invalid selection. Please try again.")
        return ConversationHandler.END

    context.user_data["tmp_slot"] = {"subject": chosen}

    # Go straight to day selection
    buttons = [InlineKeyboardButton(day[:3], callback_data=f"addday_{i}") for i, day in enumerate(DAYS)]
    reply_markup = build_menu(buttons, n_cols=4, footer_buttons=get_cancel_button())

    await query.edit_message_text(
        f"Subject: *{chosen}*\n\nSelect the day of the week:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return DAY


async def add_slot_subj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tmp_slot"] = {"subject": update.message.text}
    
    buttons = [InlineKeyboardButton(day[:3], callback_data=f"addday_{i}") for i, day in enumerate(DAYS)]
    reply_markup = build_menu(buttons, n_cols=4, footer_buttons=get_cancel_button())
    
    await update.message.reply_text(
        f"Subject: *{update.message.text}*\n\nSelect the day of the week:", 
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return DAY

async def add_slot_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_action":
        await query.edit_message_text("❌ Action Cancelled.")
        return ConversationHandler.END
        
    day_idx = int(query.data.split("_")[1])
    context.user_data["tmp_slot"]["day_of_week"] = day_idx
    
    day_name = DAYS[day_idx]
    
    await query.edit_message_text(
        text=f"Day: *{day_name}*\n\nPlease type the *Start Time* (e.g., 09:30 or 2:30 PM):",
        parse_mode="Markdown"
    )
    return START

async def add_slot_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "/cancel":
        await update.message.reply_text("❌ Action Cancelled.")
        return ConversationHandler.END
        
    try:
        parsed_time = parse_time(update.message.text)
        context.user_data["tmp_slot"]["start_time"] = parsed_time
        
        await update.message.reply_text(
            f"Start Time: *{parsed_time}*\n\nPlease type the *End Time* (e.g., 14:00 or 4:00 PM):",
            parse_mode="Markdown"
        )
        return END
    except ValueError:
        await update.message.reply_text("⚠️ Invalid time format. Please use something like *14:00* or *2:00 PM*.\nOr type /cancel.")
        return START

async def add_slot_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "/cancel":
        await update.message.reply_text("❌ Action Cancelled.")
        return ConversationHandler.END
        
    try:
        parsed_time = parse_time(update.message.text)
        context.user_data["tmp_slot"]["end_time"] = parsed_time
        
        # Room selection can be None
        buttons = [InlineKeyboardButton("Skip / No Room", callback_data="skip_room")]
        reply_markup = build_menu(buttons, n_cols=1)
        
        await update.message.reply_text(
            f"End Time: *{parsed_time}*\n\nPlease type the *Room Number/Name*:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return ROOM
    except ValueError:
        await update.message.reply_text("⚠️ Invalid time format. Please use something like *15:30* or *3:30 PM*.\nOr type /cancel.")
        return END

async def process_slot_saving(user_id, slot_data):
    user = Database.get_user(user_id)
    class_id = f"{user['department']}_{user['semester']}"
    slot_data["class_id"] = class_id
    Database.add_timetable_slot(slot_data)

async def add_slot_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This could be a text message OR a callback query (skip)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        room = None
        user_id = query.from_user.id
        msg_obj = query.message
    else:
        if update.message.text.lower() == "/cancel":
            await update.message.reply_text("❌ Action Cancelled.")
            return ConversationHandler.END
        room = update.message.text
        user_id = update.effective_user.id
        msg_obj = update.message

    context.user_data["tmp_slot"]["room"] = room
    slot_data = context.user_data["tmp_slot"]
    
    await process_slot_saving(user_id, slot_data)
    
    # Notification Prompt
    target_date = get_date_for_day_of_week(slot_data['day_of_week'])
    keyboard = [
        [InlineKeyboardButton("📤 Send Instant Alert", callback_data=f"ntfy_inst_{target_date}")],
        [InlineKeyboardButton("🕒 Schedule Notification", callback_data=f"ntfy_sch_{target_date}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    success_text = f"✅ Success! *{slot_data['subject']}* mapped to {DAYS[slot_data['day_of_week']]}.\n\nWould you like to notify the class about the updated routine for {target_date}?"
    
    if update.callback_query:
        await msg_obj.edit_text(success_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await msg_obj.reply_text(success_text, reply_markup=reply_markup, parse_mode="Markdown")
        
    return ConversationHandler.END

# Common Cancel Handler
async def cancel_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Action Cancelled.")
    else:
        await update.message.reply_text("❌ Action Cancelled.")
    return ConversationHandler.END

# --- Routine Image Management ---

async def view_routine_img(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = Database.get_user(query.from_user.id)
    class_id = f"{user['department']}_{user['semester']}"
    lang = user.get("language", "en")
    
    config = Database.get_class_config(class_id)
    if not config or not config.get("routine_image_id"):
        msg = "❌ No routine image has been uploaded for this class yet."
        if user["role"] in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
            msg += "\n\nUse the '📤 Upload Routine' button to add one."
        await query.message.reply_text(msg)
        return
        
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=config["routine_image_id"],
        caption=f"🖼️ *Official Routine - {class_id}*",
        parse_mode="Markdown"
    )

# States for Routine Upload
UPLOAD_IMG = range(10, 11)

async def upload_routine_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = Database.get_user(query.from_user.id)
    lang = user.get("language", "en")
    
    if user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        await query.edit_message_text("❌ Unauthorized.")
        return ConversationHandler.END

    await query.edit_message_text(t("ask_routine_img", lang), parse_mode="Markdown")
    return UPLOAD_IMG

async def handle_routine_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("⚠️ Please send a *Photo* of the routine.")
        return UPLOAD_IMG
        
    user = Database.get_user(update.effective_user.id)
    class_id = f"{user['department']}_{user['semester']}"
    file_id = update.message.photo[-1].file_id
    
    Database.set_class_config(class_id, {"routine_image_id": file_id})
    
    await update.message.reply_text(t("routine_updated", user.get("language", "en")), parse_mode="Markdown")
    return ConversationHandler.END

async def delete_slot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = Database.get_user(query.from_user.id)
    if user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        return
        
    slot_id = query.data.split("_")[1]
    Database.delete_timetable_slot(slot_id)
    
    await query.message.reply_text("✅ Slot permanently deleted from the routine.")
    await view_timetable(update, context)

# --- Notification Handlers ---
async def notify_instant_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = Database.get_user(query.from_user.id)
    if user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        return
        
    target_date = query.data.split("_")[2]
    class_id = f"{user['department']}_{user['semester']}"
    
    # Generate batched routine text without management IDs for students
    routine_text, _ = get_routine_text(class_id, user['department'], user['semester'], target_date, "STUDENT")
    msg = f"📢 *CLASS ROUTINE UPDATE*\n\n{routine_text}"
    
    from database import supabase
    class_users = supabase.table("users").select("id").eq("department", user['department']).eq("semester", user['semester']).neq("id", user["id"]).execute().data
    for u in class_users:
        try: await context.bot.send_message(u["id"], msg, parse_mode="Markdown")
        except: pass
        
    await query.edit_message_text(f"✅ Batched notification for {target_date} sent to the class!")

NOTIFY_SCHED_TIME = range(20, 21)

async def notify_sched_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = Database.get_user(query.from_user.id)
    if user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        return
        
    target_date = query.data.split("_")[2]
    context.user_data["notify_target_date"] = target_date
    
    await query.edit_message_text(
        f"🕒 *Schedule Notification for {target_date}*\n\n"
        "Please enter the time to send the notification (Format: HH:MM or HH:MM PM, e.g. 20:30 or 8:30 PM):",
        parse_mode="Markdown"
    )
    return NOTIFY_SCHED_TIME

async def notify_sched_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "/cancel":
        await update.message.reply_text("❌ Action Cancelled.")
        return ConversationHandler.END
        
    try:
        parsed_time = parse_time(update.message.text)
        
        user = Database.get_user(update.effective_user.id)
        class_id = f"{user['department']}_{user['semester']}"
        target_date = context.user_data["notify_target_date"]
        
        # Create a datetime for today with the parsed time
        now = get_now()
        hour, minute = map(int, parsed_time.split(':'))
        sched_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If the scheduled time is in the past for today, assume they mean tomorrow
        if sched_dt < now:
            sched_dt += datetime.timedelta(days=1)
            
        import pytz
        utc_sched_time = sched_dt.astimezone(pytz.UTC).isoformat()
        
        Database.add_scheduled_notification({
            "class_id": class_id,
            "target_date": target_date,
            "scheduled_time": utc_sched_time,
            "status": "PENDING"
        })
        
        await update.message.reply_text(f"✅ Notification scheduled successfully for {sched_dt.strftime('%d %b %Y, %I:%M %p')}!")
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("⚠️ Invalid time format. Please use something like *20:30* or *8:30 PM*.\nOr type /cancel.", parse_mode="Markdown")
        return NOTIFY_SCHED_TIME

# exports ...
timetable_view_handler = CommandHandler("timetable", view_timetable)
timetable_nav_handler = CallbackQueryHandler(view_timetable, pattern="^ttt_")
routine_view_handler = CallbackQueryHandler(view_routine_img, pattern="^view_routine_img$")
slot_delete_handler = CallbackQueryHandler(delete_slot_callback, pattern="^delslot_")
notify_instant_handler = CallbackQueryHandler(notify_instant_callback, pattern="^ntfy_inst_")

notify_sched_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(notify_sched_trigger, pattern="^ntfy_sch_")],
    states={
        NOTIFY_SCHED_TIME: [MessageHandler(filters.TEXT, notify_sched_save)]
    },
    fallbacks=[CommandHandler("cancel", cancel_global)]
)

routine_upload_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(upload_routine_trigger, pattern="^upload_routine_trigger$")],
    states={
        UPLOAD_IMG: [MessageHandler(filters.PHOTO, handle_routine_upload)]
    },
    fallbacks=[CommandHandler("cancel", cancel_global)]
)

timetable_add_handler = ConversationHandler(
    entry_points=[
        CommandHandler("add_slot", add_slot_trigger),
        CallbackQueryHandler(add_slot_trigger, pattern="^add_slot_trigger$")
    ],
    states={
        SUBJ_CHOICE: [
            CallbackQueryHandler(
                add_slot_subj_choice,
                pattern="^(course_\\d+|course_manual|cancel_action)$"
            )
        ],
        SUBJ: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_slot_subj)],
        DAY: [CallbackQueryHandler(add_slot_day, pattern="^(addday_|cancel_action)")],
        START: [MessageHandler(filters.TEXT, add_slot_start_time)],
        END: [MessageHandler(filters.TEXT, add_slot_end_time)],
        ROOM: [
            MessageHandler(filters.TEXT, add_slot_room),
            CallbackQueryHandler(add_slot_room, pattern="^skip_room$")
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_global)]
)
