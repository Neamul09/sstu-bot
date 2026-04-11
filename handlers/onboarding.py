from telegram import Update, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import Config
from database import Database
from utils.helpers import build_menu
from utils.i18n import t

# States
GET_NAME, GET_ID, GET_DEPT, GET_SEM = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = Database.get_user(user_id)

    lang = user.get("language", "en") if user else "en"

    if user:
        await update.message.reply_text(
            t("welcome_back", lang, name=user['full_name']),
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # For new users, assume 'en' for onboarding, they can change later
    await update.message.reply_text(
        t("welcome_start", "en"),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["full_name"] = update.message.text
    
    await update.message.reply_text(
        t("ask_id", "en", name=update.message.text),
        parse_mode="Markdown"
    )
    return GET_ID

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["student_id"] = update.message.text
    
    # Build Department inline buttons
    buttons = [InlineKeyboardButton(dept, callback_data=f"dept_{i}") for i, dept in enumerate(Config.DEPARTMENTS)]
    reply_markup = build_menu(buttons, n_cols=1)
    
    await update.message.reply_text(
        t("ask_dept", "en"),
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return GET_DEPT

async def get_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Extract department index
    dept_idx = int(query.data.split("_")[1])
    department = Config.DEPARTMENTS[dept_idx]
    context.user_data["department"] = department
    
    # Build Semester inline buttons (grid 4x2)
    buttons = [InlineKeyboardButton(f"Semester {sem}", callback_data=f"sem_{sem}") for sem in Config.SEMESTERS]
    reply_markup = build_menu(buttons, n_cols=2)
    
    await query.edit_message_text(
        text=t("ask_sem", "en", dept=department),
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return GET_SEM

async def get_sem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Registration Complete!")
    
    semester = int(query.data.split("_")[1])
    data = context.user_data
    
    user_record = {
        "id": update.effective_user.id,
        "full_name": data["full_name"],
        "student_id": data["student_id"],
        "language": "en", # Default
        "role": Config.ROLE_STUDENT, # Automatically Auto-Approved Student
        "department": data["department"],
        "semester": semester
    }
    
    Database.create_user(user_record)
    
    summary = t("reg_complete", "en", name=data['full_name'], student_id=data['student_id'], dept=data['department'], sem=semester)
    
    await query.edit_message_text(
        text=summary,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t("reg_cancelled", "en"))
    return ConversationHandler.END

onboarding_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        GET_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id)],
        GET_DEPT: [CallbackQueryHandler(get_dept, pattern="^dept_")],
        GET_SEM: [CallbackQueryHandler(get_sem, pattern="^sem_")],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_message=False
)
