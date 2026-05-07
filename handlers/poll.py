from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from database import Database
from config import Config
from utils.helpers import get_cancel_button, build_menu

# States
QUESTION, OPTIONS = range(2)

async def poll_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = Database.get_user(update.effective_user.id)
    if not user or user["role"] not in [Config.ROLE_CR, Config.ROLE_TEACHER, Config.ROLE_ADMIN]:
        await update.message.reply_text("❌ Only CRs or Teachers can create polls.")
        return ConversationHandler.END

    await update.message.reply_text(
        "📊 *Create a Class Poll*\n\nWhat is your poll question?\n_(Or type /cancel)_",
        parse_mode="Markdown"
    )
    return QUESTION

async def poll_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "/cancel":
        await update.message.reply_text("❌ Poll Cancelled.")
        return ConversationHandler.END
        
    context.user_data["poll_question"] = update.message.text
    
    await update.message.reply_text(
        "✅ Question saved.\n\nNow, send me the *options* separated by commas.\n_Example: Monday, Wednesday, Friday_",
        parse_mode="Markdown"
    )
    return OPTIONS

async def poll_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "/cancel":
        await update.message.reply_text("❌ Poll Cancelled.")
        return ConversationHandler.END
        
    options = [opt.strip() for opt in update.message.text.split(",") if opt.strip()]
    
    if len(options) < 2:
        await update.message.reply_text("⚠️ You must provide at least *2* options separated by commas.\nTry again:", parse_mode="Markdown")
        return OPTIONS
        
    if len(options) > 10:
        await update.message.reply_text("⚠️ Telegram only supports up to *10* poll options.\nPlease provide fewer options:", parse_mode="Markdown")
        return OPTIONS

    question = context.user_data["poll_question"]
    user = Database.get_user(update.effective_user.id)
    class_id = f"{user['department']}_{user['semester']}"
    
    dept, sem = class_id.split("_")
    
    # Send poll and fetch the result locally
    confirm_msg = await update.message.reply_text("⏳ Broadcasting poll to your class...")
    
    class_users = Database.supabase.table("users").select("id").eq("department", dept).eq("semester", int(sem)).neq("id", user["id"]).execute().data
    
    for u in class_users:
        try:
            await context.bot.send_poll(
                chat_id=u["id"],
                question=question,
                options=options,
                is_anonymous=False
            )
        except Exception:
            pass

    # Send one to the author too
    await context.bot.send_poll(
        chat_id=update.effective_user.id,
        question=question,
        options=options,
        is_anonymous=False
    )
    
    Database.add_poll({
        "class_id": class_id,
        "author_id": user['id'],
        "question": question,
        "options": options
    })
            
    await confirm_msg.edit_text(f"✅ Poll successfully broadcasted and saved for Class {dept} Sem {sem}!")
    
    return ConversationHandler.END

async def view_active_polls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = Database.get_user(update.effective_user.id)
    if not user: return
    
    class_id = f"{user['department']}_{user['semester']}"
    polls = Database.get_polls(class_id)
    
    if not polls:
        await update.message.reply_text("📭 No active polls in your section.")
        return
        
    text = "📊 *Active Polls in Your Section*\n\n"
    for p in polls:
        text += f"❓ *{p['question']}*\n"
        opts = p['options']
        for i, opt in enumerate(opts):
            text += f"   {i+1}. {opt}\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        
    await update.message.reply_text(text, parse_mode="Markdown")

async def delete_poll_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = Database.get_user(query.from_user.id)
    if not user or user["role"] not in [Config.ROLE_CR, Config.ROLE_ADMIN]:
        await query.answer("❌ Unauthorized.")
        return
        
    poll_id = query.data.split("_")[1]
    Database.delete_poll(poll_id)
    await query.answer("✅ Poll Deleted.")
    await query.edit_message_text("🗑️ Poll has been removed.")

async def cancel_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action Cancelled.")
    return ConversationHandler.END

poll_view_handler = CommandHandler("polls", view_active_polls)
poll_delete_handler = CallbackQueryHandler(delete_poll_callback, pattern="^delpoll_")

poll_handler = ConversationHandler(
    entry_points=[CommandHandler("poll", poll_start)],
    states={
        QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, poll_question)],
        OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, poll_options)],
    },
    fallbacks=[CommandHandler("cancel", cancel_poll)]
)
