from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ConversationHandler
from database import Database
from utils.i18n import t
from utils.course_loader import get_courses
from utils.helpers import build_menu
from config import Config

# States for Adding Results (CR/Teacher only)
SELECT_STUDENT, SELECT_SUBJECT, ENTER_TITLE, ENTER_MARKS = range(4)

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
        footer.append(InlineKeyboardButton("➕ Add Marks", callback_data="add_result_start"))

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
    
    subj_idx = int(query.data.split("_")[2])
    courses = get_courses(user["semester"], user["department"])
    subject = courses[subj_idx]
    
    # Fetch results for this user and subject
    # We use user_id to show personal marks
    res = Database.supabase.table("results").select("*").eq("user_id", user_id).eq("subject", subject).order("created_at").execute()
    marks_list = res.data
    
    text = t("results_for_subject", lang, subject=subject)
    
    if not marks_list:
        text += "_No marks uploaded for this subject yet._"
    else:
        for m in marks_list:
            text += f"📌 *{m['title']}*: `{m['marks']}`\n"
            
    kb = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_results")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- Result Management (Add Marks) ---

async def add_result_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = Database.get_user(query.from_user.id)
    dept = user["department"]
    sem = user["semester"]
    
    # First, select the subject
    courses = get_courses(sem, dept)
    buttons = [
        InlineKeyboardButton(course, callback_data=f"addres_subj_{i}")
        for i, course in enumerate(courses)
    ]
    
    await query.edit_message_text(
        "📝 *Add Result*\nSelect the subject:",
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
    
    # Now ask for title (e.g. CT-1)
    await query.edit_message_text(f"Subject: *{subject}*\n\nPlease enter the *Title* (e.g., CT-1, Midterm, Assignment):", parse_mode="Markdown")
    return ENTER_TITLE

async def add_result_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text
    context.user_data["tmp_res"]["title"] = title
    
    await update.message.reply_text(f"Title: *{title}*\n\nNow enter the *Marks* for the student(s).\nFormat: `StudentID Marks` (one per line)\nExample:\n`BSSE1501 18` \n`BSSE1502 15`", parse_mode="Markdown")
    return ENTER_MARKS

async def add_result_marks_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = update.message.text.strip().split("\n")
    user = Database.get_user(update.effective_user.id)
    class_id = f"{user['department']}_{user['semester']}"
    res_data = context.user_data["tmp_res"]
    
    success_count = 0
    fail_count = 0
    
    for line in lines:
        parts = line.split()
        if len(parts) < 2: continue
        
        student_id = parts[0]
        marks = " ".join(parts[1:])
        
        # Find user by student_id in this class
        user_res = Database.supabase.table("users").select("id").eq("student_id", student_id).eq("department", user["department"]).eq("semester", user["semester"]).execute()
        
        if user_res.data:
            target_uid = user_res.data[0]["id"]
            Database.supabase.table("results").insert({
                "user_id": target_uid,
                "class_id": class_id,
                "subject": res_data["subject"],
                "title": res_data["title"],
                "marks": marks
            }).execute()
            success_count += 1
            # Optionally notify the student
            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text=f"📊 *New Result Published!*\n\nSubject: {res_data['subject']}\nTitle: {res_data['title']}\nMarks: `{marks}`",
                    parse_mode="Markdown"
                )
            except: pass
        else:
            fail_count += 1
            
    await update.message.reply_text(f"✅ Finished! Added marks for {success_count} students.\n❌ Could not find {fail_count} students.")
    return ConversationHandler.END

async def cancel_res(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action Cancelled.")
    return ConversationHandler.END

# Exports
results_nav_handler = CallbackQueryHandler(handle_subject_results, pattern="^res_subj_")
results_back_handler = CallbackQueryHandler(view_results, pattern="^back_to_results$")

results_add_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_result_start, pattern="^add_result_start$")],
    states={
        SELECT_SUBJECT: [CallbackQueryHandler(add_result_subj_selected, pattern="^addres_subj_")],
        ENTER_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_result_title_received)],
        ENTER_MARKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_result_marks_received)]
    },
    fallbacks=[CommandHandler("cancel", cancel_res)]
)
