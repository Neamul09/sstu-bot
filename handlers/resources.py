from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from database import Database
from config import Config
from utils.helpers import build_menu, get_cancel_button
from telegram.error import BadRequest
from utils.i18n import t
import datetime
import pytz

# States for Adding Resource
RES_TITLE, RES_DESC, RES_CONTENT, RES_SEARCH = range(4)
ITEMS_PER_PAGE = 5

async def view_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = Database.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ You are not registered yet. Use /start")
        return

    class_id = f"{user['department']}_{user['semester']}"
    
    query = update.callback_query
    page = 0
    if query:
        await query.answer()
        data_parts = query.data.split("_")
        if len(data_parts) > 1 and data_parts[1].isdigit():
            page = int(data_parts[1])

    limit = ITEMS_PER_PAGE + 1
    offset = page * ITEMS_PER_PAGE
    
    # We fetch all ordered by created_at desc (can optimize with offset later)
    resources = Database.get_resources(class_id, limit=100)
    lang = user.get("language", "en") or "en"
    
    total_resources = len(resources)
    current_page_items = resources[offset:offset + ITEMS_PER_PAGE]
    
    text = t("res_library_title", lang, dept=user['department'], sem=user['semester'])
    
    buttons = []
    
    if not resources:
        text += "\n\n" + t("res_empty", lang)
    else:
        text += "\n" + t("res_count", lang, count=total_resources) + "\n\n"
        for r in current_page_items:
            icon = "📎" if r["resource_type"] in ["FILE", "PHOTO"] else "🔗"
            btn_text = f"{icon} {r['title']}"
            buttons.append(InlineKeyboardButton(btn_text, callback_data=f"resitem_{r['id']}"))
            
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(t("btn_newer", lang), callback_data=f"resources_{page-1}"))
    if total_resources > offset + ITEMS_PER_PAGE:
        nav_buttons.append(InlineKeyboardButton(t("btn_older", lang), callback_data=f"resources_{page+1}"))
    
    # Add Search Button
    nav_buttons.insert(0, InlineKeyboardButton(t("btn_search", lang), callback_data="search_res_trigger"))
        
    footer = None
    if user["role"] in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        footer = [InlineKeyboardButton(t("btn_add_res", lang), callback_data="add_resource_trigger")]
        
    reply_markup = None
    if buttons or nav_buttons or footer:
        # We handle layout: resources stacked vertically, nav horizontally
        kb = []
        for btn in buttons:
            kb.append([btn])
        if nav_buttons:
            kb.append(nav_buttons)
        if footer:
            kb.append(footer)
        reply_markup = InlineKeyboardMarkup(kb)

    if query:
        try:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        except BadRequest:
            pass
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def handle_resource_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    res_id = query.data.split("_")[1]
    
    # Fetch resource info securely
    data = Database.supabase.table("resources").select("*").eq("id", res_id).execute().data
    if not data:
        await query.message.reply_text("❌ Resource not found.")
        return
        
    r = data[0]
    
    caption = f"📚 *{r['title']}*\n\n{r['description']}" if r.get("description") else f"📚 *{r['title']}*"
    
    if r["resource_type"] == "PHOTO":
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=r["content"], caption=caption, parse_mode="Markdown")
    elif r["resource_type"] == "FILE":
        await context.bot.send_document(chat_id=update.effective_chat.id, document=r["content"], caption=caption, parse_mode="Markdown")
    else:
        # Link
        msg = f"{caption}\n\n🔗 [Open Link]({r['content']})"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown", disable_web_page_preview=False)

    # For authorized users, send a separate message with management options (Delete)
    user = Database.get_user(update.effective_user.id)
    if user and user["role"] in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        kb = [[InlineKeyboardButton(f"🗑️ Delete Resource", callback_data=f"delres_{r['id']}")]]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚙️ *Resource Management*",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

async def delete_resource_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = Database.get_user(query.from_user.id)
    
    if not user or user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        await query.answer("❌ Unauthorized.")
        return

    res_id = query.data.split("_")[1]
    Database.delete_resource(res_id)
    await query.answer("✅ Resource Deleted.")
    await query.edit_message_text("🗑️ Resource has been removed from the library.")


# --- Add Resource Flow ---
async def add_res_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    msg_obj = query.message if query else update.message
    user_id = query.from_user.id if query else update.effective_user.id
        
    user = Database.get_user(user_id)
    if not user or user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        txt = "❌ Only CRs or Teachers can add resources."
        if query: await query.edit_message_text(txt)
        else: await msg_obj.reply_text(txt)
        return ConversationHandler.END

    if query: await query.answer()

    text = "📚 *Add New Resource*\n\nPlease type a *Title* for this resource (e.g., Physics Syllabus):\n_(Or type /cancel)_"
    
    if query:
        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await msg_obj.reply_text(text, parse_mode="Markdown")
        
    return RES_TITLE

async def add_res_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "/cancel":
        await update.message.reply_text("❌ Action Cancelled.")
        return ConversationHandler.END

    context.user_data["tmp_res"] = {"title": update.message.text}
    
    await update.message.reply_text("📝 *Great!* Now optionally type a *Description*, or just type 'skip':", parse_mode="Markdown")
    return RES_DESC

async def add_res_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "/cancel":
        await update.message.reply_text("❌ Action Cancelled.")
        return ConversationHandler.END

    desc = update.message.text
    if desc.lower() == "skip":
        desc = ""
        
    context.user_data["tmp_res"]["description"] = desc
    
    await update.message.reply_text("📎 *Almost done!*\n\nPlease send the *File / Photo*, OR send a *Link* (URL).\nThis is what students will receive when they click the resource.", parse_mode="Markdown")
    return RES_CONTENT

async def add_res_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and update.message.text.lower() == "/cancel":
        await update.message.reply_text("❌ Action Cancelled.")
        return ConversationHandler.END

    if update.message.photo:
        res_type = "PHOTO"
        content = update.message.photo[-1].file_id
    elif update.message.document:
        res_type = "FILE"
        content = update.message.document.file_id
    elif update.message.text:
        res_type = "LINK"
        content = update.message.text
    else:
        await update.message.reply_text("⚠️ Unsupported message. Send a file, photo, or link URL.")
        return RES_CONTENT

    user = Database.get_user(update.effective_user.id)
    class_id = f"{user['department']}_{user['semester']}"

    res_data = {
        "class_id": class_id,
        "author_id": update.effective_user.id,
        "title": context.user_data["tmp_res"]["title"],
        "description": context.user_data["tmp_res"]["description"],
        "resource_type": res_type,
        "content": content
    }

    Database.add_resource(res_data)

    # Offer 'Done' button or continue uploading (to handle albums)
    kb = [[InlineKeyboardButton("✅ Done / সম্পন্ন", callback_data="finish_res")]]
    await update.message.reply_text(
        f"✅ *{res_data['title']}* saved! You can send another file/link for this topic or click **Done**.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )
    return RES_CONTENT

async def finish_res(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Resources saved!")
    await query.edit_message_text("✅ All resources have been added to the library.")
    return ConversationHandler.END

async def cancel_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action Cancelled.")
    return ConversationHandler.END

# --- Search Flow ---

async def search_res_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = Database.get_user(query.from_user.id)
    lang = user.get("language", "en")
    await query.answer()
    await query.edit_message_text(t("search_prompt", lang), parse_mode="Markdown")
    return RES_SEARCH

async def search_res_perform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search_text = update.message.text
    user = Database.get_user(update.effective_user.id)
    lang = user.get("language", "en")
    class_id = f"{user['department']}_{user['semester']}"
    
    results = Database.search_resources(class_id, search_text)
    
    if not results:
        await update.message.reply_text(t("search_none", lang))
        return ConversationHandler.END
        
    text = t("search_results", lang, query=search_text)
    buttons = []
    
    for r in results[:10]: # Top 10 results
        icon = "📎" if r["resource_type"] in ["FILE", "PHOTO"] else "🔗"
        buttons.append([InlineKeyboardButton(f"{icon} {r['title']}", callback_data=f"resitem_{r['id']}")])
        
    if not buttons:
        await update.message.reply_text(t("search_none", lang))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
        
    return ConversationHandler.END


res_view_handler = CommandHandler("resources", view_resources)
res_nav_handler = CallbackQueryHandler(view_resources, pattern="^resources_")
res_click_handler = CallbackQueryHandler(handle_resource_click, pattern="^resitem_")
res_delete_handler = CallbackQueryHandler(delete_resource_callback, pattern="^delres_")

res_search_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(search_res_trigger, pattern="^search_res_trigger$")],
    states={
        RES_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_res_perform)]
    },
    fallbacks=[CommandHandler("cancel", cancel_global)]
)

res_add_handler = ConversationHandler(
    entry_points=[
        CommandHandler("add_resource", add_res_trigger),
        CallbackQueryHandler(add_res_trigger, pattern="^add_resource_trigger$")
    ],
    states={
        RES_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_res_title)],
        RES_DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_res_desc)],
        RES_CONTENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_res_content),
            MessageHandler(filters.PHOTO | filters.Document.ALL, add_res_content),
            CallbackQueryHandler(finish_res, pattern="^finish_res$")
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_global)]
)
