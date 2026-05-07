from telegram import Update, InlineKeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from database import Database
from utils.timezone import get_now
import datetime
import pytz
from config import Config
from utils.helpers import build_menu, get_cancel_button
from telegram.error import BadRequest
from utils.i18n import t

# States
TITLE, DESC, SEARCH_QUERY = range(3)
POSTS_PER_PAGE = 3

async def view_notices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = Database.get_user(user_id)
    lang = user.get("language", "en") if user else "en"
    
    if not user:
        await update.message.reply_text("❌ You are not registered yet. Use /start")
        return

    class_id = f"{user['department']}_{user['semester']}"
    
    # Check if called from pagination callback
    query = update.callback_query
    page = 0
    if query:
        await query.answer()
        data_parts = query.data.split("_")
        if len(data_parts) > 1 and data_parts[1].isdigit():
            page = int(data_parts[1])

    # Fetch more notices than needed to see if we need a "Next" button
    limit = POSTS_PER_PAGE + 1
    offset = page * POSTS_PER_PAGE
    
    # Notice: the get_notices in database needs to support offset
    # I'll modify database.py or just fetch a large chunk for now, but better to fetch from DB
    notices = Database.get_notices(class_id, limit=100) # Fetch all and slice for simplicity
    
    total_notices = len(notices)
    current_notices = notices[offset:offset + POSTS_PER_PAGE]
    
    text = t("notice_board_title", lang, dept=user['department'], sem=user['semester'])
    
    if not current_notices:
        text += t("notice_empty", lang)
    else:
        for n in current_notices:
            created = datetime.datetime.fromisoformat(n['created_at']).astimezone(pytz.timezone(Config.TZ))
            
            # Since author is a user ID, we could fetch their name, but for board we can just show notice text
            text += f"📅 _{created.strftime('%d %b, %I:%M %p')}_\n"
            if n.get('title'):
                text += f"   📌 *{n['title']}*\n"
            
            # Legacy notices used 'content', new notices use 'description'
            display_text = n.get('description') or n.get('content', '')
            text += f"   {display_text}\n\n"
            
            if n.get('file_id'):
                text += "📎 _(This notice contained an attachment. Find it in 📚 Resources or scroll up.)_\n\n"
            text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Pagination
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(t("btn_newer", lang), callback_data=f"notices_{page-1}"))
    if total_notices > offset + POSTS_PER_PAGE:
        nav_buttons.append(InlineKeyboardButton(t("btn_older", lang), callback_data=f"notices_{page+1}"))
    
    # Add Search Button
    nav_buttons.insert(0, InlineKeyboardButton(t("btn_search", lang), callback_data="search_notice_trigger"))
        
    footer = []
    if user["role"] in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        footer.append(InlineKeyboardButton(t("btn_add_notice", lang), callback_data="post_notice_trigger"))
        # Add delete buttons for current notices
        for n in current_notices:
            # We use a short ID or a slice of UUID for the button
            short_id = n['id'][:8]
            footer.append(InlineKeyboardButton(f"🗑️ Delete {short_id}", callback_data=f"delnotice_{n['id']}"))
        
    if nav_buttons or footer:
        reply_markup = build_menu(nav_buttons, n_cols=2, footer_buttons=footer)
    else:
        reply_markup = None

    if query:
        try:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        except BadRequest:
            pass
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

# --- Post Notice Flow ---

async def post_notice_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    msg_obj = query.message if query else update.message
    user_id = query.from_user.id if query else update.effective_user.id
        
    user = Database.get_user(user_id)
    lang = user.get("language", "en") if user else "en"
    if not user or user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        txt = "❌ Only CRs or Teachers can post notices."
        if query: await query.edit_message_text(txt)
        else: await msg_obj.reply_text(txt)
        return ConversationHandler.END

    if query: await query.answer()

    text = "📝 *Post New Notice*\n\nPlease type the *Title* of the Notice:"
    
    if query:
        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await msg_obj.reply_text(text, parse_mode="Markdown")
        
    return TITLE

async def post_notice_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_obj = update.message
    if msg_obj.text and msg_obj.text.lower() == "/cancel":
        await msg_obj.reply_text("❌ Action Cancelled.")
        return ConversationHandler.END
        
    context.user_data["active_notice_title"] = msg_obj.text
    
    text = "Got it! Now please type the *Description/Content* or upload a File/Photo with a Caption:\n_(Or type /skip to leave description empty)_"
    await msg_obj.reply_text(text, parse_mode="Markdown")
    return DESC

async def post_notice_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_obj = update.message
    if msg_obj.text and msg_obj.text.lower() == "/cancel":
        await msg_obj.reply_text(t("action_cancelled", "en"))
        return ConversationHandler.END

    user = Database.get_user(update.effective_user.id)
    lang = user.get("language", "en") if user else "en"
    class_id = f"{user['department']}_{user['semester']}"
    
    # Initialize variables to avoid UnboundLocalError
    file_id = None
    file_type = None
    res_type = "LINK" # fallback
    
    # Check for existing session content (to share title among multiple files)
    session_content = context.user_data.get("active_notice_content")

    if msg_obj.photo:
        # If no session content yet, use current caption or default
        if not session_content:
            desc = msg_obj.caption or "Attached Photo"
            context.user_data["active_notice_content"] = desc
        else:
            desc = session_content
        
        file_id = msg_obj.photo[-1].file_id
        file_type = "photo"
        res_type = "PHOTO"
    elif msg_obj.document:
        if not session_content:
            desc = msg_obj.caption or msg_obj.document.file_name
            context.user_data["active_notice_content"] = desc
        else:
            desc = session_content

        file_id = msg_obj.document.file_id
        file_type = "document"
        res_type = "FILE"
    else:
        desc = "" if msg_obj.text.lower() == "/skip" else msg_obj.text
        context.user_data["active_notice_content"] = desc
    
    notice_title = context.user_data.get("active_notice_title", "Notice")
    
    notice_data = {
        "class_id": class_id,
        "author_id": user['id'],
        "title": notice_title,
        "description": desc,
        "content": desc, # Legacy fallback
        "category": 'GENERAL',
        "file_id": file_id
    }
    
    Database.add_notice(notice_data)
    
    if file_id:
        Database.add_resource({
            "class_id": class_id,
            "author_id": user['id'],
            "title": notice_title,
            "description": desc,
            "resource_type": res_type,
            "content": file_id
        })
    
    # Broadcast Notification
    from database import supabase
    dept, sem = class_id.split("_")
    class_users = supabase.table("users").select("id, language").eq("department", dept).eq("semester", int(sem)).neq("id", user.get('id')).execute().data
    
    for u in class_users:
        if u.get('pref_notices', True) == False:
            continue
            
        u_lang = u.get("language", "en")
        try:
            msg = t("notice_from", u_lang, author=user['full_name'], role=user['role'])
            msg += f"\n📌 *{notice_title}*\n{desc}"
            if file_id:
                if file_type == "photo":
                    await context.bot.send_photo(u["id"], photo=file_id, caption=msg, parse_mode="Markdown")
                else:
                    await context.bot.send_document(u["id"], document=file_id, caption=msg, parse_mode="Markdown")
            else:
                await context.bot.send_message(u["id"], msg, parse_mode="Markdown")
        except:
            pass

    # If it was just text, we end. If it was a file, we stay open to allow more files in one go (Album support)
    if not file_id:
        await msg_obj.reply_text(f"✅ *Notice* broadcasted successfully!", parse_mode="Markdown")
        return ConversationHandler.END
    else:
        # File sent, stay in DESC and offer a DONE button
        kb = [[InlineKeyboardButton("✅ Done / সম্পন্ন", callback_data="finish_notice")]]
        await msg_obj.reply_text("✅ File synced! You can send more files/photos, or click **Done** to finish.", reply_markup=InlineKeyboardMarkup(kb))
        return DESC

async def finish_notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Clear session cache
    context.user_data.pop("active_notice_content", None)
    context.user_data.pop("active_notice_title", None)
    
    await query.answer("Broadcast Complete!")
    await query.edit_message_text("✅ All files have been broadcasted and saved to Resources.")
    return ConversationHandler.END

async def delete_notice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = Database.get_user(user_id)
    
    if not user or user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        await query.answer("❌ Unauthorized.")
        return

    notice_id = query.data.split("_")[1]
    
    # Confirmation step (optional but good)
    # For now, let's just delete to keep it snappy as requested
    Database.delete_notice(notice_id)
    await query.answer("✅ Notice Deleted.")
    
    # Refresh the view
    await view_notices(update, context)

async def cancel_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action Cancelled.")
    return ConversationHandler.END

# --- Search Flow ---

async def search_notice_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = Database.get_user(query.from_user.id)
    lang = user.get("language", "en")
    await query.answer()
    await query.edit_message_text(t("search_prompt", lang), parse_mode="Markdown")
    return SEARCH_QUERY

async def search_notice_perform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search_text = update.message.text
    user = Database.get_user(update.effective_user.id)
    lang = user.get("language", "en")
    class_id = f"{user['department']}_{user['semester']}"
    
    results = Database.search_notices(class_id, search_text)
    
    if not results:
        await update.message.reply_text(t("search_none", lang))
        return ConversationHandler.END
        
    text = t("search_results", lang, query=search_text)
    for n in results[:5]: # Top 5 results
        created = datetime.datetime.fromisoformat(n['created_at']).astimezone(pytz.timezone(Config.TZ))
        display_text = n.get('description') or n.get('content', '')
        title_text = f"📌 *{n['title']}*\n   " if n.get('title') else ""
        text += f"📅 _{created.strftime('%d %b, %I:%M %p')}_\n   {title_text}{display_text}\n\n"
        
    await update.message.reply_text(text, parse_mode="Markdown")
    return ConversationHandler.END

notice_view_handler = CommandHandler("notices", view_notices)
notice_nav_handler = CallbackQueryHandler(view_notices, pattern="^notices_")
notice_delete_handler = CallbackQueryHandler(delete_notice_callback, pattern="^delnotice_")

notice_search_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(search_notice_trigger, pattern="^search_notice_trigger$")],
    states={
        SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_notice_perform)]
    },
    fallbacks=[CommandHandler("cancel", cancel_global)]
)

notice_post_handler = ConversationHandler(
    entry_points=[
        CommandHandler("post_notice", post_notice_trigger),
        CallbackQueryHandler(post_notice_trigger, pattern="^post_notice_trigger$")
    ],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_notice_title)],
        DESC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, post_notice_desc),
            MessageHandler(filters.PHOTO | filters.Document.ALL, post_notice_desc),
            CallbackQueryHandler(finish_notice, pattern="^finish_notice$")
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_global)]
)
