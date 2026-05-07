from telegram import Update, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from database import Database
from utils.timezone import get_now, parse_time
from utils.helpers import build_menu, get_cancel_button
from config import Config
import datetime
import pytz

# States
TITLE, DESC, TYPE, DUE_DATE, DUE_TIME = range(5)

async def view_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = Database.get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ You are not registered yet. Use /start")
        return

    class_id = f"{user['department']}_{user['semester']}"
    deadlines = Database.get_deadlines(class_id)
    
    text = f"🚨 *Upcoming Deadlines*\n_Class: {user['department']} Semester {user['semester']}_\n\n"
    
    if not deadlines:
        text += "🎉 No upcoming assignments or exams!"
    else:
        now = datetime.datetime.now(datetime.timezone.utc)
        for d in deadlines:
            due = datetime.datetime.fromisoformat(d['due_datetime']).replace(tzinfo=pytz.UTC)
            local_due = due.astimezone(pytz.timezone(Config.TZ))
            time_left = due - now
            
            # Urgent marker
            urgency = "🔴" if time_left.total_seconds() < 172800 else "🕒" # less than 48 hours
            
            text += f"📌 *{d['title']}* [{d['type']}]\n"
            if d.get('description'):
                text += f"   📝 _{d['description']}_\n"
            text += f"   {urgency} *{local_due.strftime('%d %b, %I:%M %p')}*\n"
            if d.get('file_id'):
                text += "   📎 _Attachment in History_\n"
            text += "\n"
            
    reply_markup = None
    buttons = []
    if user["role"] in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        buttons.append(InlineKeyboardButton("➕ Add Deadline", callback_data="add_deadline_trigger"))
        # Add delete buttons for current deadlines
        for d in deadlines:
            short_title = d['title'][:15] + "..." if len(d['title']) > 15 else d['title']
            buttons.append(InlineKeyboardButton(f"🗑️ Delete {short_title}", callback_data=f"deldead_{d['id']}"))
        
        reply_markup = build_menu(buttons, n_cols=1)

    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

# --- Add Deadline Flow ---

async def add_deadline_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    msg_obj = query.message if query else update.message
    user_id = query.from_user.id if query else update.effective_user.id
        
    user = Database.get_user(user_id)
    if not user or user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        txt = "❌ Only CRs or Teachers can add deadlines."
        if query: await query.edit_message_text(txt)
        else: await update.message.reply_text(txt)
        return ConversationHandler.END

    if query: await query.answer()

    text = "🗓 *Add New Deadline*\n\nPlease type the *Title* (e.g., Physics Assignment 3)\n_OR upload a File/Photo with the title as the caption:_"
    
    if query:
        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await msg_obj.reply_text(text, parse_mode="Markdown")
    return TITLE

async def add_deadline_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data["tmp_deadline"] = {
            "title": update.message.caption or "Untitled Deadline",
            "file_id": update.message.photo[-1].file_id,
            "file_type": "photo"
        }
    elif update.message.document:
        context.user_data["tmp_deadline"] = {
            "title": update.message.caption or update.message.document.file_name,
            "file_id": update.message.document.file_id,
            "file_type": "document"
        }
    else:
        context.user_data["tmp_deadline"] = {
            "title": update.message.text,
            "file_id": None,
            "file_type": None
        }
    
    await update.message.reply_text(
        f"Title: *{context.user_data['tmp_deadline']['title']}*\n\nPlease type a *Description* for this deadline, or type /skip to leave it empty:",
        parse_mode="Markdown"
    )
    return DESC

async def add_deadline_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "/cancel":
        await update.message.reply_text("❌ Action Cancelled.")
        return ConversationHandler.END
        
    desc = None if update.message.text.lower() == "/skip" else update.message.text
    context.user_data["tmp_deadline"]["description"] = desc
    
    buttons = [
        InlineKeyboardButton("📚 ASSIGNMENT", callback_data="type_ASSIGNMENT"),
        InlineKeyboardButton("📝 EXAM", callback_data="type_EXAM"),
        get_cancel_button()
    ]
    reply_markup = build_menu(buttons, n_cols=2)
    
    await update.message.reply_text(
        "Select the type of deadline:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return TYPE

async def add_deadline_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_action":
        await query.edit_message_text("❌ Action Cancelled.")
        return ConversationHandler.END
        
    dtype = query.data.split("_")[1]
    context.user_data["tmp_deadline"]["type"] = dtype
    
    await query.edit_message_text(
        text=f"Type: *{dtype}*\n\nPlease type the *Due Date* (Format: YYYY-MM-DD):",
        parse_mode="Markdown"
    )
    return DUE_DATE

async def add_deadline_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "/cancel":
        await update.message.reply_text("❌ Action Cancelled.")
        return ConversationHandler.END

    try:
        datetime.datetime.strptime(update.message.text, "%Y-%m-%d")
        context.user_data["tmp_deadline"]["date"] = update.message.text
        
        await update.message.reply_text(
            f"Date: *{update.message.text}*\n\nPlease type the *Due Time* (e.g., 23:59 or 11:59 PM):",
            parse_mode="Markdown"
        )
        return DUE_TIME
    except ValueError:
        await update.message.reply_text("⚠️ Invalid date. Please use *YYYY-MM-DD* (e.g., 2026-05-12).\nOr type /cancel.")
        return DUE_DATE

async def add_deadline_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "/cancel":
        await update.message.reply_text("❌ Action Cancelled.")
        return ConversationHandler.END

    try:
        time_str = parse_time(update.message.text)
        
        date_str = context.user_data["tmp_deadline"]["date"]
        full_dt_str = f"{date_str} {time_str}"
        
        local_tz = pytz.timezone(Config.TZ)
        local_dt = local_tz.localize(datetime.datetime.strptime(full_dt_str, "%Y-%m-%d %H:%M"))
        utc_dt = local_dt.astimezone(pytz.UTC).isoformat()
        
        user = Database.get_user(update.effective_user.id)
        class_id = f"{user['department']}_{user['semester']}"
        
        deadline_data = {
            "class_id": class_id,
            "title": context.user_data["tmp_deadline"]["title"],
            "description": context.user_data["tmp_deadline"]["description"],
            "type": context.user_data["tmp_deadline"]["type"],
            "due_datetime": utc_dt,
            "file_id": context.user_data["tmp_deadline"].get("file_id")
        }
        file_type = context.user_data["tmp_deadline"].get("file_type")
        
        Database.add_deadline(deadline_data)
        
        # Broadcast Notification
        from database import supabase
        dept, sem = class_id.split("_")
        class_users = supabase.table("users").select("id, pref_deadline_reminders").eq("department", dept).eq("semester", int(sem)).neq("id", user.get('id')).execute().data
        for u in class_users:
            if not u.get("pref_deadline_reminders", True):
                continue
            try:
                msg = f"🔔 *New Deadline Added by {user['full_name']}*\n" \
                      f"Title: *{deadline_data['title']}* [{deadline_data['type']}]\n"
                if deadline_data.get('description'):
                    msg += f"Description: _{deadline_data['description']}_\n"
                msg += f"Due: {local_dt.strftime('%d %b, %Y at %I:%M %p')}"
                if deadline_data.get('file_id'):
                    if file_type == "photo":
                        await context.bot.send_photo(u["id"], photo=deadline_data['file_id'], caption=msg, parse_mode="Markdown")
                    else:
                        await context.bot.send_document(u["id"], document=deadline_data['file_id'], caption=msg, parse_mode="Markdown")
                else:
                    await context.bot.send_message(u["id"], msg, parse_mode="Markdown")
            except:
                pass
        
        await update.message.reply_text(
            f"✅ *{deadline_data['title']}* saved! Reminders will be sent 24h and 1h prior.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("⚠️ Invalid time format. Please use something like *11:59 PM* or *23:59*.\nOr type /cancel.")
        return DUE_TIME

async def delete_deadline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = Database.get_user(query.from_user.id)
    
    if not user or user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        await query.answer("❌ Unauthorized.")
        return

    deadline_id = query.data.split("_")[1]
    Database.delete_deadline(deadline_id)
    await query.answer("✅ Deadline Deleted.")
    
    # Refresh the view
    await view_deadlines(update, context)

async def cancel_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action Cancelled.")
    return ConversationHandler.END


deadline_view_handler = CommandHandler("deadlines", view_deadlines)
deadline_nav_handler = CallbackQueryHandler(view_deadlines, pattern="^view_deadlines$")
deadline_delete_handler = CallbackQueryHandler(delete_deadline_callback, pattern="^deldead_")

deadline_add_handler = ConversationHandler(
    entry_points=[
        CommandHandler("add_deadline", add_deadline_trigger),
        CallbackQueryHandler(add_deadline_trigger, pattern="^add_deadline_trigger$")
    ],
    states={
        TITLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_deadline_title),
            MessageHandler(filters.PHOTO | filters.Document.ALL, add_deadline_title)
        ],
        DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_deadline_desc)],
        TYPE: [CallbackQueryHandler(add_deadline_type, pattern="^(type_|cancel_action)")],
        DUE_DATE: [MessageHandler(filters.TEXT, add_deadline_date)],
        DUE_TIME: [MessageHandler(filters.TEXT, add_deadline_time)],
    },
    fallbacks=[CommandHandler("cancel", cancel_global)]
)
