from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from database import Database
from utils.i18n import t

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = Database.get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ You are not registered yet. Use /start")
        return

    role = user["role"]
    lang = user.get("language", "en")
    
    if not user.get("is_approved", False):
        await update.message.reply_text(
            "⏳ *Your registration is pending CR approval.*\n"
            "Please wait while your batch CR verifies your information.",
            parse_mode="Markdown"
        )
        return
    
    keyboard = [
        [t("menu_timetable", lang), t("menu_resources", lang)],
        [t("menu_deadlines", lang), t("menu_notices", lang)],
        [t("menu_results", lang), t("menu_profile", lang)]
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    msg_text = (
        f"📋 *Main Menu*\n"
        f"👤 Role: {role}\n"
        f"🏢 Class: {user['department']} Semester {user['semester']}"
    )

    if update.message:
        await update.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=user_id, text=msg_text, reply_markup=reply_markup, parse_mode="Markdown")

async def send_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, query_obj=None):
    user = Database.get_user(user_id)
    lang = user.get("language", "en")
    student_id = user.get("student_id", "N/A")
    
    msg = t("profile_title", lang, name=user['full_name'], student_id=student_id, role=user['role'], dept=user['department'], sem=user['semester'])
    
    btn_text = t("lang_toggle_btn", lang)
    settings_btn = "⚙️ Notifications / সেটিংস"
    
    keyboard = [
        [InlineKeyboardButton(btn_text, callback_data="toggle_lang")],
        [InlineKeyboardButton(settings_btn, callback_data="view_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query_obj:
        await query_obj.edit_message_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = Database.get_user(update.effective_user.id)
    if not user: return
    if not user.get("is_approved", False):
        await update.message.reply_text("⏳ Your access is pending approval.")
        return
    lang = user.get("language", "en") or "en"
    
    # Trigger functions based on persistent menu click
    from handlers.timetable import view_timetable
    from handlers.deadlines import view_deadlines
    from handlers.notices import view_notices
    from handlers.resources import view_resources
    from handlers.results import view_results
    from handlers.router import heuristic_router
    
    # Check against both languages for better resilience
    if text in [t("menu_timetable", "en"), t("menu_timetable", "bn")]:
        await view_timetable(update, context)
    elif text in [t("menu_resources", "en"), t("menu_resources", "bn")]:
        await view_resources(update, context)
    elif text in [t("menu_deadlines", "en"), t("menu_deadlines", "bn")]:
        await view_deadlines(update, context)
    elif text in [t("menu_notices", "en"), t("menu_notices", "bn")]:
        await view_notices(update, context)
    elif text in [t("menu_results", "en"), t("menu_results", "bn")]:
        await view_results(update, context)
    elif text in [t("menu_profile", "en"), t("menu_profile", "bn")]:
        await send_profile(update, context, update.effective_user.id)
    else:
        # Check Natural Language Query (Heuristic Router)
        routed = await heuristic_router(update, context)
        if not routed:
            # Fallback or unknown command
            pass

async def toggle_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = Database.get_user(user_id)
    
    new_lang = "bn" if user.get("language", "en") == "en" else "en"
    Database.update_user(user_id, {"language": new_lang})
    
    # Notify user it switched
    await query.answer(t("lang_switched", new_lang), show_alert=True)
    
    # Refresh profile view
    await send_profile(update, context, user_id, query_obj=query)
    
    # IMPORTANT: Force a keyboard refresh with the new language
    await menu(update, context)

async def view_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = Database.get_user(user_id)
    
    pref_class = user.get("pref_class_reminders", True)
    pref_deadlines = user.get("pref_deadline_reminders", True)
    pref_digest = user.get("pref_daily_digest", True)
    pref_notices = user.get("pref_notices", True)
    
    def get_icon(val): return "✅ ON" if val else "❌ OFF"
    
    keyboard = [
        [InlineKeyboardButton(f"Class Alerts: {get_icon(pref_class)}", callback_data="toggle_pref_class")],
        [InlineKeyboardButton(f"Deadline Alerts: {get_icon(pref_deadlines)}", callback_data="toggle_pref_deadlines")],
        [InlineKeyboardButton(f"Daily Digest: {get_icon(pref_digest)}", callback_data="toggle_pref_digest")],
        [InlineKeyboardButton(f"Notice Broadcasts: {get_icon(pref_notices)}", callback_data="toggle_pref_notices")],
        [InlineKeyboardButton("⬅️ Back to Profile", callback_data="back_to_profile")]
    ]
    
    await query.answer()
    await query.edit_message_text(
        "🔔 *Notification Settings*\n\nChoose what you want to be notified about:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def toggle_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = Database.get_user(user_id)
    
    pref_key = query.data.replace("toggle_pref_", "")
    # Map to DB columns
    db_map = {
        "class": "pref_class_reminders",
        "deadlines": "pref_deadline_reminders",
        "digest": "pref_daily_digest",
        "notices": "pref_notices"
    }
    
    column = db_map.get(pref_key)
    if column:
        current_val = user.get(column, True)
        Database.update_user(user_id, {column: not current_val})
        
    await query.answer("Preference updated!")
    await view_settings(update, context)

async def back_to_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await send_profile(update, context, query.from_user.id, query_obj=query)

menu_handler = CommandHandler("menu", menu)
lang_toggle_handler = CallbackQueryHandler(toggle_language, pattern="^toggle_lang$")
settings_view_handler = CallbackQueryHandler(view_settings, pattern="^view_settings$")
pref_toggle_handler = CallbackQueryHandler(toggle_preference, pattern="^toggle_pref_")
profile_back_handler = CallbackQueryHandler(back_to_profile, pattern="^back_to_profile$")
