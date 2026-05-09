from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ConversationHandler
from database import Database
from utils.i18n import t
from utils.course_loader import get_courses
from utils.helpers import build_menu
from config import Config

# States for Adding Results (CR/Teacher only)
SELECT_ACTION, SELECT_SUBJECT, ENTER_TITLE, ENTER_MARKS, ENTER_FILE = range(5)

async def view_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = Database.get_user(user_id)
    if not user: return
    
    lang = user.get("language", "en")
    dept = user["department"]
    sem = user["semester"]
    
    courses = get_courses(sem, dept)
    
    if not courses:
        await update.message.reply_text(t("results_empty", lang, dept=dept, sem=sem))
        return

    text = t("results_title", lang, dept=dept, sem=sem) + "\n\n" + t("results_select_subject", lang)
    
    buttons = [
        InlineKeyboardButton(course, callback_data=f"res_subj_{i}")
        for i, course in enumerate(courses)
    ]
    
    # If CR/Teacher, add a management button
    footer = []
    if user["role"] in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        footer.append(InlineKeyboardButton("➕ Manage Results", callback_data="add_result_start"))

    reply_markup = build_menu(buttons, n_cols=1, footer_buttons=footer)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_subject_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = Database.get_user(user_id)
    lang = user.get("language", "en")
    class_id = f"{user['department']}_{user['semester']}"
    
    subj_idx = int(query.data.split("_")[2])
    courses = get_courses(user["semester"], user["department"])
    subject = courses[subj_idx]
    
    # 1. Personal Marks
    res = Database.supabase.table("results").select("*").eq("user_id", user_id).eq("subject", subject).order("created_at").execute()
    marks_list = res.data
    
    # 2. Shared Result Sheets (Files)
    sheets_res = Database.supabase.table("course_results").select("*").eq("class_id", class_id).eq("subject", subject).order("created_at").execute()
    sheets_list = sheets_res.data
    
    text = t("results_for_subject", lang, subject=subject)
    
    # Format Marks
    if marks_list:
        text += "📝 *Your Marks:*\n"
        for m in marks_list:
            text += f"   • {m['title']}: `{m['marks']}`\n"
        text += "\n"
    
    # Format Sheets
    text += "📜 *Result Sheets:*\n"
    buttons = []
    if not sheets_list:
        text += "_No result copies uploaded yet._"
    else:
        for s in sheets_list:
            icon = "📄" if s["file_type"] == "DOCUMENT" else "🖼️"
            text += f"   {icon} {s['title']}\n"
            buttons.append(InlineKeyboardButton(f"View {s['title']}", callback_data=f"viewres_{s['id']}"))
            
    if not marks_list and not sheets_list:
        text = t("results_for_subject", lang, subject=subject) + "_No information available for this subject._"

    kb = build_menu(buttons, n_cols=1, footer_buttons=[InlineKeyboardButton("⬅️ Back", callback_data="back_to_results")])
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def view_result_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    res_id = query.data.split("_")[1]
    res = Database.supabase.table("course_results").select("*").eq("id", res_id).execute().data
    
    if not res:
        await query.message.reply_text("❌ File not found.")
        return
        
    f = res[0]
    caption = f"📜 *Result Copy*: {f['title']}\nSubject: {f['subject']}"
    
    if f["file_type"] == "PHOTO":
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=f["file_id"], caption=caption, parse_mode="Markdown")
    else:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=f["file_id"], caption=caption, parse_mode="Markdown")

# --- Result Management (CR Flow) ---

async def add_result_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📝 Enter Personal Marks", callback_data="act_marks")],
        [InlineKeyboardButton("📜 Upload Result Sheet (PDF/JPG)", callback_data="act_sheet")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_res")]
    ]
    
    await query.edit_message_text(
        "⚙️ *Result Management*\nWhat would you like to do?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return SELECT_ACTION

async def add_result_action_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    context.user_data["res_action"] = action
    
    user = Database.get_user(query.from_user.id)
    dept = user["department"]
    sem = user["semester"]
    
    courses = get_courses(sem, dept)
    buttons = [
        InlineKeyboardButton(course, callback_data=f"addres_subj_{i}")
        for i, course in enumerate(courses)
    ]
    
    await query.edit_message_text(
        "📝 Select the *Subject*:",
        reply_markup=build_menu(buttons, n_cols=1),
        parse_mode="Markdown"
    )
    return SELECT_SUBJECT

async def add_result_subj_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = Database.get_user(query.from_user.id)
    subj_idx = int(query.data.split("_")[2])
    courses = get_courses(user["semester"], user["department"])
    subject = courses[subj_idx]
    
    context.user_data["tmp_res"] = {"subject": subject}
    
    await query.edit_message_text(f"Subject: *{subject}*\n\nPlease enter the *Exam Name* (e.g., CT-1, Quiz):", parse_mode="Markdown")
    return ENTER_TITLE

async def add_result_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text
    context.user_data["tmp_res"]["title"] = title
    action = context.user_data["res_action"]
    
    if action == "act_marks":
        await update.message.reply_text(f"Title: *{title}*\n\nNow enter the *Marks* for students.\nFormat: `StudentID Marks` (one per line):", parse_mode="Markdown")
        return ENTER_MARKS
    else:
        await update.message.reply_text(f"Title: *{title}*\n\nNow please upload the **Result Copy (PDF or Image)**:", parse_mode="Markdown")
        return ENTER_FILE

async def add_result_marks_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = update.message.text.strip().split("\n")
    user = Database.get_user(update.effective_user.id)
    class_id = f"{user['department']}_{user['semester']}"
    res_data = context.user_data["tmp_res"]
    
    success_count = 0
    for line in lines:
        parts = line.split()
        if len(parts) < 2: continue
        student_id, marks = parts[0], " ".join(parts[1:])
        user_res = Database.supabase.table("users").select("id").eq("student_id", student_id).eq("department", user["department"]).eq("semester", user["semester"]).execute()
        if user_res.data:
            target_uid = user_res.data[0]["id"]
            Database.supabase.table("results").insert({
                "user_id": target_uid, "class_id": class_id, "subject": res_data["subject"], "title": res_data["title"], "marks": marks
            }).execute()
            success_count += 1
            try:
                await context.bot.send_message(chat_id=target_uid, text=f"📊 *New Result Published!*\n\nSubject: {res_data['subject']}\nTitle: {res_data['title']}\nMarks: `{marks}`", parse_mode="Markdown")
            except: pass
            
    await update.message.reply_text(f"✅ Successfully added marks for {success_count} students.")
    return ConversationHandler.END

async def add_result_file_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = Database.get_user(update.effective_user.id)
    class_id = f"{user['department']}_{user['semester']}"
    res_data = context.user_data["tmp_res"]
    
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "PHOTO"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "DOCUMENT"
    else:
        await update.message.reply_text("⚠️ Please send an Image or a PDF file.")
        return ENTER_FILE
        
    Database.supabase.table("course_results").insert({
        "class_id": class_id,
        "subject": res_data["subject"],
        "title": res_data["title"],
        "file_id": file_id,
        "file_type": file_type
    }).execute()
    
    await update.message.reply_text(f"✅ Result sheet for *{res_data['title']}* has been uploaded for the class!", parse_mode="Markdown")
    return ConversationHandler.END

async def cancel_res(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "❌ Action Cancelled."
    if update.callback_query: await update.callback_query.edit_message_text(msg)
    else: await update.message.reply_text(msg)
    return ConversationHandler.END

# Exports
results_nav_handler = CallbackQueryHandler(handle_subject_results, pattern="^res_subj_")
results_back_handler = CallbackQueryHandler(view_results, pattern="^back_to_results$")
result_file_handler = CallbackQueryHandler(view_result_file, pattern="^viewres_")

results_add_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_result_start, pattern="^add_result_start$")],
    states={
        SELECT_ACTION: [CallbackQueryHandler(add_result_action_selected, pattern="^act_"), 
                       CallbackQueryHandler(cancel_res, pattern="^cancel_res$")],
        SELECT_SUBJECT: [CallbackQueryHandler(add_result_subj_selected, pattern="^addres_subj_")],
        ENTER_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_result_title_received)],
        ENTER_MARKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_result_marks_received)],
        ENTER_FILE: [MessageHandler(filters.PHOTO | filters.Document.ALL, add_result_file_received)]
    },
    fallbacks=[CommandHandler("cancel", cancel_res)]
)
