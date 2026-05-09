from telegram import Update, InlineKeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import Config
from database import Database, supabase
from utils.helpers import build_menu
from utils.i18n import t

# States
GET_NAME, GET_ID, GET_DEPT, GET_SEM = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = Database.get_user(user_id)

    if user:
        lang = user.get("language", "en")
        if not user.get("is_approved", False):
            await update.message.reply_text(
                "⏳ *Your registration is pending CR approval.*\n"
                "Please wait while your batch CR verifies your information.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
            
        await update.message.reply_text(
            t("welcome_back", lang, name=user['full_name']),
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # For new users
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
    buttons = [InlineKeyboardButton(dept, callback_data=f"dept_{i}") for i, dept in enumerate(Config.DEPARTMENTS)]
    reply_markup = build_menu(buttons, n_cols=1)
    await update.message.reply_text(t("ask_dept", "en"), reply_markup=reply_markup, parse_mode="Markdown")
    return GET_DEPT

async def get_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dept_idx = int(query.data.split("_")[1])
    department = Config.DEPARTMENTS[dept_idx]
    context.user_data["department"] = department
    buttons = [InlineKeyboardButton(f"Semester {sem}", callback_data=f"sem_{sem}") for sem in Config.SEMESTERS]
    reply_markup = build_menu(buttons, n_cols=2)
    await query.edit_message_text(text=t("ask_sem", "en", dept=department), reply_markup=reply_markup, parse_mode="Markdown")
    return GET_SEM

async def get_sem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Registration Submitted!")
    
    semester = int(query.data.split("_")[1])
    data = context.user_data
    
    user_record = {
        "id": update.effective_user.id,
        "full_name": data["full_name"],
        "student_id": data["student_id"],
        "language": "en",
        "role": Config.ROLE_STUDENT,
        "department": data["department"],
        "semester": semester,
        "is_approved": False # Default to False
    }
    
    Database.create_user(user_record)
    
    # Notify CRs
    crs = supabase.table("users").select("id").eq("department", data["department"]).eq("semester", semester).eq("role", Config.ROLE_CR).execute().data
    
    approval_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"appr_{update.effective_user.id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rejt_{update.effective_user.id}")
        ]
    ])
    
    admin_msg = (
        f"👤 *New Registration Request*\n\n"
        f"Name: {data['full_name']}\n"
        f"ID: {data['student_id']}\n"
        f"Batch: {data['department']} Semester {semester}\n\n"
        f"Please verify and approve this student."
    )
    
    notified = False
    for cr in crs:
        try:
            await context.bot.send_message(chat_id=cr["id"], text=admin_msg, reply_markup=approval_kb, parse_mode="Markdown")
            notified = True
        except:
            pass

    # If no CR was notified (none found or all failed), notify Admins
    if not notified:
        admins = supabase.table("users").select("id").eq("role", Config.ROLE_ADMIN).execute().data
        for admin in admins:
            try:
                await context.bot.send_message(chat_id=admin["id"], text=admin_msg, reply_markup=approval_kb, parse_mode="Markdown")
            except:
                pass
            
    await query.edit_message_text(
        text=f"✅ *Registration Submitted!*\n\nYour details have been sent to the **Batch CR** for approval.\n"
             f"You will be notified once they verify your access.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, target_id = query.data.split("_")
    await query.answer()
    
    user = Database.get_user(target_id)
    if not user:
        await query.edit_message_text("❌ User not found.")
        return

    if action == "appr":
        Database.update_user(target_id, {"is_approved": True})
        await query.edit_message_text(f"✅ Approved {user['full_name']} ({user['student_id']})")
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🎉 *Access Approved!*\n\nWelcome {user['full_name']}, your registration has been approved by the CR. Use /start to begin.",
                parse_mode="Markdown"
            )
        except:
            pass
    else:
        # Rejection: Just delete the user record or keep as rejected?
        # User might want to try again, so let's delete
        supabase.table("users").delete().eq("id", target_id).execute()
        await query.edit_message_text(f"❌ Rejected and removed {user['full_name']}")
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="❌ *Access Denied*\n\nYour registration request was rejected by the Batch CR. If this was a mistake, please contact your CR."
            )
        except:
            pass

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

approval_handler = CallbackQueryHandler(handle_approval, pattern="^(appr_|rejt_)")
