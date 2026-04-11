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
    
    keyboard = [
        [t("menu_timetable", lang), t("menu_resources", lang)],
        [t("menu_deadlines", lang), t("menu_notices", lang)],
        [t("menu_profile", lang)]
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
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, callback_data="toggle_lang")]])
    
    if query_obj:
        await query_obj.edit_message_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = Database.get_user(update.effective_user.id)
    if not user: return
    lang = user.get("language", "en") or "en"
    
    # Trigger functions based on persistent menu click
    from handlers.timetable import view_timetable
    from handlers.deadlines import view_deadlines
    from handlers.notices import view_notices
    from handlers.resources import view_resources
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

menu_handler = CommandHandler("menu", menu)
lang_toggle_handler = CallbackQueryHandler(toggle_language, pattern="^toggle_lang$")
